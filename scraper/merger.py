import traceback
from rest_framework import serializers
from django.db import transaction
from datetime import datetime, timedelta, timezone

from scraper import constants as C
from scraper import helper
from base.models import (
    Tender, Lot, Agrement, Qualif, Kind, Domain, Mode, Procedure, 
    Category, Change, Client, Meeting, Sample, Visit, FileToGet,
    RelAgrementLot, RelDomainTender, RelQualifLot
)
from scraper.serializers import (
    TenderSerializer, LotSerializer, MeetingSerializer, SampleSerializer, VisitSerializer, 
    ModeSerializer, ProcedureSerializer, DomainSerializer, 
    CategorySerializer, ChangeSerializer, ClientSerializer, KindSerializer, AgrementSerializer, 
    QualifSerializer, RelDomainTenderSerializer, RelAgrementLotSerializer, 
    RelQualifLotSerializer
)



def format(tender_json):

    helper.printMessage('INFO', 'm.format', "### Started formatting Tender data ...")
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


@transaction.atomic
def save(tender_data):    

    formatted_data = format(tender_data)
    helper.printMessage('INFO', 'm.save', f"### Started saving formatted Tender data {formatted_data["chrono"]}")

    # Step x: Validate the JSON using TenderSerializer
    tender_serializer = TenderSerializer(data=formatted_data)
    tender_serializer.is_valid(raise_exception=True)
    validated_data = tender_serializer.validated_data

    changed_fields = []

    # Step x: Handle foreign key relationships (category, client, kind, mode, procedure)
    category_data = formatted_data['category']
    client_data = formatted_data['client']
    kind_data = formatted_data['kind']
    mode_data = formatted_data['mode']
    procedure_data = formatted_data['procedure']

    ## Handle Category
    category = None
    helper.printMessage('TRACE', 'm.save', "### Handling Category ... ")
    if category_data:
        helper.printMessage('TRACE', 'm.save', "+++ Got Category data. Analyzing ... ")
        label = category_data.get('label')
        if label and Category.objects.filter(label=label).exists():
            category = Category.objects.get(label=label)
            category_serializer = CategorySerializer(category, data=category_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Category already exists. Skipping.")
        else:
            category_serializer = CategorySerializer(data=category_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Category to be created: {label[:C.TRUNCA]}...")
            category_serializer.is_valid(raise_exception=True)
            category = category_serializer.save()
            change = {"field": "category" , "old_value": "", "new_value": category.label}
            changed_fields.append(change)

    else:
        helper.printMessage('WARN', 'm.save', "--- Could not pop out Category data!", 1)

    ## Handle Client
    client = None
    helper.printMessage('TRACE', 'm.save', "### Handling Client ... ")
    if client_data:
        name = client_data.get('name')
        if name and Client.objects.filter(name=name).exists():
            client = Client.objects.get(name=name)
            client_serializer = ClientSerializer(client, data=client_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Client already exists. Skipping.")
        else:
            client_serializer = ClientSerializer(data=client_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Client to be created: {name[:C.TRUNCA]}...")
            client_serializer.is_valid(raise_exception=True)
            client = client_serializer.save()
            change = {"field": "client" , "old_value": "", "new_value": client.name}
            changed_fields.append(change)

    ## Handle Kind
    kind = None
    helper.printMessage('TRACE', 'm.save', "### Handling Type ... ")
    if kind_data:
        name = kind_data.get('name')
        if name and Kind.objects.filter(name=name).exists():
            kind = Kind.objects.get(name=name)
            kind_serializer = KindSerializer(kind, data=kind_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Procedure Type already exists. Skipping.")
        else:
            kind_serializer = KindSerializer(data=kind_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Procedure Type to be created: {name[:C.TRUNCA]}...")
            kind_serializer.is_valid(raise_exception=True)
            kind = kind_serializer.save()
            change = {"field": "kind" , "old_value": "", "new_value": kind.name}
            changed_fields.append(change)

    ## Handle Mode
    mode = None
    helper.printMessage('TRACE', 'm.save', "### Handling Mode ... ")
    if mode_data:
        name = mode_data.get('name')
        if name and Mode.objects.filter(name=name).exists():
            mode = Mode.objects.get(name=name)
            mode_serializer = ModeSerializer(mode, data=mode_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Awarding Mode already exists. Skipping.")
        else:
            mode_serializer = ModeSerializer(data=mode_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Awarding Mode to be created: {name[:C.TRUNCA]}...")
            mode_serializer.is_valid(raise_exception=True)
            mode = mode_serializer.save()
            change = {"field": "mode" , "old_value": "", "new_value": mode.name}
            changed_fields.append(change)

    ## Handle Procedure
    procedure = None
    helper.printMessage('TRACE', 'm.save', "### Handling Procedure ... ")
    if procedure_data:
        name = procedure_data.get('name')
        if name and Procedure.objects.filter(name=name).exists():
            procedure = Procedure.objects.get(name=name)
            procedure_serializer = ProcedureSerializer(procedure, data=procedure_data, partial=True)
            helper.printMessage('DEBUG', 'm.save', "+++ Procedure already exists. Skipping.")
        else:
            procedure_serializer = ProcedureSerializer(data=procedure_data)
            helper.printMessage('DEBUG', 'm.save', f"+++ Procedure to be created: {name[:C.TRUNCA]}...")
            procedure_serializer.is_valid(raise_exception=True)
            procedure = procedure_serializer.save()
            change = {"field": "procedure" , "old_value": "", "new_value": procedure.name}
            changed_fields.append(change)


    # Step x: Create or update Tender
    chrono = validated_data.get('chrono')
    tender = None
    tender_create = False
    helper.printMessage('TRACE', 'm.save', "### Handling Tender ... ")
    if chrono and Tender.objects.filter(chrono=chrono).exists():
        tender = Tender.objects.filter(chrono=chrono).first()
        tender_serializer = TenderSerializer(tender, data=validated_data, partial=True)
        for field, new_value in validated_data.items():
            current_value = getattr(tender, field)
            if current_value != new_value:
                keep_change = True
                if field == 'size_bytes':
                    if current_value == None or new_value == None:
                        keep_change = False
                if keep_change:
                    change = { "field": field , "old_value": str(current_value), "new_value": str(new_value)}
                    changed_fields.append(change)
        helper.printMessage('INFO', 'm.save', "+++ Tender already exists. Updating.")
    else:
        tender_serializer = TenderSerializer(data=validated_data)
        helper.printMessage('INFO', 'm.save', f"+++ Tender to be created: {chrono}")
        changed_fields = []
        tender_create = True
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)


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

    for lot_data in lots_data:
        i += 1
        helper.printMessage('DEBUG', 'm.save', f"#### Handling Lot {i}/{ll} ... ")
        # Update Tender fields
        estimate_total += lot_data["estimate"]
        bond_total += lot_data["bond"]

        # Handle nested Category for Lot
        lot_category_data = lot_data["category"]
        lot_category = None
        helper.printMessage('DEBUG', 'm.save', "#### Handling Lot Category ... ")
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

        # Match Lot by title
        lot_title = lot_data.get('title')
        lot = None
        helper.printMessage('TRACE', 'm.save', "#### Handling Lot details ... ")
        if lot_title and Lot.objects.filter(title=lot_title, tender=tender).exists():
            helper.printMessage('TRACE', 'm.save', "#### Lot exists. Skipping.")
            lot = Lot.objects.get(title=lot_title, tender=tender)
            lot_serializer = LotSerializer(lot, data=lot_data, partial=True)
        else:
            lot_serializer = LotSerializer(data=lot_data)
            helper.printMessage('TRACE', 'm.save', f"#### Lot to be created: {lot_title[:C.TRUNCA]}...")
            lot_serializer.is_valid(raise_exception=True)
            lot = lot_serializer.save(tender=tender)
            if not tender_create:
                change = {"field": "lot" , "old_value": "", "new_value": lot.title}
                changed_fields.append(change)

        json_lot_keys.add((lot.title, lot.number))

        # Handle Meetings
        json_meeting_keys = set()
        helper.printMessage('TRACE', 'm.save', "#### Handling Lot Meetings ... ")
        for meeting_data in meetings_data:
            when = meeting_data.get('when')
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
                    change = {"field": "meeting" , "old_value": "", "new_value": str(when)}
                    changed_fields.append(change)

        # Remove Meetings not in JSON
        helper.printMessage('TRACE', 'm.save', "#### Handling Meetings relationships ... ")
        existing_meetings = set(lot.meetings.values_list('when', 'description'))
        meetings_to_remove = existing_meetings - json_meeting_keys
        for when, description in meetings_to_remove:
            Meeting.objects.filter(when=when, description=description, lot=lot).delete()
            if not tender_create:
                change = {"field": "meeting" , "old_value": str(when), "new_value": ""}
                changed_fields.append(change)

        # Handle Samples
        json_sample_keys = set()
        helper.printMessage('TRACE', 'm.save', "#### Handling Lot Samples ... ")
        for sample_data in samples_data:
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
                    change = {"field": "sample" , "old_value": "", "new_value": str(when)}
                    changed_fields.append(change)

        # Remove Samples not in JSON
        helper.printMessage('TRACE', 'm.save', "#### Handling Samples relationships ... ")
        existing_samples = set(lot.samples.values_list('when', 'description'))
        samples_to_remove = existing_samples - json_sample_keys
        for when, description in samples_to_remove:
            Sample.objects.filter(when=when, description=description, lot=lot).delete()
            if not tender_create: 
                change = {"field": "sample" , "old_value": str(when), "new_value": ""}
                changed_fields.append(change)

        # Handle Visits
        json_visit_keys = set()
        helper.printMessage('TRACE', 'm.save', "#### Handling Lot Visits ... ")
        for visit_data in visits_data:
            when = visit_data.get('when')
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
                    change = {"field": "visit" , "old_value": "", "new_value": str(when)}
                    changed_fields.append(change)

        # Remove Visits not in JSON
        helper.printMessage('TRACE', 'm.save', "#### Handling Visits relationships ... ")
        existing_visits = set(lot.visits.values_list('when', 'description'))
        visits_to_remove = existing_visits - json_visit_keys
        for when, description in visits_to_remove:
            Visit.objects.filter(when=when, description=description, lot=lot).delete()
            if not tender_create: 
                change = {"field": "visit" , "old_value": str(when), "new_value": ""}
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
    target_date = datetime.now() - timedelta(days=C.CLEAN_DCE_AFTER_DAYS)
    target_date = target_date.date()
    tender_date = tender.deadline.date()

    if changed_fields:
        try:
            helper.printMessage('TRACE', 'm.save', "#### Saving change record to databse ... ")
            change = Change(tender=tender, changes=changed_fields)
            change.save()
            log_message = f"Tender {tender.chrono} updated. Changes saved."
            helper.printMessage('INFO', 'm.save', log_message)
            helper.printMessage('DEBUG', 'm.save', f"Reported changes: {changed_fields}")
        except:
            helper.printMessage('WARN', 'm.save', "---- Exception raised saving change to database.")
            traceback.print_exc()

        if tender_date > target_date:
            try:
                helper.printMessage('TRACE', 'm.save', f"#### Adding DCE request for Tender {tender.chrono} ... ")
                f2d = FileToGet(tender=tender, reason="Updated")
                f2d.save()
            except:
                helper.printMessage('WARN', 'm.save', "---- Exception raised saving DCE request.")
                traceback.print_exc()

    
    if tender_create:
        if tender_date > target_date:
            try:
                helper.printMessage('TRACE', 'm.save', "#### Adding DCE request for Tender ... ")
                f2d = FileToGet(tender=tender)
                f2d.save()
            except:
                helper.printMessage('WARN', 'm.save', "---- Exception raised saving DCE request.")
                traceback.print_exc()
    else: # Update return boolean: True=Created, False=Updated, None=None
        if len(changed_fields) == 0:
            helper.printMessage('INFO', 'm.save', f"No change was found for {tender.chrono}" )
            tender_create = None


    helper.printMessage('DEBUG', 'g.save', '+++ Finished saving Tender data.')

    return tender, tender_create

