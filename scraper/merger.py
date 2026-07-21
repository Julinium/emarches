import traceback
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytz
from django.db import transaction
from rest_framework import serializers

from base.models import (
    Agrement, Category, Change, Client, Concurrent, Deposit, Domain, FileToGet,
    Kind, Lot, Meeting, Mode, Opening, Procedure, Qualif, RelAgrementLot,
    RelDomainTender, RelQualifLot, Sample, Tender, Visit)

from scraper import constants as C
from scraper import helper

from scraper.serializers import (AgrementSerializer, CategorySerializer,
                                 ChangeSerializer, ClientSerializer,
                                 DomainSerializer, KindSerializer,
                                 LotSerializer, MeetingSerializer,
                                 ModeSerializer, ProcedureSerializer,
                                 QualifSerializer, RelAgrementLotSerializer,
                                 RelDomainTenderSerializer,
                                 RelQualifLotSerializer, SampleSerializer,
                                 TenderSerializer, VisitSerializer)


def format(tender_json):

    helper.printMessage('DEBUG', 'm.format', "### Started formatting Tender data ...")
    j = tender_json
    try:
        j["published"] = helper.getDateTime(j["published"])
        j["deadline"] = helper.getDateTime(j["deadline"])
        j["cancelled"] = j["cancelled"] == "Oui"
        j["plans_price"] = helper.getAmount(j["plans_price"])
        j["acronym"] = j["link"].split("=")[1]

        ebs = j["ebid_esign"] # 1: Required, 0: Not required, Else: NA
        match ebs:  # Look at the image ...
            case "reponse-elec-oblig": # cons_repec = 'RO'
                j["ebid"] = 1
                j["esign"] = 0                
            case "reponse-elec": #cons_repec = 'OO'
                j["ebid"] = 0
                j["esign"] = 0
            case "reponse-elec-oblig-avec-signature": #cons_repec = 'RR'
                j["ebid"] = 1
                j["esign"] = 1
            case "reponse-elec-avec-signature": # cons_repec = 'OR'
                j["ebid"] = 0
                j["esign"] = 1
            # case "reponse-elec-non": # cons_repec = 'I'

        ll = j["lots"]

        reserved_t, variant_t = False, False
        estimate_t, bond_t = 0, 0
        jl = len(ll) if ll else 0
        if jl > 0:
            reserved_t = ll[0]["reserved"] == "Oui"
            variant_t = ll[0]["variant"] == "Oui"
            c = 0
            for l in ll:
                c += 1
                l["number"] = lottify(l["number"], c)
                l["estimate"] = helper.getAmount(l["estimate"])
                estimate_t += l["estimate"]
                l["bond"] = helper.getAmount(l["bond"])
                bond_t += l["bond"]
                l["variant"] = l["variant"] == "Oui"
                l["reserved"] = l["reserved"] == "Oui"
                ss = l["samples"]
                sl = len(ss) if ss else 0
                if sl > 0:
                    for s in ss:
                        s["when"] = helper.getDateTime(s["when"])
                    l["samples"] = ss
                mm = l["meetings"]
                ml = len(mm) if mm else 0
                if ml > 0:
                    for m in mm:
                        m["when"] = helper.getDateTime(m["when"])
                    l["meetings"] = mm
                vv = l["visits"]
                vl = len(vv) if vv else 0
                if vl > 0:
                    for v in vv:
                        v["when"] = helper.getDateTime(v["when"])
                    l["visits"] = vv
            j["lots"] = ll
            j["reserved"] = reserved_t
            j["variant"] = variant_t
            j["estimate"] = estimate_t
            j["bond"] = bond_t
        helper.printMessage('DEBUG', 'm.format', "+++ Done formatting Tender data")

    except:
        traceback.print_exc()

    return j


# TODO: Saving lots related objects, try to change the approach.
#       Always create new instances. At the end, delete orphans.

