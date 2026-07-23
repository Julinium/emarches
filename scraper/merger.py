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
            case _: # cons_repec = 'OR'
                j["ebid"] = 9
                j["esign"] = 9

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


@transaction.atomic
def save(tender_data):    

    formatted_data = format(tender_data)
    helper.printMessage('DEBUG', 'm.save', f"### Started saving formatted Tender data {formatted_data["chrono"]}")

    tender_serializer = TenderSerializer(data=formatted_data)
    tender_serializer.is_valid(raise_exception=True)
    validated_data = tender_serializer.validated_data

    category_data  = formatted_data['category']
    client_data    = formatted_data['client']
    kind_data      = formatted_data['kind']
    mode_data      = formatted_data['mode']
    procedure_data = formatted_data['procedure']
    lots_data      = formatted_data['lots']
    domains_data   = formatted_data['domains']
    chrono         = formatted_data["chrono"]

    category, client, kind, mode, procedure = create_cckmp(category_data, client_data, kind_data, mode_data, procedure_data)

    tender = Tender.objects.filter(chrono=chrono).first()
    tender_create = tender == None
    changed_fields = []

    if tender is None: ### Create a new Tender
        helper.printMessage('DEBUG', 'm.save', f"### Tender to be created: {chrono}")
        tender = create_tender(validated_data, category, client, kind, mode, procedure)
        if tender:
            domains = set_domains(domains_data, tender)
            created_lots = create_lots(lots_data, tender)
    else: ### Update existing Tender
        helper.printMessage('INFO', 'm.save', f"### Tender exists. Updating: {chrono}")
        
        lots_qs = tender.lots.all()
        numbers_list = [lot_data['number'] for lot_data in lots_data] if lots_data else []
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
            if tender.lots_count > 1:
                change = {"field": "lot", "old_value": "-", "new_value": f"{-len(numbers_to_delete)}"}
                changed_fields.append(change)
        if len(numbers_to_create) > 0 :
            data_to_create = [obj for obj in lots_data if obj.get('number') in set(numbers_to_create)]
            create_lots(data_to_create, tender)
            if tender.lots_count > 1:
                change = {"field": "lot", "old_value": f"+{len(numbers_to_create)}", "new_value": f"-"}
                changed_fields.append(change)
        if len(numbers_to_update) > 0 :
            data_to_update = [obj for obj in lots_data if obj.get('number') in set(numbers_to_update)]
            if tender.lots_count > 1:
                changes = update_lots(numbers_to_update, data_to_update, tender)
                changed_fields += changes

        tender_changes = update_tender(tender, formatted_data, category, client, kind, mode, procedure)
        changed_fields += tender_changes

    log_changes(changed_fields, tender)
    if len(changed_fields) < 1: 
        helper.printMessage('DEBUG', 'g.save', '--- No changes were found. >>> Next.')
    else:
        helper.printMessage('DEBUG', 'g.save', '+++ Data saved successfully. >>> Next.')

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
                category_serializer = CategorySerializer(data=category_data)
                category_serializer.is_valid(raise_exception=True)
                category = category_serializer.save()
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
                client_serializer = ClientSerializer(data=client_data)
                client_serializer.is_valid(raise_exception=True)
                client = client_serializer.save()
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
                kind_serializer = Kinderializer(kind_data)
                kind_serializer.is_valid(raise_exception=True)
                kind = kind_serializer.save()
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
                mode_serializer = ModeSerializer(data=mode_data)
                mode_serializer.is_valid(raise_exception=True)
                mode = mode_serializer.save()
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
                procedure_serializer = ProcedureSerializer(data=procedure_data)
                procedure_serializer.is_valid(raise_exception=True)
                procedure = procedure_serializer.save()
                helper.printMessage('TRACE', 'm.create_cckmp', f"+++ Created Procedure: {procedure.name}")
            else:
                helper.printMessage('TRACE', 'm.create_cckmp', f"--- Procedure found. Skipping: {procedure.name}")
    

    return category, client, kind, mode, procedure


def create_tender(input_data, category, client, kind, mode, procedure):
    validated_data = input_data
    chrono = validated_data.get('chrono')
    tender = None
    tender_serializer = TenderSerializer(data=validated_data)
    helper.printMessage('DEBUG', 'm.create_tender', f"+++ Tender to be created: {chrono}")
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)

    return tender


