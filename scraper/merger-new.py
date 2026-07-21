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
            for l in ll:
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

    category, client, kind, mode, procedure = create_cckmp(category_data, client_data, kind_data, mode_data, procedure_data)


    ## Handle Tender base details
    tender = Tender.objects.filter(chrono=chrono).first()

    if tender is None:
        ### Create a new Tender
        tender = create_tender(validated_data, category, client, kind, mode, procedure)
        if tender: 
            domains = set_domains(domains_data, tender)
            created_lots = create_lots(lots_data, tender)
    else: 
        ### Update existing Tender
        lots_qs = tender.lots.all()##.prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
        numbers_list = [lot['number'] for lot_data in lots_data]
        numbers_list_qs = list(lots_qs.values_list('number', flat=True))

        numbers_to_create = list(set(numbers_list) - set(numbers_list_qs))
        numbers_to_update = list(set(numbers_list) & set(numbers_list_qs))
        numbers_to_delete = list(set(numbers_list_qs) - set(numbers_list))

        if len(numbers_to_create) > 0 or len(numbers_to_delete) > 0:
            # TODO: Record change
            pass

        dll = delete_lots_list(numbers_to_delete, tender)
        helper.printMessage('TRACE', 'm.save', f">>> Deleted Lots and objects: \n{dll}\n")

        data_to_create = [obj for obj in lots_data if obj.get('number') in set(numbers_to_create)]
        create_lots(data_to_create, tender)

        data_to_update = [obj for obj in lots_data if obj.get('number') in set(numbers_to_update)]
        update_lots(numbers_to_update, data_to_update, tender)


        ll = len(lots_data) if lots_data else 0
        if ll > 0:
            for lot_data in lots_data:
                lot_number = lot_data.get('number')
                lot_number_qs = lots.qs.filter(number=lot_number)
                if any(lot.number == lot_number for lot in lots_qs):
                    print("lot_data is found in lots_qs!")

    

    # Step x: Handle Domains (many-to-many)
    helper.printMessage('TRACE', 'm.save', "### Handling Domains ... ")
    domains_data = formatted_data['domains']
    json_domain_keys = set()
    for domain_data in domains_data:
        name = domain_data.get('name')
        domain = None
        if name and Domain.objects.filter(name=name).exists():
            domain = Domain.objects.get(name=name)
            domain_serializer = DomainSerializer(domain, data=domain_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Domain of Activiry already exists. Skipping.")
        else:
            domain_serializer = DomainSerializer(data=domain_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Domain of Activiry to be created: {name[:C.TRUNCA]}...")
            domain_serializer.is_valid(raise_exception=True)
            domain = domain_serializer.save()
            
            if not tender_create:
                change = {"field": "domain" , "old_value": "", "new_value": domain.name}
                changed_fields.append(change)
        json_domain_keys.add((domain.name))
        RelDomainTender.objects.get_or_create(domain=domain, tender=tender)


    # Remove domains not in JSON
    helper.printMessage('TRACE', 'm.save', "#### Handling Domains relationships ... ")
    existing_domains = set(tender.domains.values_list('name'))
    domains_to_remove = existing_domains - json_domain_keys
    for name in domains_to_remove:
        domain = Domain.objects.filter(name=name).first()
        if domain:
            helper.printMessage('DEBUG', 'm.save', f"#### Unlinking Tender {tender.chrono} and Domain {domain.name} ... ")
            RelDomainTender.objects.filter(domain=domain, tender=tender).delete()
            if not tender_create: 
                change = {"field": "domain" , "old_value": domain.name, "new_value": ""}
                changed_fields.append(change)


    # Step x: Handle Lots
    helper.printMessage('TRACE', 'm.save', "### Handling Lots ... ")
    lots_data = formatted_data["lots"]
    json_lot_keys = set()
    new_lots = []

    estimate_total, bond_total = 0, 0
    reserved_tender, variant_tender = False, False
    ll = len(lots_data) if lots_data else 0
    if ll > 0:
        helper.printMessage('TRACE', 'm.save', f"#### Got data for {ll} Lots. ")
        i = 0
        l1 = lots_data[0]
        reserved_tender = l1["reserved"]
        variant_tender = l1["variant"]

        helper.printMessage("TRACE", 'm.save', f"Lots raw data:\n=====================\n{lots_data}\n=====================\n")

        for lot_data in lots_data:
            i += 1
            lot_number_text = lot_data['number']
            lot_data['number'] = lottify(lot_number_text, i)
            helper.printMessage('DEBUG', 'm.save', f"#### Handling Lot {i}/{ll} ... ")
            helper.printMessage("TRACE", 'm.save', f"Lot {i} raw data:\n=====================\n{lot_data}\n=====================\n")
            # Update Tender fields
            estimate_total += lot_data["estimate"]
            bond_total += lot_data["bond"]

            # Handle nested Category for Lot
            lot_category_data = lot_data["category"]
            lot_category = None
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Category ... ")
            if lot_category_data:
                label = lot_category_data.get('label')
                if label and Category.objects.filter(label=label).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Lot Category exists. Skipping.")
                    lot_category = Category.objects.get(label=label)
                    lot_category_serializer = CategorySerializer(lot_category, data=lot_category_data, partial=True)
                else:
                    lot_category_serializer = CategorySerializer(data=lot_category_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Lot Category to be created: {label[:C.TRUNCA]}...")
                    lot_category_serializer.is_valid(raise_exception=True)
                    lot_category = lot_category_serializer.save()
                    if not tender_create: 
                        change = {"field": "category" , "old_value": "", "new_value": lot_category.label}
                        changed_fields.append(change)

            meetings_data = lot_data['meetings']
            samples_data = lot_data['samples']
            visits_data = lot_data['visits']
            agrements_data = lot_data['agrements']
            qualifs_data = lot_data['qualifs']

            lot_data['category'] = lot_category

            lot_title  = lot_data.get('title')
            lot_number = lot_data.get('number', 1)
            lot = None
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot details ... ")
            if lot_title and Lot.objects.filter(title=lot_title, number=lot_number, tender=tender).exists():
                lot = Lot.objects.get(title=lot_title, number=lot_number, tender=tender,)
                lot_serializer = LotSerializer(lot, data=lot_data, partial=True)
                if lot_serializer.is_valid(): lot_serializer.save()
            else:
                lot_serializer = LotSerializer(data=lot_data)
                helper.printMessage('TRACE', 'm.save', f"#### Lot to be created: {lot_title[:C.TRUNCA]}...")
                lot_serializer.is_valid(raise_exception=True)
                lot = lot_serializer.save(tender=tender, category=lot_category)
                if not tender_create:
                    change = {"field": "lot" , "old_value": "", "new_value": lot.title}
                    changed_fields.append(change)

            json_lot_keys.add((lot.title, lot.number))

            # Handle Meetings
            json_meeting_keys = set()
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Meetings ... ")
            for meeting_data in meetings_data:
                when = ensure_dt_rabat(meeting_data.get('when'))
                description = meeting_data.get('description')
                json_meeting_keys.add((when, description))
                meeting = None
                if when and Meeting.objects.filter(when=when, lot=lot).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Meeting exists. Skipping.")
                    meeting = Meeting.objects.get(when=when, lot=lot)
                    meeting_serializer = MeetingSerializer(meeting, data=meeting_data, partial=True)
                else:
                    meeting_serializer = MeetingSerializer(data=meeting_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Meeting to be created: {when}")
                    meeting_serializer.is_valid(raise_exception=True)
                    meeting_serializer.save(lot=lot)
                    if not tender_create: 
                        change = {"field": "meeting" , "old_value": "", "new_value": when.strftime("%Y-%m-%d %H:%M") if when else "-"}
                        changed_fields.append(change)

            # Remove Meetings not in JSON
            helper.printMessage('TRACE', 'm.save', "#### Handling Meetings relationships ... ")
            existing_meetings = set(lot.meetings.values_list('when', 'description'))
            meetings_to_remove = existing_meetings - json_meeting_keys
            for when, description in meetings_to_remove:
                Meeting.objects.filter(when=when, description=description, lot=lot).delete()
                if not tender_create:
                    change = {"field": "meeting" , "old_value": when.strftime("%Y-%m-%d %H:%M") if when else "-", "new_value": ""}
                    changed_fields.append(change)

            # Handle Samples
            json_sample_keys = set()
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Samples ... ")
            for sample_data in samples_data:
                sample_data['when'] = ensure_dt_rabat(sample_data.get('when'))
                when = sample_data.get('when')
                description = sample_data.get('description')
                json_sample_keys.add((when, description))
                sample = None
                if when and Sample.objects.filter(when=when, lot=lot).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Sample exists. Skipping.")
                    sample = Sample.objects.get(when=when, lot=lot)
                    sample_serializer = SampleSerializer(sample, data=sample_data, partial=True)
                else:
                    sample_serializer = SampleSerializer(data=sample_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Sample to be created: {when}")
                    sample_serializer.is_valid(raise_exception=True)
                    sample_serializer.save(lot=lot)
                    if not tender_create: 
                        change = {"field": "sample" , "old_value": "", "new_value": when.strftime("%Y-%m-%d %H:%M") if when else "-"}
                        changed_fields.append(change)

            # Remove Samples not in JSON
            helper.printMessage('TRACE', 'm.save', "#### Handling Samples relationships ... ")
            existing_samples = set(lot.samples.values_list('when', 'description'))
            samples_to_remove = existing_samples - json_sample_keys
            for when, description in samples_to_remove:
                Sample.objects.filter(when=when, description=description, lot=lot).delete()
                if not tender_create: 
                    change = {"field": "sample" , "old_value": when.strftime("%Y-%m-%d %H:%M") if when else "-", "new_value": ""}
                    changed_fields.append(change)

            # Handle Visits
            json_visit_keys = set()
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Visits ... ")
            for visit_data in visits_data:
                when = ensure_dt_rabat(visit_data.get('when'))
                description = visit_data.get('description')
                json_visit_keys.add((when, description))
                visit = None
                if when and Visit.objects.filter(when=when, lot=lot).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Visit exists. Skipping.")
                    visit = Visit.objects.get(when=when, lot=lot)
                    visit_serializer = VisitSerializer(visit, data=visit_data, partial=True)
                else:
                    visit_serializer = VisitSerializer(data=visit_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Visit to be created: {when}")
                    visit_serializer.is_valid(raise_exception=True)
                    visit_serializer.save(lot=lot)
                    if not tender_create: 
                        change = {"field": "visit" , "old_value": "", "new_value": when.strftime("%Y-%m-%d %H:%M") if when else "-"}
                        changed_fields.append(change)

            # Remove Visits not in JSON
            helper.printMessage('TRACE', 'm.save', "#### Handling Visits relationships ... ")
            existing_visits = set(lot.visits.values_list('when', 'description'))
            visits_to_remove = existing_visits - json_visit_keys
            for when, description in visits_to_remove:
                Visit.objects.filter(when=when, description=description, lot=lot).delete()
                if not tender_create: 
                    change = {"field": "visit" , "old_value": when.strftime("%Y-%m-%d %H:%M") if when else "-", "new_value": ""}
                    changed_fields.append(change)

            # Handle Agrements (many-to-many)
            json_agrement_keys = set()
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Agrements ... ")
            for agrement_data in agrements_data:
                name = agrement_data.get('name')
                agrement = None
                if name and Agrement.objects.filter(name=name).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Agrement exists. Skipping.")
                    agrement = Agrement.objects.get(name=name)
                    agrement_serializer = AgrementSerializer(agrement, data=agrement_data, partial=True)
                else:
                    agrement_serializer = AgrementSerializer(data=agrement_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Agrement to be created: {name[:C.TRUNCA]}...")
                    agrement_serializer.is_valid(raise_exception=True)
                    agrement = agrement_serializer.save()
                    if not tender_create: 
                        change = {"field": "agrement" , "old_value": "", "new_value": agrement.name}
                        changed_fields.append(change)
                        
                json_agrement_keys.add((agrement.short, agrement.name))
                RelAgrementLot.objects.get_or_create(agrement=agrement, lot=lot)

            # Remove Agrements not in JSON
            helper.printMessage('TRACE', 'm.save', "#### Handling Agrements relationships ... ")
            existing_agrements = set(lot.agrements.values_list('short', 'name'))
            agrements_to_remove = existing_agrements - json_agrement_keys
            for short, name in agrements_to_remove:
                agrement = Agrement.objects.filter(short=short, name=name).first()
                if agrement:
                    RelAgrementLot.objects.filter(agrement=agrement, lot=lot).delete()
                    if not tender_create: 
                        change = {"field": "agrement" , "old_value": agrement.name, "new_value": ""}
                        changed_fields.append(change)

            # Handle Qualifs (many-to-many)
            json_qualif_keys = set()
            helper.printMessage('TRACE', 'm.save', "#### Handling Lot Qualifs ... ")
            for qualif_data in qualifs_data:
                short = qualif_data.get('short')
                name = qualif_data.get('name')
                qualif = None
                if name and Qualif.objects.filter(name=name).exists():
                    helper.printMessage('TRACE', 'm.save', "#### Qualif exists. Skipping.")
                    qualif = Qualif.objects.get(name=name)
                    qualif_serializer = QualifSerializer(qualif, data=qualif_data, partial=True)
                else:
                    qualif_serializer = QualifSerializer(data=qualif_data)
                    helper.printMessage('TRACE', 'm.save', f"#### Qualif to be created: {name[:C.TRUNCA]}...")
                    qualif_serializer.is_valid(raise_exception=True)
                    qualif = qualif_serializer.save()
                    if not tender_create:
                        change = {"field": "qualif" , "old_value": "", "new_value": qualif.name}
                        changed_fields.append(change)

                json_qualif_keys.add((qualif.short, qualif.name))
                RelQualifLot.objects.get_or_create(qualif=qualif, lot=lot)

            # Remove Qualifs not in JSON
            helper.printMessage('TRACE', 'm.save', "#### Handling Qualifs relationships ... ")
            existing_qualifs = set(lot.qualifs.values_list('short', 'name'))
            qualifs_to_remove = existing_qualifs - json_qualif_keys
            for short, name in qualifs_to_remove:
                qualif = Qualif.objects.filter(name=name).first()
                if qualif:
                    RelQualifLot.objects.filter(qualif=qualif, lot=lot).delete()
                    if not tender_create:
                        change = {"field": "qualif" , "old_value": qualif.name, "new_value": ""}
                        changed_fields.append(change)

            new_lots.append(lot)
    
    # Remove Lots not in JSON
    helper.printMessage('TRACE', 'm.save', "#### Handling Lots relationships ... ")
    existing_lots = set(tender.lots.values_list('title', 'number'))
    lots_to_remove = existing_lots - json_lot_keys
    for title, number in lots_to_remove:
        Lot.objects.filter(title=title, number=number, tender=tender).delete()
        if not tender_create:
            change = {"field": "lot" , "old_value": title, "new_value": ""}
            changed_fields.append(change)

    # Log changed fields, if any
    target_date = datetime.now() - timedelta(days=C.PORTAL_DCE_PAST_DAYS)
    target_date = target_date.date()
    tender_date = tender.deadline.date()

    if changed_fields:
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

    
    if tender_create:
        if tender_date > target_date:
            try:
                helper.printMessage('TRACE', 'm.save', "#### Adding DCE request for Tender ... ")
                f2d, _ = FileToGet.objects.update_or_create(tender=tender)
            except:
                helper.printMessage('WARN', 'm.save', "---- Exception raised saving DCE request.")
                traceback.print_exc()
    else: # Update return boolean: True=Created, False=Updated, None=None
        if len(changed_fields) == 0:
            helper.printMessage('DEBUG', 'm.save', f"No change was found for {tender.chrono}" )
            tender_create = None


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
    helper.printMessage('TRACE', 'm.save', "### Handling Category ... ")
    if category_data:        
        label = category_data.get('label')
        if label:
            category = Category.objects.filter(label=label).first()
            if category == None:
                category_serializer.is_valid(raise_exception=True)
                category = category_serializer.save()
                helper.printMessage('TRACE', 'm.save', f"+++ Created Category: {category.label}")
            else:
                helper.printMessage('TRACE', 'm.save', f"--- Category found. Skipping: {category.label}")
    
    client = None
    helper.printMessage('TRACE', 'm.save', "### Handling Client ... ")
    if client_data:        
        name = client_data.get('name')
        if name:
            client = Client.objects.filter(name=name).first()
            if client == None:
                client_serializer.is_valid(raise_exception=True)
                client = client_serializer.save()
                helper.printMessage('TRACE', 'm.save', f"+++ Created Client: {client.name}")
            else:
                helper.printMessage('TRACE', 'm.save', f"--- Client found. Skipping: {client.name}")
    
    kind = None
    helper.printMessage('TRACE', 'm.save', "### Handling Kind ... ")
    if kind_data:        
        name = kind_data.get('name')
        if name:
            kind = Kind.objects.filter(name=name).first()
            if kind == None:
                kind_serializer.is_valid(raise_exception=True)
                kind = kind_serializer.save()
                helper.printMessage('TRACE', 'm.save', f"+++ Created Kind: {kind.name}")
            else:
                helper.printMessage('TRACE', 'm.save', f"--- Kind found. Skipping: {kind.name}")
    
    mode = None
    helper.printMessage('TRACE', 'm.save', "### Handling Mode ... ")
    if mode_data:        
        name = mode_data.get('name')
        if name:
            mode = Mode.objects.filter(name=name).first()
            if mode == None:
                mode_serializer.is_valid(raise_exception=True)
                mode = mode_serializer.save()
                helper.printMessage('TRACE', 'm.save', f"+++ Created Mode: {mode.name}")
            else:
                helper.printMessage('TRACE', 'm.save', f"--- Mode found. Skipping: {mode.name}")
    
    procedure = None
    helper.printMessage('TRACE', 'm.save', "### Handling Procedure ... ")
    if procedure_data:        
        name = procedure_data.get('name')
        if name:
            procedure = Procedure.objects.filter(name=name).first()
            if procedure == None:
                procedure_serializer.is_valid(raise_exception=True)
                procedure = procedure_serializer.save()
                helper.printMessage('TRACE', 'm.save', f"+++ Created Procedure: {procedure.name}")
            else:
                helper.printMessage('TRACE', 'm.save', f"--- Procedure found. Skipping: {procedure.name}")
    

    return category, client, kind, mode, procedure


def create_tender(input_data, category, client, kind, mode, procedure):
    validated_data = input_data
    chrono = validated_data.get('chrono')
    tender = None
    helper.printMessage('TRACE', 'm.save', "### Handling Tender ... ")
    tender_serializer = TenderSerializer(data=validated_data, category=category, client=client, kind=kind, mode=mode, procedure=procedure )
    helper.printMessage('DEBUG', 'm.save', f"+++ Tender to be created: {chrono}")
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)

    return tender


def set_domains(input_data, tender):
    helper.printMessage('TRACE', 'm.save', "### Handling Domains ... ")
    domains_data = input_data
    created_domains, skipped_domains = 0, 0
    domains = []
    for domain_data in domains_data:
        name = domain_data.get('name')
        if name and name != "":
            domain = Domain.objects.filter(name=name).first()
            if domain:
                skipped_domains += 1
                helper.printMessage('DEBUG', 'm.save', f"--- Domain already exists. Skipping: {name[:C.TRUNCA]}...")
            else:
                helper.printMessage('DEBUG', 'm.save', f"+++ Domain of Activiry to be created: {name[:C.TRUNCA]}...")
                domain_serializer = DomainSerializer(data=domain_data)
                domain_serializer.is_valid(raise_exception=True)
                domain = domain_serializer.save()
                created_domains += 1
            domains.append(domain)
    helper.printMessage('TRACE', 'm.save', f">>> Domains: Created {created_domains}, skipped {skipped_domains}.")

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
            lot_data['number'] = lottify(lot_number_text, i)
            helper.printMessage('DEBUG', 'm.create_lots', f"#### Handling Lot {i}/{ll} ... ")
            helper.printMessage("TRACE", 'm.create_lots', f"Lot {i} raw data:\n=====================\n{lot_data}\n=====================\n")


            # Handle nested Category for Lot
            lot_category = create_category_if_none(lot_data["category"])

            # Create Lot
            lot = None
            lot_title  = lot_data.get('title')
            lot_number = lot_data.get('number', 1)
            helper.printMessage('TRACE', 'm.create_lots', "#### Handling Lot details ... ")
            if lot_title:
                if not Lot.objects.filter(tender=tender, title=lot_title, number=lot_number).exists():
                    lot_serializer = LotSerializer(data=lot_data)
                    helper.printMessage('TRACE', 'm.create_lots', f"+++ Lot to be created: {lot_title[:C.TRUNCA]}...")
                    lot_serializer.is_valid(raise_exception=True)
                    lot = lot_serializer.create_lots(tender=tender, category=lot_category)


            created_samples = create_samples(lot_data['samples'], lot)
            created_meetings = create_meetings(lot_data['meetings'], lot)
            created_visits = create_visits(lot_data['visits'], lot)
            created_qualifs = create_qualifs(lot_data['qualifs'], lot)
            created_agrements = create_agrements(lot_data['agrements'], lot)

            helper.printMessage('TRACE', 'm.create_lots', f">>> Created: {created_samples} Samples, {created_meetings} Meetings, {created_visits} Visits, {created_qualifs} Qualifs, {created_agrements} Agrements, ")


def create_category_if_none(input_data):
    lot_category_data = input_data
    lot_category = None
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Category ... ")
    if lot_category_data:
        label = lot_category_data.get('label')
        if label:
            if not Category.objects.filter(label=label).exists():
                helper.printMessage('TRACE', 'm.save', f"++++ Lot Category to be created: {label[:C.TRUNCA]}...")
                lot_category_serializer = CategorySerializer(data=lot_category_data)                    
                lot_category_serializer.is_valid(raise_exception=True)
                lot_category = lot_category_serializer.save()
            else:
                helper.printMessage('TRACE', 'm.save', f"---- Lot Category exists. Skipping: : {label[:C.TRUNCA]}...")
    return lot_category


def create_samples(input_data, lot):
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Samples ... ")
    samples_data = input_data
    created_samples = 0
    for sample_data in samples_data:
        sample_data['when'] = ensure_dt_rabat(sample_data.get('when'))
        when = sample_data.get('when')
        description = sample_data.get('description')
        if when:
            if not Sample.objects.filter(when=when, lot=lot).exists():
                sample_serializer = SampleSerializer(data=sample_data)
                helper.printMessage('TRACE', 'm.save', f"++++ Sample to be created: {when}")
                sample_serializer.is_valid(raise_exception=True)
                sample_serializer.save(lot=lot)
                created_samples += 1
    return created_samples


def create_meetings(input_data, lot):
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Meetings ... ")
    meetings_data = input_data
    created_meetings = 0
    for meeting_data in meetings_data:
        meeting_data['when'] = ensure_dt_rabat(meeting_data.get('when'))
        when = meeting_data.get('when')
        description = meeting_data.get('description')
        if when:
            if not Meeting.objects.filter(when=when, lot=lot).exists():
                meeting_serializer = MeetingSerializer(data=meeting_data)
                helper.printMessage('TRACE', 'm.save', f"++++ Meeting to be created: {when}")
                meeting_serializer.is_valid(raise_exception=True)
                meeting_serializer.save(lot=lot)
                created_meetings += 1
    return created_meetings


def create_visits(input_data, lot):
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Visitss ... ")
    visits_data = input_data
    created_visits = 0
    for visit_data in visits_data:
        visit_data['when'] = ensure_dt_rabat(visit_data.get('when'))
        when = visit_data.get('when')
        description = visit_data.get('description')
        if when:
            if not Visits.objects.filter(when=when, lot=lot).exists():
                visit_serializer = VisitsSerializer(data=visit_data)
                helper.printMessage('TRACE', 'm.save', f"++++ Visits to be created: {when}")
                visit_serializer.is_valid(raise_exception=True)
                visit_serializer.save(lot=lot)
                created_visits += 1
    return created_visits


def create_qualifs(input_data, lot):
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Qualifs ... ")
    qualifs_data = input_data
    qualifs = []
    for qualif_data in qualifs_data:
        short = qualif_data.get('short')
        name = qualif_data.get('name')
        qualif = None
        if name:
            if not Qualif.objects.filter(name=name).exists():
                qualif_serializer = QualifSerializer(data=qualif_data)
                helper.printMessage('TRACE', 'm.save', f"++++ Qualif to be created: {name[:C.TRUNCA]}...")
                qualif_serializer.is_valid(raise_exception=True)
                qualif = qualif_serializer.save()
                qualifs.append(qualif)
            else:
                helper.printMessage('TRACE', 'm.save', "---- Qualif exists. Skipping.")                
    lot.qualifs.set(qualifs)
    return len(qualifs)


def create_agrements(input_data, lot):
    helper.printMessage('TRACE', 'm.save', "#### Handling Lot Agrements ... ")
    agrements_data = input_data
    agrements = []
    for agrement_data in agrements_data:
        short = agrement_data.get('short')
        name = agrement_data.get('name')
        agrement = None
        if name:
            if not Agrement.objects.filter(name=name).exists():
                agrement_serializer = AgrementSerializer(data=agrement_data)
                helper.printMessage('TRACE', 'm.save', f"++++ Agrement to be created: {name[:C.TRUNCA]}...")
                agrement_serializer.is_valid(raise_exception=True)
                agrement = agrement_serializer.save()
                agrements.append(agrement)
            else:
                helper.printMessage('TRACE', 'm.save', "---- Agrement exists. Skipping.")
    
    lot.agrements.set(agrements)
    return len(agrements)


def lottify(lot_no_str, default_int):
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
    lots_qs = tender.lots.filter(number__in=numbers).prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
    for lot_qs in lots_qs:
        lot_data = next((obj for obj in set(lots_data) if obj.get('number') == lot_qs.number), None)
        if lot_data:
            deleted_agrements = lot_qs.agrements.all().delete()
            deleted_qualifs   = lot_qs.qualifs.all().delete()
            deleted_samples   = lot_qs.samples.all().delete()
            deleted_meetings  = lot_qs.meetings.all().delete()
            deleted_visits    = lot_qs.visits.all().delete()

            created_samples   = create_samples(lot_data['samples'], lot)
            created_meetings  = create_meetings(lot_data['meetings'], lot)
            created_visits    = create_visits(lot_data['visits'], lot)
            created_qualifs   = create_qualifs(lot_data['qualifs'], lot)
            created_agrements = create_agrements(lot_data['agrements'], lot)
    return 0