@transaction.atomic
def save(tender_data):    

    formatted_data = format(tender_data)
    helper.printMessage('DEBUG', 'm.save', f"### Started saving formatted Tender data {formatted_data["chrono"]}")

    # Step x: Validate the JSON using TenderSerializer
    tender_serializer = TenderSerializer(data=formatted_data)
    tender_serializer.is_valid(raise_exception=True)
    validated_data = tender_serializer.validated_data


    # Step x: Handle foreign key relationships (category, client, kind, mode, procedure)
    category_data  = formatted_data['category']
    client_data    = formatted_data['client']
    kind_data      = formatted_data['kind']
    mode_data      = formatted_data['mode']
    procedure_data = formatted_data['procedure']
    lots_data      = formatted_data['lots']
    domains_data   = formatted_data['domains']
    chrono         = formatted_data["chrono"]

    category, client, kind, mode, procedure = create_cckmp(category_data, client_data, kind_data, mode_data, procedure_data)


    ## Handle Tender base details
    tender = Tender.objects.filter(chrono=chrono).first()
    tender_create = tender == None

    if tender is None:
        ### Create a new Tender
        helper.printMessage('DEBUG', 'm.save', f"### Tender to be created: {chrono}")
        tender = create_tender(validated_data, category, client, kind, mode, procedure)
        if tender:
            domains = set_domains(domains_data, tender)
            created_lots = create_lots(lots_data, tender)
    else: 
        ### Update existing Tender
        helper.printMessage('INFO', 'm.save', f"### Tender exists. Updating: {chrono}")
        changed_fields = []
        lots_qs = tender.lots.all()##.prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
        numbers_list = [lot_data['number'] for lot_data in lots_data]
        numbers_list_qs = list(lots_qs.values_list('number', flat=True))

        numbers_to_create = list(set(numbers_list) - set(numbers_list_qs))
        numbers_to_update = list(set(numbers_list) & set(numbers_list_qs))
        numbers_to_delete = list(set(numbers_list_qs) - set(numbers_list))

        helper.printMessage('DEBUG', 'm.save', f"### Lots: +{len(numbers_to_create)}, -{len(numbers_to_delete)}, ~{len(numbers_to_update)}")
        helper.printMessage('TRACE', 'm.save', f"### numbers_to_create: {numbers_to_create}")
        helper.printMessage('TRACE', 'm.save', f"### numbers_to_update: {numbers_to_update}")
        helper.printMessage('TRACE', 'm.save', f"### numbers_to_delete: {numbers_to_delete}")

        if len(numbers_to_delete) > 0:
            dll = delete_lots_list(numbers_to_delete, tender)
            helper.printMessage('TRACE', 'm.save', f">>> Deleted Lots and objects: \n{dll}\n")
            change = {"field": "lot", "old_value": "-", "new_value": f"{-len(numbers_to_delete)}"}
            changed_fields.append(change)
        if len(numbers_to_create) > 0 :
            data_to_create = [obj for obj in lots_data if obj.get('number') in set(numbers_to_create)]
            create_lots(data_to_create, tender)
            change = {"field": "lot", "old_value": f"+{len(numbers_to_create)}", "new_value": f"-"}
            changed_fields.append(change)
        if len(numbers_to_update) > 0 :
            # TODO: Check for and record changes
            data_to_update = [obj for obj in lots_data if obj.get('number') in set(numbers_to_update)]
            changes = update_lots(numbers_to_update, data_to_update, tender)
            changed_fields += changes


    # Log changed fields, if any
    target_date = datetime.now() - timedelta(days=C.PORTAL_DCE_PAST_DAYS)
    target_date = target_date.date()
    tender_date = tender.deadline.date()

    if len(changed_fields) > 0 :
        try:
            helper.printMessage('TRACE', 'm.save', "#### Saving change record to databse ... ")
            change = Change(tender=tender, changes=changed_fields)
            change.save()
            log_message = f"Tender {tender.chrono} updated. Changes saved."
            helper.printMessage('DEBUG', 'm.save', log_message)
            helper.printMessage('DEBUG', 'm.save', f"Reported changes: {changed_fields}")
        except:
            helper.printMessage('WARN', 'm.save', "---- Exception raised saving change to database.")
            traceback.print_exc()

        if tender_date > target_date:
            try:
                helper.printMessage('TRACE', 'm.save', f"#### Adding DCE request for Tender {tender.chrono} ... ")
                f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Updated'})
            except:
                helper.printMessage('WARN', 'm.save', "---- Exception raised saving DCE request.")
                traceback.print_exc()

    
    # if tender_create:
    #     if tender_date > target_date:
    #         try:
    #             helper.printMessage('TRACE', 'm.save', "#### Adding DCE request for Tender ... ")
    #             f2d, _ = FileToGet.objects.update_or_create(tender=tender)
    #         except:
    #             helper.printMessage('WARN', 'm.save', "---- Exception raised saving DCE request.")
    #             traceback.print_exc()
    # else: # Update return boolean: True=Created, False=Updated, None=None
    #     if len(changed_fields) == 0:
    #         helper.printMessage('DEBUG', 'm.save', f"No change was found for {tender.chrono}" )
    #         tender_create = None


    helper.printMessage('DEBUG', 'g.save', '+++ Finished saving Tender data.')


    return tender, tender_create