def update_tender(tender, input_data, category, client, kind, mode, procedure):
    helper.printMessage('TRACE', 'm.update_tender', f"### Tender {tender.chrono} to update with: \n{input_data}:")
    
    changes = []

    def domains_changed(data, domains):
        incoming_names = {item.get("name") for item in data}
        existing_names = set(domains.values_list("name", flat=True))
        return incoming_names != existing_names

    def tender_changed(tender, input_data):
        if input_data.get('deadline') != tender.deadline: return {"field": "deadline", "old_value": tender.deadline, "new_value": input_data.get('deadline')}
        if input_data.get('estimate') != tender.estimate: return {"field": "estimate", "old_value": tender.estimate, "new_value": input_data.get('estimate')}
        if input_data.get('bond') != tender.bond: return {"field": "bond", "old_value": tender.bond, "new_value": input_data.get('bond')}
        if input_data.get('cancelled') != tender.cancelled: return {"field": "cancelled", "old_value": tender.cancelled, "new_value": input_data.get('cancelled')}
        if input_data.get('size_read') != tender.size_read: return {"field": "size_read", "old_value": tender.size_read, "new_value": input_data.get('size_read')}
        if input_data.get('size_bytes') and input_data.get('size_bytes') != tender.size_bytes: return {"field": "size_bytes", "old_value": tender.size_bytes, "new_value": input_data.get('size_bytes')}
        if input_data.get('contact_name') != tender.contact_name: return {"field": "contact_name", "old_value": tender.contact_name, "new_value": input_data.get('contact_name')}
        if input_data.get('contact_phone') != tender.contact_phone: return {"field": "contact_phone", "old_value": tender.contact_phone, "new_value": input_data.get('contact_phone')}
        if input_data.get('contact_email') != tender.contact_email: return {"field": "contact_email", "old_value": tender.contact_email, "new_value": input_data.get('contact_email')}
        if input_data.get('contact_fax') != tender.contact_fax: return {"field": "contact_fax", "old_value": tender.contact_fax, "new_value": input_data.get('contact_fax')}
        if input_data.get('address_withdrawal') != tender.address_withdrawal: return {"field": "address_withdrawal", "old_value": tender.address_withdrawal, "new_value": input_data.get('address_withdrawal')}
        if input_data.get('address_bidding') != tender.address_bidding: return {"field": "address_bidding", "old_value": tender.address_bidding, "new_value": input_data.get('address_bidding')}
        if input_data.get('address_opening') != tender.address_opening: return {"field": "address_opening", "old_value": tender.address_opening, "new_value": input_data.get('address_opening')}
        if (input_data.get('category') or {}).get('label', "") != tender.category.label: return {"field": "category", "old_value": tender.category.label, "new_value": (input_data.get('category') or {}).get('label', "")}
        if (input_data.get('kind') or {}).get('name', "") != tender.kind.name: return {"field": "type", "old_value": tender.kind.name, "new_value": (input_data.get('kind') or {}).get('name', "")}
        if (input_data.get('mode') or {}).get('name', "") != tender.mode.name: return{"field": "mode", "old_value": tender.mode.name, "new_value": (input_data.get('mode') or {}).get('name', "")}
        if (input_data.get('procedure') or {}).get('name', "") != tender.procedure.name: return{"field": "procedure", "old_value": tender.procedure.name, "new_value": (input_data.get('procedure') or {}).get('name', "")}
        if (input_data.get('client') or {}).get('name', "") != tender.client.name: return{"field": "client", "old_value": tender.client.name, "new_value": (input_data.get('client') or {}).get('name', "")}
        if input_data.get('title') != tender.title: return {"field": "title", "old_value": tender.title, "new_value": input_data.get('title')}
        if input_data.get('reference') != tender.reference: return {"field": "reference", "old_value": tender.reference, "new_value": input_data.get('reference')}
        if input_data.get('published') != tender.published: return {"field": "published", "old_value": tender.published, "new_value": input_data.get('published')}
        if input_data.get('ebid') != tender.ebid: return {"field": "ebid", "old_value": tender.ebid, "new_value": input_data.get('ebid')}
        if input_data.get('esign') != tender.esign: return {"field": "esign", "old_value": tender.esign, "new_value": input_data.get('esign')}
        if input_data.get('plans_price') != tender.plans_price: return {"field": "plans_price", "old_value": tender.plans_price, "new_value": input_data.get('plans_price')}
        if input_data.get('reserved') != tender.reserved: return {"field": "reserved", "old_value": tender.reserved, "new_value": input_data.get('reserved')}
        if input_data.get('variant') != tender.variant: return {"field": "variant", "old_value": tender.variant, "new_value": input_data.get('variant')}
        if input_data.get('location') != tender.location: return {"field": "location", "old_value": tender.location, "new_value": input_data.get('location')}
        if input_data.get('acronym') != tender.acronym: return {"field": "acronym", "old_value": tender.acronym, "new_value": input_data.get('acronym')}
        if input_data.get('link') != tender.link: return {"field": "link", "old_value": tender.link, "new_value": input_data.get('link')}
        if domains_changed(input_data.get('domains'), tender.domains): return {"field": "domains", "old_value": len(tender.domains.all()), "new_value": len(input_data.get('domains'))}
        return None

    tc = tender_changed(tender, input_data)
    if tc:
        tender_serializer = TenderSerializer(tender, data=input_data)
        tender_serializer.is_valid(raise_exception=True)
        tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)
        set_domains(input_data.get('domains'), tender)
        helper.printMessage('DEBUG', 'm.update_tender', f"+++ Tender updated: {tender.chrono}")
        changes.append(tc)

    return changes