@transaction.atomic
def mergeResults(digest):

    chro = digest.get('chrono', '?')
    acro = digest.get('acronym', '?')    
    helper.printMessage('INFO', 'm.mergeResults', f"### Started merging results for {chro}&{acro}")
    helper.printMessage('DEBUG', 'm.mergeResults', f"\tReceived result digest {digest}")
    tender = Tender.objects.filter(chrono=chro, acronym=acro).first()
    if not tender: 
        helper.printMessage('ERROR', 'm.mergeResults', f"### Error: Tender not found for {chro}&{acro}. No result saved", 1)
        return None

    failures_text = digest.get('failures_text', '-')
    date_str = digest.get('date_finished', '')
    try: 
        date = datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception as xc:
        date = None
        helper.printMessage('ERROR', 'm.mergeResults', f"\tCould not extract date from {date}")
        helper.printMessage('DEBUG', 'm.mergeResults', f"\tRaised exception: {xc}")

    has_tech = digest.get('has_tech', None)
    
    winners = digest.get('winner_offers', [])
    won_amount, won_lots = 0, 0
    for w in winners: 
        won_amount += helper.getAmount(w.get('amount'))
        won_lots += 1



    # Create or update Opening                
    opening, created = Opening.objects.update_or_create(
        tender = tender,
        defaults = {
            'has_tech' : has_tech,
            'failure' : failures_text,
            'date' : date,
            'won_amount'   : won_amount,
            'won_lots'     : won_lots,
            }
        )
    if created: 
        helper.printMessage('DEBUG', 'm.mergeResults', f"Created results digest for {chro}&{acro}")
    else: 
        helper.printMessage('DEBUG', 'm.mergeResults', f"Updated results digest for {chro}&{acro}")


    fi_offers = digest.get('financial_offers', [])
    rejects_tech = digest.get('rejected_dt', [])
    rejects_admin = digest.get('rejected_da', [])
    reserves_admin = digest.get('reserved_da', [])
    accepts_admin = digest.get('accepted_da', [])


    candidates = digest.get('bidders', [])
    tender_lots = list(tender.lots.values_list('number', flat=True))

    for cand in candidates:
        name    = cand.get('name')
        helper.printMessage('DEBUG', 'm.mergeResults', f"\t##Handling Candidate: { name }")
        concurrent, created_c = Concurrent.objects.get_or_create(
            name = name,
        )
        if created_c:
            helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Created Concurrent { name }")
        else:
            helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Found existing Concurrent { name }")

        for lot in tender_lots:
            found_depots = 0
            lot_obj = tender.lots.filter(number=lot).first()
            lot_est = lot_obj.estimate if lot_obj else None
            lot = str(lot)
            admin = None
            reject_t = None
            justif = None
            xin_offset = None
            amount_a = None
            amount_b = None
            amount_w = None
            winner = None
                        
            if next((item for item in accepts_admin if item.get("name") == name and item.get("lot") == lot), None): 
                admin = 'a'
                found_depots += 1
            if next((item for item in reserves_admin if item.get("name") == name and item.get("lot") == lot), None): 
                admin = 'r'
                found_depots += 1
            if next((item for item in rejects_admin if item.get("name") == name and item.get("lot") == lot), None): 
                admin = 'x'
                found_depots += 1
            
            if next((item for item in rejects_tech if item.get("name") == name and item.get("lot") == lot), None): 
                reject_t = True
                found_depots += 1            
            
            winner_item = next((item for item in winners if item.get("name") == name and item.get("lot") == lot), None)
            if winner_item:
                amount_w = helper.getAmount(winner_item.get("amount"))
                winner = True
                found_depots += 1
                
                justifs = digest.get('winner_justifs', [])
                justif_item = next((item for item in justifs if item.get("lot") == lot), None)
                if justif_item:
                    justif = justif_item.get("justif", '')
            
            offer_item = next((item for item in fi_offers if item.get("name") == name and item.get("lot") == lot), None)
            if offer_item:
                amount_b = helper.getAmount(offer_item.get("pre_amount"))
                amount_a = helper.getAmount(offer_item.get("amount"))
                found_depots += 1

            if found_depots > 0:                
                deposit, created_d = Deposit.objects.get_or_create(
                    opening=opening,
                    concurrent=concurrent,
                    lot_number=lot,
                    defaults={
                        'date'         : date,
                        'amount_b'     : amount_b,
                        'amount_a'     : amount_a,
                        'amount_w'     : amount_w,
                        'winner'       : winner, 
                        'justif'       : justif,
                        'reject_t'     : reject_t, 
                        'admin'        : admin, 
                    }
                )

                if created_d:
                    helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Created Deposit instance, Lot { lot}, for { name }")
                else:
                    helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Updated existing Deposit instance, Lot { lot}, for { name }")
      
    return 0



def ensure_dt_rabat(snap, default_time=time(0,0)):
    rabat_tz = pytz.timezone("Africa/Casablanca")
    if not snap: return None
    if not isinstance(snap, datetime):
        naive_dt = datetime.combine(snap, default_time)
        return rabat_tz.localize(naive_dt)
    return snap


def create_cckmp(category_data, client_data, kind_data, mode_data, procedure_data):
    
    category = None
    helper.printMessage('TRACE', 'm.create_cckmp', "### Handling Category ... ")
    if category_data:        
        label = category_data.get('label')
        if label:
            category = Category.objects.filter(label=label).first()
            if category == None:
                category_serializer.is_valid(raise_exception=True)
                category = category_serializer.create_cckmp()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Category: {category.label}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Category found. Skipping: {category.label}")
    
    client = None
    helper.printMessage('TRACE', 'm.create_cckmp', "### Handling Client ... ")
    if client_data:        
        name = client_data.get('name')
        if name:
            client = Client.objects.filter(name=name).first()
            if client == None:
                client_serializer.is_valid(raise_exception=True)
                client = client_serializer.create_cckmp()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Client: {client.name}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Client found. Skipping: {client.name}")
    
    kind = None
    helper.printMessage('TRACE', 'm.create_cckmp', "### Handling Kind ... ")
    if kind_data:        
        name = kind_data.get('name')
        if name:
            kind = Kind.objects.filter(name=name).first()
            if kind == None:
                kind_serializer.is_valid(raise_exception=True)
                kind = kind_serializer.create_cckmp()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Kind: {kind.name}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Kind found. Skipping: {kind.name}")
    
    mode = None
    helper.printMessage('TRACE', 'm.create_cckmp', "### Handling Mode ... ")
    if mode_data:        
        name = mode_data.get('name')
        if name:
            mode = Mode.objects.filter(name=name).first()
            if mode == None:
                mode_serializer.is_valid(raise_exception=True)
                mode = mode_serializer.create_cckmp()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Mode: {mode.name}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Mode found. Skipping: {mode.name}")
    
    procedure = None
    helper.printMessage('TRACE', 'm.create_cckmp', "### Handling Procedure ... ")
    if procedure_data:        
        name = procedure_data.get('name')
        if name:
            procedure = Procedure.objects.filter(name=name).first()
            if procedure == None:
                procedure_serializer.is_valid(raise_exception=True)
                procedure = procedure_serializer.create_cckmp()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Procedure: {procedure.name}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Procedure found. Skipping: {procedure.name}")
    

    return category, client, kind, mode, procedure