def set_domains(input_data, tender):
    helper.printMessage('TRACE', 'm.set_domains', "### Handling Domains ... ")    
    valid_data = [d for d in input_data if d.get('name')]
    if not valid_data:
        tender.domains.clear()
        helper.printMessage('TRACE', 'm.set_domains', ">>> Domains: Created 0, skipped 0.")
        return 0

    names = [d['name'] for d in valid_data]
    existing_domains = {d.name: d for d in Domain.objects.filter(name__in=names)}

    domains = []
    created_domains = 0
    skipped_domains = 0

    for domain_data in valid_data:
        name = domain_data['name']
        
        if name in existing_domains:
            domain = existing_domains[name]
            skipped_domains += 1
            helper.printMessage('DEBUG', 'm.set_domains', f"--- Domain already exists. Skipping: {name[:C.TRUNCA]}...")
        else:
            helper.printMessage('DEBUG', 'm.set_domains', f"+++ Domain of Activiry to be created: {name[:C.TRUNCA]}...")
            domain_serializer = DomainSerializer(data=domain_data)
            domain_serializer.is_valid(raise_exception=True)
            domain = domain_serializer.save()
            
            existing_domains[name] = domain
            created_domains += 1

        domains.append(domain)

    helper.printMessage('TRACE', 'm.set_domains', f">>> Domains: Created {created_domains}, skipped {skipped_domains}.")

    tender.domains.set(domains)
    return len(domains)


def create_lots(input_data, tender):
    helper.printMessage('TRACE', 'm.create_lots', f"### Handling { ll } Lots ... ")
    lots_data = input_data
    created_lots = 0
    ll = len(lots_data) if lots_data else 0
    if ll > 0:
        helper.printMessage('DEBUG', 'm.create_lots', f"#### Got data for {ll} Lots. ")
        i = 0

        helper.printMessage("TRACE", 'm.create_lots', f"Lots raw data:\n=====================\n{lots_data}\n=====================\n")

        for lot_data in lots_data:
            i += 1
            lot_number_text = lot_data['number']
            helper.printMessage('DEBUG', 'm.create_lots', f"#### Handling Lot {i}/{ll} ... ")
            helper.printMessage("TRACE", 'm.create_lots', f"Lot {i} raw data:\n=====================\n{lot_data}\n=====================")

            lot_category = create_category(lot_data["category"])

            lot = None
            lot_title  = lot_data.get('title')
            lot_number = lot_data.get('number', 1)
            helper.printMessage('TRACE', 'm.create_lots', "#### Handling Lot details ... ")
            if lot_title:
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
        cat = lot_data.get('category')
        dict_cat_label = cat.get('label') if cat else ""
        obj_cat_label = lot.category.label if lot.category else None
        if dict_cat_label != obj_cat_label: return "category"
        attrs = ("number", "title", "estimate", "bond", "variant", "reserved")        
        return next((attr for attr in attrs if lot_data.get(attr) != getattr(lot, attr)), None)

    def qualifs_changed(qualifs, data):
        qualif_list = list(qualifs.all())        
        if len(data) != len(qualif_list): return True
        return any(
            q_data.get("name") != qualif.name 
            for q_data, qualif in zip(data, qualif_list)
        )

    def agrements_changed(agrements, data):
        agrement_list = list(agrements.all())        
        if len(data) != len(agrement_list): return True
        return any(
            q_data.get("name") != agrement.name 
            for q_data, agrement in zip(data, agrement_list)
        )

    def samples_changed(samples, data):
        sample_list = list(samples.all())
        if len(data) != len(sample_list): return True
        return any(
            s_data.get("when") != sample.when or s_data.get("description") != sample.description
            for s_data, sample in zip(data, sample_list)
        )

    def meetings_changed(meetings, data):
        meeting_list = list(meetings.all())
        if len(data) != len(meeting_list): return True
        return any(
            s_data.get("when") != meeting.when or s_data.get("description") != meeting.description
            for s_data, meeting in zip(data, meeting_list)
        )

    def visits_changed(visits, data):
        visit_list = list(visits.all())
        if len(data) != len(visit_list): return True
        return any(
            s_data.get("when") != visit.when or s_data.get("description") != visit.description
            for s_data, visit in zip(data, visit_list)
        )

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
    
    tender.save()
    
    return changes


def log_changes(changed_fields, tender):
    # Log changed fields, if any
    if len(changed_fields) > 0 :
        target_date = datetime.now() - timedelta(days=C.PORTAL_DCE_PAST_DAYS)
        target_date = target_date.date()
        tender_date = tender.deadline.date()

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
    