def create_tender(input_data, category, client, kind, mode, procedure):
    validated_data = input_data
    chrono = validated_data.get('chrono')
    tender = None
    helper.printMessage('TRACE', 'm.create_tender', "### Handling Tender ... ")
    tender_serializer = TenderSerializer(data=validated_data, category=category, client=client, kind=kind, mode=mode, procedure=procedure )
    helper.printMessage('DEBUG', 'm.create_tender', f"+++ Tender to be created: {chrono}")
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)

    return tender


def set_domains(input_data, tender):
    helper.printMessage('TRACE', 'm.set_domains', "### Handling Domains ... ")
    domains_data = input_data
    created_domains, skipped_domains = 0, 0
    domains = []
    for domain_data in domains_data:
        name = domain_data.get('name')
        if name and name != "":
            domain = Domain.objects.filter(name=name).first()
            if domain:
                skipped_domains += 1
                helper.printMessage('DEBUG', 'm.set_domains', f"--- Domain already exists. Skipping: {name[:C.TRUNCA]}...")
            else:
                helper.printMessage('DEBUG', 'm.set_domains', f"+++ Domain of Activiry to be created: {name[:C.TRUNCA]}...")
                domain_serializer = DomainSerializer(data=domain_data)
                domain_serializer.is_valid(raise_exception=True)
                domain = domain_serializer.save()
                created_domains += 1
            domains.append(domain)
    helper.printMessage('TRACE', 'm.set_domains', f">>> Domains: Created {created_domains}, skipped {skipped_domains}.")

    tender.domains.set(domains)
    return len(domains)


def create_lots(input_data, tender):
    helper.printMessage('TRACE', 'm.create_lots', "### Handling Lots ... ")
    lots_data = input_data
    created_lots = 0
    ll = len(lots_data) if lots_data else 0
    if ll > 0:
        helper.printMessage('TRACE', 'm.create_lots', f"#### Got data for {ll} Lots. ")
        i = 0

        helper.printMessage("TRACE", 'm.create_lots', f"Lots raw data:\n=====================\n{lots_data}\n=====================\n")

        for lot_data in lots_data:
            i += 1
            lot_number_text = lot_data['number']
            # lot_data['number'] = lottify(lot_number_text, i)
            helper.printMessage('DEBUG', 'm.create_lots', f"#### Handling Lot {i}/{ll} ... ", 1)
            helper.printMessage("TRACE", 'm.create_lots', f"Lot {i} raw data:\n=====================\n{lot_data}\n=====================")


            # Handle nested Category for Lot
            lot_category = create_category(lot_data["category"])

            # Create Lot
            lot = None
            lot_title  = lot_data.get('title')
            lot_number = lot_data.get('number', 1)
            helper.printMessage('TRACE', 'm.create_lots', "#### Handling Lot details ... ")
            if lot_title:
                # if not Lot.objects.filter(tender=tender, title=lot_title, number=lot_number).exists():
                lot_serializer = LotSerializer(data=lot_data)
                helper.printMessage('TRACE', 'm.create_lots', f"+++ Lot to be created: {lot_title[:C.TRUNCA]}...")
                lot_serializer.is_valid(raise_exception=True)
                lot = lot_serializer.save(tender=tender, category=lot_category)


            created_samples = create_samples(lot_data['samples'], lot)
            created_meetings = create_meetings(lot_data['meetings'], lot)
            created_visits = create_visits(lot_data['visits'], lot)
            created_qualifs = create_qualifs(lot_data['qualifs'], lot)
            created_agrements = create_agrements(lot_data['agrements'], lot)

            helper.printMessage('TRACE', 'm.create_lots', f">>> Created: {created_samples} Samples, {created_meetings} Meetings, {created_visits} Visits, {created_qualifs} Qualifs, {created_agrements} Agrements, ")


def create_category(input_data):
    lot_category_data = input_data
    lot_category = None
    helper.printMessage('TRACE', 'm.create_category', "#### Handling Lot Category ... ")
    if lot_category_data:
        label = lot_category_data.get('label')
        if label:
            if not Category.objects.filter(label=label).exists():
                helper.printMessage('TRACE', 'm.create_category', f"++++ Lot Category to be created: {label[:C.TRUNCA]}...")
                lot_category_serializer = CategorySerializer(data=lot_category_data)                    
                lot_category_serializer.is_valid(raise_exception=True)
                lot_category = lot_category_serializer.save()
            else:
                helper.printMessage('TRACE', 'm.create_category', f"---- Lot Category exists. Skipping: : {label[:C.TRUNCA]}...")
    return lot_category


def create_samples(input_data, lot):
    helper.printMessage('TRACE', 'm.create_samples', "#### Handling Lot Samples ... ")
    samples_data = input_data
    created_samples = 0
    for sample_data in samples_data:
        sample_data['when'] = ensure_dt_rabat(sample_data.get('when'))
        when = sample_data.get('when')
        description = sample_data.get('description')
        if when:
            # if not Sample.objects.filter(when=when, lot=lot).exists():
            sample_serializer = SampleSerializer(data=sample_data)
            helper.printMessage('TRACE', 'm.create_samples', f"++++ Sample to be created: {when}")
            sample_serializer.is_valid(raise_exception=True)
            sample_serializer.save(lot=lot)
            created_samples += 1
    return created_samples


def create_meetings(input_data, lot):
    helper.printMessage('TRACE', 'm.create_meetings', "#### Handling Lot Meetings ... ")
    meetings_data = input_data
    created_meetings = 0
    for meeting_data in meetings_data:
        meeting_data['when'] = ensure_dt_rabat(meeting_data.get('when'))
        when = meeting_data.get('when')
        description = meeting_data.get('description')
        if when:
            # if not Meeting.objects.filter(when=when, lot=lot).exists():
            meeting_serializer = MeetingSerializer(data=meeting_data)
            helper.printMessage('TRACE', 'm.create_meetings', f"++++ Meeting to be created: {when}")
            meeting_serializer.is_valid(raise_exception=True)
            meeting_serializer.save(lot=lot)
            created_meetings += 1
    return created_meetings


def create_visits(input_data, lot):
    helper.printMessage('TRACE', 'm.create_visits', "#### Handling Lot Visitss ... ")
    visits_data = input_data
    created_visits = 0
    for visit_data in visits_data:
        visit_data['when'] = ensure_dt_rabat(visit_data.get('when'))
        when = visit_data.get('when')
        description = visit_data.get('description')
        if when:
            # if not Visit.objects.filter(when=when, lot=lot).exists():
            visit_serializer = VisitSerializer(data=visit_data)
            helper.printMessage('TRACE', 'm.create_visits', f"++++ Visits to be created: {when}")
            visit_serializer.is_valid(raise_exception=True)
            visit_serializer.save(lot=lot)
            created_visits += 1
    return created_visits


def create_qualifs(input_data, lot):
    helper.printMessage('TRACE', 'm.create_qualifs', "#### Handling Lot Qualifs ... ")
    qualifs_data = input_data
    qualifs = []
    for qualif_data in qualifs_data:
        short = qualif_data.get('short')
        name = qualif_data.get('name')
        qualif = None
        if name:
            if not Qualif.objects.filter(name=name).exists():
                qualif_serializer = QualifSerializer(data=qualif_data)
                helper.printMessage('TRACE', 'm.create_qualifs', f"++++ Qualif to be created: {name[:C.TRUNCA]}...")
                qualif_serializer.is_valid(raise_exception=True)
                qualif = qualif_serializer.save()
                qualifs.append(qualif)
            else:
                helper.printMessage('TRACE', 'm.create_qualifs', "---- Qualif exists. Skipping.")                
    lot.qualifs.set(qualifs)
    return len(qualifs)


def create_agrements(input_data, lot):
    helper.printMessage('TRACE', 'm.create_qualifs', "#### Handling Lot Agrements ... ")
    agrements_data = input_data
    agrements = []
    for agrement_data in agrements_data:
        short = agrement_data.get('short')
        name = agrement_data.get('name')
        agrement = None
        if name:
            if not Agrement.objects.filter(name=name).exists():
                agrement_serializer = AgrementSerializer(data=agrement_data)
                helper.printMessage('TRACE', 'm.create_qualifs', f"++++ Agrement to be created: {name[:C.TRUNCA]}...")
                agrement_serializer.is_valid(raise_exception=True)
                agrement = agrement_serializer.save()
                agrements.append(agrement)
            else:
                helper.printMessage('TRACE', 'm.create_qualifs', "---- Agrement exists. Skipping.")
    
    lot.agrements.set(agrements)
    return len(agrements)


def lottify(lot_no_str, default_int = 1):
    try:
        s = lot_no_str.lower().replace('lot', '').replace(':', '').replace('#', '')
        n = int(s.strip())
        if n > 0: return n
    except: pass
    return default_int


def delete_lots_list(numbers_list=[], tender=None):       
    if numbers_list == [] or tender == None: return None
    try:
        lots = Lot.objects.filter(tender=tender, number__in=numbers_list)
        return lots.delete()
    except Exception as xx:
        helper.printMessage('ERROR', 'g.delete_lots_list', str(xx))
        return None


def update_lots(numbers, lots_data, tender):
    helper.printMessage('TRACE', 'm.update_lots', f"### Updating {len(numbers)} lot(s) with data: \n{lots_data}")    
    lots_qs = tender.lots.filter(number__in=numbers).prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
    helper.printMessage('TRACE', 'm.update_lots', f">>> Found {len(lots_qs)} lot(s) in databas.")

    def lot_changed(lot, lot_data):
        if lot_data.get('number') != lot.number: return "number"
        if lot_data.get('title') != lot.title: return "title"
        if (lot_data.get('category') or {}).get('label', "") != lot.category.label: return "category"
        if lot_data.get('estimate') != lot.estimate: return "estimate"
        if lot_data.get('bond') != lot.bond: return "bond"
        if lot_data.get('variant') != lot.variant: return "variant"
        if lot_data.get('reserved') != lot.reserved: return "reserved"

        # if len(lot_data.get('qualifs')) != len(lot.qualifs.all()): return "qualifs"
        # if len(lot_data.get('agrements')) != len(lot.agrements.all()): return "agrements"
        # if len(lot_data.get('samples')) != len(lot.samples.all()): return "samples"
        # if len(lot_data.get('meetings')) != len(lot.meetings.all()): return "meetings"
        # if len(lot_data.get('visits')) != len(lot.visits.all()): return "visits"

        return None

    def qualifs_changed(qualifs, data):
        if len(data) != len(qualifs.all()): return True
        i = 0
        for qualif_data in data:
            qualif = qualifs.all()[i]
            if qualif_data.get("name") != qualif.name: return True
            i += 1
        return False

    def agrements_changed(agrements, data):
        if len(data) != len(agrements.all()): return True
        i = 0
        for agrement_data in data:
            agrement = agrements.all()[i]
            if agrement_data.get("name") != agrement.name: return True
            i += 1
        return False

    def samples_changed(samples, data):
        if len(data) != len(samples.all()): return True
        i = 0
        for sample_data in data:
            sample = samples.all()[i]
            if sample_data.get("when") != sample.when: return True
            if sample_data.get("description") != sample.description: return True
            i += 1
        return False

    def meetings_changed(meetings, data):
        if len(data) != len(meetings.all()): return True
        i = 0
        for meeting_data in data:
            meeting = meetings.all()[i]
            if meeting_data.get("when") != meeting.when: return True
            if meeting_data.get("description") != meeting.description: return True
            i += 1
        return False

    def visits_changed(visits, data):
        if len(data) != len(visits.all()): return True
        i = 0
        for visit_data in data:
            visit = visits.all()[i]
            if visit_data.get("when") != visit.when: return True
            if visit_data.get("description") != visit.description: return True
            i += 1
        return False

    changes = []
    changed = False
    l = len(lots_qs.all())

    for lot_qs in lots_qs:
        lot_data = next((obj for obj in lots_data if obj.get('number') == lot_qs.number), None)
        helper.printMessage('DEBUG', 'm.update_lots', f"#### Checking Lot {lot_qs.number}/{l}...")
        if lot_data:
            if lot_changed(lot_qs, lot_data):
                helper.printMessage('DEBUG', 'm.update_lots', f">>>> Change detected in Lot #{lot_qs.number}. To be updated")
                helper.printMessage('TRACE', 'm.update_lots', f"#### Updating Lot {lot_qs.number} with data: \n{ lot_data }")
                lot_serializer = LotSerializer(lot_qs, data=lot_data, partial=True)
                if lot_serializer.is_valid(): lot_serializer.save()
                changed = True
                
            if qualifs_changed(lot_qs.qualifs, lot_data['qualifs']):
                deleted_qualifs   = lot_qs.qualifs.all().delete()
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Deleted Qualifs: {len(deleted_qualifs)}")
                created_qualifs   = create_qualifs(lot_data['qualifs'], lot_qs)
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Created Qualifs: {created_qualifs}")
                changed = True
                
            if agrements_changed(lot_qs.agrements, lot_data['agrements']):
                deleted_agrements   = lot_qs.agrements.all().delete()
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Deleted Agrements: {len(deleted_agrements)}")
                created_agrements   = create_agrements(lot_data['agrements'], lot_qs)
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Created Agrements: {created_agrements}")
                changed = True
                
            if meetings_changed(lot_qs.meetings, lot_data['meetings']):
                deleted_meetings   = lot_qs.meetings.all().delete()
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Deleted Meetings: {len(deleted_meetings)}")
                created_meetings   = create_meetings(lot_data['meetings'], lot_qs)
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Created Meetings: {created_meetings}")
                changed = True
                
            if samples_changed(lot_qs.samples, lot_data['samples']):
                deleted_samples   = lot_qs.samples.all().delete()
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Deleted Samples: {len(deleted_samples)}")
                created_samples   = create_samples(lot_data['samples'], lot_qs)
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Created Samples: {created_samples}")
                changed = True
                
            if visits_changed(lot_qs.visits, lot_data['visits']):
                deleted_visits   = lot_qs.visits.all().delete()
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Deleted Visits: {len(deleted_visits)}")
                created_visits   = create_visits(lot_data['visits'], lot_qs)
                helper.printMessage('TRACE', 'm.update_lots', f">>>> Created Visits: {created_visits}")
                changed = True

    if changed:
        change = {"field": "lot" , "old_value": "-", "new_value": "-"}
        changes.append(change)
    
    return changes



