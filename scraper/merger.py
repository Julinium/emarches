import traceback
import pytz
from decimal import Decimal
from django.db import transaction, reset_queries
from datetime import date, datetime, time, timedelta, timezone

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
def saveTender(tender_data):    

    formatted_data = format(tender_data)
    helper.printMessage('DEBUG', 'm.saveTender', f"### Started saving formatted Tender data {formatted_data["chrono"]}")

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

    category, client, kind, mode, procedure = createCckmp(category_data, client_data, kind_data, mode_data, procedure_data)

    tender = Tender.objects.filter(chrono=chrono).first()
    tender_create = tender == None
    changed_fields = []

    if tender is None:
        helper.printMessage('DEBUG', 'm.saveTender', f"### Tender to be created: {chrono}")
        tender = createTender(validated_data, category, client, kind, mode, procedure)
        if tender:
            domains = setDomains(domains_data, tender)
            created_lots = createLots(lots_data, tender)
    else:
        helper.printMessage('INFO', 'm.saveTender', f"### Tender exists: {chrono}")
        
        lots_qs = tender.lots.all()
        numbers_list = [lot_data['number'] for lot_data in lots_data] if lots_data else []
        numbers_list_qs = list(lots_qs.values_list('number', flat=True))

        numbers_to_create = list(set(numbers_list) - set(numbers_list_qs))
        numbers_to_update = list(set(numbers_list) & set(numbers_list_qs))
        numbers_to_delete = list(set(numbers_list_qs) - set(numbers_list))

        helper.printMessage('DEBUG', 'm.saveTender', f"### Lots: +{len(numbers_to_create)}, -{len(numbers_to_delete)}, ~{len(numbers_to_update)}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_create: {numbers_to_create}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_update: {numbers_to_update}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_delete: {numbers_to_delete}")

        if len(numbers_to_delete) > 0:
            dll = deleteLots(numbers_to_delete, tender)
            helper.printMessage('TRACE', 'm.saveTender', f">>> Deleted Lots : \n{dll}\n")
            if tender.lots_count > 1:
                change = {"field": "lot", "old_value": "-", "new_value": f"{-len(numbers_to_delete)}"}
                changed_fields.append(change)
        if len(numbers_to_create) > 0 :
            data_to_create = [obj for obj in lots_data if obj.get('number') in set(numbers_to_create)]
            createLots(data_to_create, tender)
            if tender.lots_count > 1:
                change = {"field": "lot", "old_value": f"+{len(numbers_to_create)}", "new_value": f"-"}
                changed_fields.append(change)
        if len(numbers_to_update) > 0 :
            data_to_update = [obj for obj in lots_data if obj.get('number') in set(numbers_to_update)]
            
            changes = lotsChanged(lots_data, tender)

            if len(changes) > 0:
                updateLots(data_to_update, tender)
                changed_fields += changes

        tender_changes = updateTender(tender, formatted_data, category, client, kind, mode, procedure)
        changed_fields += tender_changes

        logChanges(changed_fields, tender)
        if len(changed_fields) < 1: 
            helper.printMessage('DEBUG', 'm.saveTender', '--- No changes were found in Tender.')
    
    helper.printMessage('DEBUG', 'm.saveTender', '+++ Data saved successfully.')

    return tender, tender_create


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


def timeRabat(snap, default_time=time(0,0)):
    rabat_tz = pytz.timezone("Africa/Casablanca")
    if not snap: return None
    if not isinstance(snap, datetime):
        naive_dt = datetime.combine(snap, default_time)
        return rabat_tz.localize(naive_dt)
    return snap


def createCckmp(category_data, client_data, kind_data, mode_data, procedure_data):
    
    category = None
    helper.printMessage('TRACE', 'm.createCckmp', "### Handling Category ... ")
    if category_data:        
        label = category_data.get('label')
        if label:
            category = Category.objects.filter(label=label).first()
            if category == None:
                category_serializer = CategorySerializer(data=category_data)
                category_serializer.is_valid(raise_exception=True)
                category = category_serializer.save()
                helper.printMessage('TRACE', 'm.createCckmp', f"+++ Created Category: {category.label}")
            else:
                helper.printMessage('TRACE', 'm.createCckmp', f"--- Category found. Skipping: {category.label}")
    
    client = None
    helper.printMessage('TRACE', 'm.createCckmp', "### Handling Client ... ")
    if client_data:        
        name = client_data.get('name')
        if name:
            client = Client.objects.filter(name=name).first()
            if client == None:
                client_serializer = ClientSerializer(data=client_data)
                client_serializer.is_valid(raise_exception=True)
                client = client_serializer.save()
                helper.printMessage('TRACE', 'm.createCckmp', f"+++ Created Client: {client.name}")
            else:
                helper.printMessage('TRACE', 'm.createCckmp', f"--- Client found. Skipping: {client.name}")
    
    kind = None
    helper.printMessage('TRACE', 'm.createCckmp', "### Handling Kind ... ")
    if kind_data:        
        name = kind_data.get('name')
        if name:
            kind = Kind.objects.filter(name=name).first()
            if kind == None:
                kind_serializer = Kinderializer(kind_data)
                kind_serializer.is_valid(raise_exception=True)
                kind = kind_serializer.save()
                helper.printMessage('TRACE', 'm.createCckmp', f"+++ Created Kind: {kind.name}")
            else:
                helper.printMessage('TRACE', 'm.createCckmp', f"--- Kind found. Skipping: {kind.name}")
    
    mode = None
    helper.printMessage('TRACE', 'm.createCckmp', "### Handling Mode ... ")
    if mode_data:        
        name = mode_data.get('name')
        if name:
            mode = Mode.objects.filter(name=name).first()
            if mode == None:
                mode_serializer = ModeSerializer(data=mode_data)
                mode_serializer.is_valid(raise_exception=True)
                mode = mode_serializer.save()
                helper.printMessage('TRACE', 'm.createCckmp', f"+++ Created Mode: {mode.name}")
            else:
                helper.printMessage('TRACE', 'm.createCckmp', f"--- Mode found. Skipping: {mode.name}")
    
    procedure = None
    helper.printMessage('TRACE', 'm.createCckmp', "### Handling Procedure ... ")
    if procedure_data:        
        name = procedure_data.get('name')
        if name:
            procedure = Procedure.objects.filter(name=name).first()
            if procedure == None:
                procedure_serializer = ProcedureSerializer(data=procedure_data)
                procedure_serializer.is_valid(raise_exception=True)
                procedure = procedure_serializer.save()
                helper.printMessage('TRACE', 'm.createCckmp', f"+++ Created Procedure: {procedure.name}")
            else:
                helper.printMessage('TRACE', 'm.createCckmp', f"--- Procedure found. Skipping: {procedure.name}")
    

    return category, client, kind, mode, procedure


def createTender(input_data, category, client, kind, mode, procedure):
    validated_data = input_data
    chrono = validated_data.get('chrono')
    tender = None
    tender_serializer = TenderSerializer(data=validated_data)
    helper.printMessage('DEBUG', 'm.createTender', f"+++ Tender to be created: {chrono}")
    helper.printMessage("TRACE", 'm.updateTender', f"Tender raw data:\n\t+++++###############\n{input_data}\n\t+++++###############")
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)
    
    if tender:
        try:
            helper.printMessage('TRACE', 'm.createTender', f"#### Adding DCE request for Tender {tender.chrono} ... ")
            f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Created'})
            helper.printMessage('DEBUG', 'm.createTender', f"++++ Added DCE request for Tender {tender.chrono} ... ")
        except:
            helper.printMessage('WARN', 'm.createTender', "---- Exception raised saving DCE request.")
            traceback.print_exc()
    return tender


@transaction.atomic
def updateTender(tender, input_data, category, client, kind, mode, procedure):
    helper.printMessage('DEBUG', 'm.updateTender', f"### Checking Tender {tender.chrono} for changes")
    helper.printMessage("TRACE", 'm.updateTender', f"Tender raw data:\n\t~~~~~###############\n{input_data}\n\t~~~~~###############")
    
    changes = []

    def domainsChanged(data, domains):
        incoming_names = {item.get("name") for item in data}
        existing_names = set(domains.values_list("name", flat=True))
        return incoming_names != existing_names

    def tenderChanged(tender, input_data):
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
        if domainsChanged(input_data.get('domains'), tender.domains): return {"field": "domains", "old_value": len(tender.domains.all()), "new_value": len(input_data.get('domains'))}
        return None

    tc = tenderChanged(tender, input_data)
    if tc:
        tender_serializer = TenderSerializer(tender, data=input_data)
        tender_serializer.is_valid(raise_exception=True)
        tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)
        setDomains(input_data.get('domains'), tender)
        helper.printMessage('DEBUG', 'm.updateTender', f"+++ Tender updated: {tender.chrono}")
        changes.append(tc)
    return changes


def lotsChanged(lots_data, tender):
    
    def lotChanged(lot_data, lot):
        cat = lot_data.get('category')
        dict_cat_label = cat.get('label') if cat else ""
        obj_cat_label = lot.category.label if lot.category else None
        if dict_cat_label != obj_cat_label:
            return {"field": "category" , "old_value": obj_cat_label, "new_value": dict_cat_label}
        attrs = ("number", "title", "estimate", "bond", "variant", "reserved")
        return next(
            (
                {
                    "field": attr,
                    "old_value": getattr(lot, attr),
                    "new_value": lot_data.get(attr),
                }
                for attr in attrs
                if lot_data.get(attr) != getattr(lot, attr)
            ),
            None,
        )

    def qualifsChanged(qualifs, data):
        qualif_list = list(qualifs.all())        
        if len(data) != len(qualif_list): return True
        return any(
            q_data.get("name") != qualif.name 
            for q_data, qualif in zip(data, qualif_list)
        )

    def agrementsChanged(agrements, data):
        agrement_list = list(agrements.all())        
        if len(data) != len(agrement_list): return True
        return any(
            a_data.get("name") != agrement.name 
            for a_data, agrement in zip(data, agrement_list)
        )

    def samplesChanged(samples, data):
        sample_list = list(samples.all())
        if len(data) != len(sample_list): return True
        return any(
            s_data.get("when") != sample.when or s_data.get("description") != sample.description
            for s_data, sample in zip(data, sample_list)
        )

    def meetingsChanged(meetings, data):
        meeting_list = list(meetings.all())
        if len(data) != len(meeting_list): return True
        return any(
            m_data.get("when") != meeting.when or m_data.get("description") != meeting.description
            for m_data, meeting in zip(data, meeting_list)
        )

    def visitsChanged(visits, data):
        visit_list = list(visits.all())
        if len(data) != len(visit_list): return True
        return any(
            v_data.get("when") != visit.when or v_data.get("description") != visit.description
            for v_data, visit in zip(data, visit_list)
        )

    lots = tender.lots.all().prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
    ll = len(lots)
    helper.printMessage('DEBUG', 'm.lotsChanged', f"### Checking {ll} Lots for changes ...")
    data_by_number = {lot_data.get('number'): lot_data for lot_data in lots_data}

    i = 0
    for lot in lots:
        i += 1
        helper.printMessage('TRACE', 'm.lotsChanged', f"#### Checking Lot {i}/{ll} ...")
        lot_number = lot.number
        lot_data = data_by_number.get(lot_number)

        details_change = lotChanged(lot_data, lot)
        if details_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot details changed: {details_change}")
            return [details_change]

        if qualifsChanged(lot.qualifs.all(), lot_data.get('qualifs')):
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot qualifs changed: {details_change}")
            return [{
                "field": 'qualifs',
                "old_value": len(lot.qualifs.all()),
                "new_value": len(lot_data.get('qualifs'))
            }]
        
        if agrementsChanged(lot.agrements.all(), lot_data.get('agrements')):
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot agrements changed: {details_change}")
            return [{
                "field": 'agrements',
                "old_value": len(lot.agrements.all()),
                "new_value": len(lot_data.get('agrements'))
            }]
        
        if samplesChanged(lot.samples.all(), lot_data.get('samples')):
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot samples changed: {details_change}")
            return [{
                "field": 'samples',
                "old_value": len(lot.samples.all()),
                "new_value": len(lot_data.get('samples'))
            }]

        if meetingsChanged(lot.meetings.all(), lot_data.get('meetings')):
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot meetings changed: {details_change}")
            return [{
                "field": 'meetings',
                "old_value": len(lot.meetings.all()),
                "new_value": len(lot_data.get('meetings'))
            }]
        
        if visitsChanged(lot.visits.all(), lot_data.get('visits')):
            helper.printMessage('TRACE', 'm.lotsChanged', f"+++ Lot visits changed: {details_change}")
            return [{
                "field": 'visits',
                "old_value": len(lot.visits.all()),
                "new_value": len(lot_data.get('visits'))
            }]

    helper.printMessage('DEBUG', 'm.lotsChanged', f"--- No changes found in {ll} Lots")
    return []


def setDomains(input_data, tender):
    helper.printMessage('TRACE', 'm.setDomains', "### Handling Domains ... ")    
    valid_data = [d for d in input_data if d.get('name')]
    if not valid_data:
        tender.domains.clear()
        helper.printMessage('TRACE', 'm.setDomains', ">>> Domains: Created 0, skipped 0.")
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
            helper.printMessage('DEBUG', 'm.setDomains', f"--- Domain already exists. Skipping: {name[:C.TRUNCA]}...")
        else:
            helper.printMessage('DEBUG', 'm.setDomains', f"+++ Domain of Activiry to be created: {name[:C.TRUNCA]}...")
            domain_serializer = DomainSerializer(data=domain_data)
            domain_serializer.is_valid(raise_exception=True)
            domain = domain_serializer.save()

            existing_domains[name] = domain
            created_domains += 1

        domains.append(domain)

    helper.printMessage('TRACE', 'm.setDomains', f">>> Domains: Created {created_domains}, skipped {skipped_domains}.")

    tender.domains.set(domains)
    return len(domains)


def createSamples(input_data, lot):
    helper.printMessage('TRACE', 'm.createSamples', "#### Handling Lot Samples ... ")
    samples_data = input_data
    created_samples = 0
    for sample_data in samples_data:
        sample_data['when'] = timeRabat(sample_data.get('when'))
        when = sample_data.get('when')
        description = sample_data.get('description')
        if when:
            sample_serializer = SampleSerializer(data=sample_data)
            helper.printMessage('TRACE', 'm.createSamples', f"++++ Sample to be created: {when}")
            sample_serializer.is_valid(raise_exception=True)
            sample_serializer.save(lot=lot)
            created_samples += 1
    return created_samples


def createMeetings(input_data, lot):
    helper.printMessage('TRACE', 'm.createMeetings', "#### Handling Lot Meetings ... ")
    meetings_data = input_data
    created_meetings = 0
    for meeting_data in meetings_data:
        meeting_data['when'] = timeRabat(meeting_data.get('when'))
        when = meeting_data.get('when')
        description = meeting_data.get('description')
        if when:
            meeting_serializer = MeetingSerializer(data=meeting_data)
            helper.printMessage('TRACE', 'm.createMeetings', f"++++ Meeting to be created: {when}")
            meeting_serializer.is_valid(raise_exception=True)
            meeting_serializer.save(lot=lot)
            created_meetings += 1
    return created_meetings


def createVisits(input_data, lot):
    helper.printMessage('TRACE', 'm.createVisits', "#### Handling Lot Visitss ... ")
    visits_data = input_data
    created_visits = 0
    for visit_data in visits_data:
        visit_data['when'] = timeRabat(visit_data.get('when'))
        when = visit_data.get('when')
        description = visit_data.get('description')
        if when:
            visit_serializer = VisitSerializer(data=visit_data)
            helper.printMessage('TRACE', 'm.createVisits', f"++++ Visits to be created: {when}")
            visit_serializer.is_valid(raise_exception=True)
            visit_serializer.save(lot=lot)
            created_visits += 1
    return created_visits


def lottify(lot_no_str, default_int = 1):
    try:
        s = lot_no_str.lower().replace('lot', '').replace(':', '').replace('#', '')
        n = int(s.strip())
        if n > 0: return n
    except: pass
    return default_int


def deleteLots(numbers_list=[], tender=None):       
    if numbers_list == [] or tender == None: return None
    try:
        lots = Lot.objects.filter(tender=tender, number__in=numbers_list)
        return lots.delete()
    except Exception as xx:
        helper.printMessage('ERROR', 'g.deleteLots', str(xx))
        return None


def createCategory(input_data):
    if not input_data or 'label' not in input_data:
        return None
    category, _ = Category.objects.get_or_create(label=input_data['label'])
    return category


def setQualifs(qualifs_data, lot, qualif_cache):
    helper.printMessage('DEBUG', 'm.setQualifs', "#### Handling Lot Qualifs ... ")
    qualifs_to_assign = []
    
    for qualif_data in qualifs_data:
        name = qualif_data.get('name')
        if not name:
            continue

        if name in qualif_cache:
            qualif = qualif_cache[name]
            helper.printMessage('TRACE', 'm.setQualifs', "---- Qualif exists. Skipping.")   
        else:
            helper.printMessage('TRACE', 'm.setQualifs', f"++++ Qualif to be created: {name[:C.TRUNCA]}...")
            qualif_serializer = QualifSerializer(data=qualif_data)
            qualif_serializer.is_valid(raise_exception=True)
            qualif = qualif_serializer.save()
            qualif_cache[name] = qualif

        qualifs_to_assign.append(qualif)

    if qualifs_to_assign:
        lot.qualifs.set(qualifs_to_assign)
    
    return len(qualifs_to_assign)


def setAgrements(agrements_data, lot, agrement_cache):
    helper.printMessage('DEBUG', 'm.setAgrements', "#### Handling Lot Agrements ... ")
    agrements_to_assign = []
    
    for agrement_data in agrements_data:
        name = agrement_data.get('name')
        if not name:
            continue

        if name in agrement_cache:
            agrement = agrement_cache[name]
            helper.printMessage('TRACE', 'm.setAgrements', "---- Agrement exists. Skipping.") 
        else:
            helper.printMessage('TRACE', 'm.setAgrements', f"++++ Agrement to be created: {name[:C.TRUNCA]}...")
            agrement_serializer = AgrementSerializer(data=agrement_data)
            agrement_serializer.is_valid(raise_exception=True)
            agrement = agrement_serializer.save()
            agrement_cache[name] = agrement

        agrements_to_assign.append(agrement)

    if agrements_to_assign:
        lot.agrements.set(agrements_to_assign)
    
    return len(agrements_to_assign)


def createLots(input_data, tender):
    ll = len(input_data) if input_data else 0
    helper.printMessage("TRACE", 'm.createLots', f"Lots raw data:\n\t+++++===============\n{input_data}\n\t+++++===============")
    helper.printMessage('DEBUG', 'm.createLots', f"### Handling { ll } Lots ... ")

    if not input_data:
        return

    with transaction.atomic():
        category_cache = {c.label: c for c in Category.objects.all()}
        new_categories = {}

        for lot_data in input_data:
            cat_data = lot_data.get("category")
            if cat_data and cat_data.get('label'):
                label = cat_data['label']
                if label not in category_cache and label not in new_categories:
                    new_categories[label] = Category(label=label)

        if new_categories:
            created_cats = Category.objects.bulk_create(new_categories.values())
            for cat in created_cats:
                category_cache[cat.label] = cat

        qualif_cache = {x.name: x for x in Qualif.objects.all()}
        new_qualifs = {}
        agrement_cache = {x.name: x for x in Agrement.objects.all()}
        new_agrements = {}

        i = 0
        for lot_data in input_data:
            i += 1
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot {i}/{ll} ... ")
            helper.printMessage("TRACE", 'm.createLots', f"Lot {i} raw data:\n\t+++++---------------\n{lot_data}\n\t+++++---------------")
            for q_data in lot_data.get('qualifs', []):
                name = q_data.get('name')
                if name and name not in qualif_cache and name not in new_qualifs:
                    new_qualifs[name] = Qualif(name=name)
            for a_data in lot_data.get('agrements', []):
                name = a_data.get('name')
                if name and name not in agrement_cache and name not in new_agrements:
                    new_agrements[name] = Agrement(name=name)

        if new_qualifs:
            created_qualifs = Qualif.objects.bulk_create(new_qualifs.values())
            for x in created_qualifs:
                qualif_cache[x.name] = x

        if new_agrements:
            created_agrements = Qualif.objects.bulk_create(new_agrements.values())
            for x in created_agrements:
                agrement_cache[x.name] = x


        lots_to_create = []
        i = 0
        for lot_data in input_data:
            i += 1
            lot_title = lot_data.get('title')
            if not lot_title:
                continue

            cat_data = lot_data.get("category")
            category_obj = None
            if cat_data and cat_data.get('label'):
                category_obj = category_cache.get(cat_data['label'])
            lot_to_create = Lot(tender=tender, number=lot_data.get('number', i),
                title=lot_title, description=lot_data.get('description', ''), category=category_obj,
                estimate=lot_data.get('estimate', Decimal(0)), bond=lot_data.get('bond', Decimal(0)),
                variant=lot_data.get('variant', False), reserved=lot_data.get('reserved', False))
            lots_to_create.append(lot_to_create)

        created_lots = Lot.objects.bulk_create(lots_to_create, batch_size=999)
        helper.printMessage('DEBUG', 'm.createLots', f"++++ Lots created: {len(created_lots)}.")

        LotQualifThrough = Lot.qualifs.through
        m2m_qualif_instances = []
        LotAgrementThrough = Lot.agrements.through
        m2m_agrement_instances = []

        samples_to_create = []
        meetings_to_create = []
        visits_to_create = []

        for lot_data, lot_obj in zip(input_data, created_lots):
            for q_data in lot_data.get('qualifs', []):
                name = q_data.get('name')
                if name and name in qualif_cache:
                    qualif_obj = qualif_cache[name]
                    m2m_qualif_instances.append(LotQualifThrough(lot_id=lot_obj.id, qualif_id=qualif_obj.id))

            for q_data in lot_data.get('agrements', []):
                name = q_data.get('name')
                if name and name in agrement_cache:
                    agrement_obj = agrement_cache[name]
                    m2m_agrement_instances.append(LotAgrementThrough(lot_id=lot_obj.id, agrement_id=agrement_obj.id))
        
            for sample_data in lot_data.get('samples', []):
                sample_to_create = Sample(lot_id=lot_obj.id, when=sample_data.get('when'), description=sample_data.get('description'))
                samples_to_create.append(sample_to_create)

            for meeting_data in lot_data.get('meetings', []):
                meeting_to_create = Meeting(lot_id=lot_obj.id, when=meeting_data.get('when'), description=meeting_data.get('description'))
                meetings_to_create.append(meeting_to_create)

            for visit_data in lot_data.get('visits', []):
                visit_to_create = Visit(lot_id=lot_obj.id, when=visit_data.get('when'), description=visit_data.get('description'))
                visits_to_create.append(visit_to_create)

        if m2m_qualif_instances:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Qualifs ... ")
            created_qualifs = LotQualifThrough.objects.bulk_create(m2m_qualif_instances, batch_size=999, ignore_conflicts=True)
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Qualifs: {len(created_qualifs)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"---- Lot has no Qualifs.")

        if m2m_agrement_instances:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Agrements ... ")
            created_agrements = LotAgrementThrough.objects.bulk_create(m2m_agrement_instances, batch_size=999, ignore_conflicts=True)
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Agrements: {len(created_agrements)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"---- Lot has no Agrements.")

        if samples_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Samples ... ")
            created_samples = Sample.objects.bulk_create(samples_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Samples: {len(created_samples)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"---- Lot has no Samples.")

        if meetings_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Meetings ... ")
            created_meetings = Meeting.objects.bulk_create(meetings_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Meetings: {len(created_meetings)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"---- Lot has no Samples.")

        if visits_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Visits ... ")
            created_visits = Visit.objects.bulk_create(visits_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Visits: {len(created_visits)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"---- Lot has no Visits.")


def updateLots(input_data, tender):
    ll = len(input_data) if input_data else 0
    helper.printMessage("TRACE", 'm.updateLots', f"Lots raw data:\n\t+++++===============\n{input_data}\n\t+++++===============")
    helper.printMessage('DEBUG', 'm.updateLots', f"### Updating { ll } Lots ... ")

    if input_data is None:
        return

    with transaction.atomic():
        existing_lots = {lot.number: lot for lot in Lot.objects.filter(tender=tender)}
        incoming_numbers = {lot_data.get('number') for lot_data in input_data if lot_data.get('number')}

        lots_to_delete_ids = [lot.id for num, lot in existing_lots.items() if num not in incoming_numbers]
        if lots_to_delete_ids:
            Lot.objects.filter(id__in=lots_to_delete_ids).delete()
            helper.printMessage('DEBUG', 'm.updateLots', f"---- Deleted {len(lots_to_delete_ids)} removed lots.")

        category_cache = {c.label: c for c in Category.objects.all()}
        new_categories = {}

        for lot_data in input_data:
            cat_data = lot_data.get("category")
            if cat_data and cat_data.get('label'):
                label = cat_data['label']
                if label not in category_cache and label not in new_categories:
                    new_categories[label] = Category(label=label)

        if new_categories:
            created_cats = Category.objects.bulk_create(new_categories.values())
            for cat in created_cats:
                category_cache[cat.label] = cat

        qualif_cache = {x.name: x for x in Qualif.objects.all()}
        new_qualifs = {}
        agrement_cache = {x.name: x for x in Agrement.objects.all()}
        new_agrements = {}

        for lot_data in input_data:
            for q_data in lot_data.get('qualifs', []):
                name = q_data.get('name')
                if name and name not in qualif_cache and name not in new_qualifs:
                    new_qualifs[name] = Qualif(name=name)
            for a_data in lot_data.get('agrements', []):
                name = a_data.get('name')
                if name and name not in agrement_cache and name not in new_agrements:
                    new_agrements[name] = Agrement(name=name)

        if new_qualifs:
            created_qualifs = Qualif.objects.bulk_create(new_qualifs.values())
            for x in created_qualifs:
                qualif_cache[x.name] = x

        if new_agrements:
            created_agrements = Agrement.objects.bulk_create(new_agrements.values())
            for x in created_agrements:
                agrement_cache[x.name] = x

        lots_to_create = []
        lots_to_update = []
        
        lot_pair_map = []

        i = 0
        for lot_data in input_data:
            i += 1
            lot_title = lot_data.get('title')
            if not lot_title:
                continue

            lot_number = lot_data.get('number', i)
            cat_data = lot_data.get("category")
            category_obj = category_cache.get(cat_data['label']) if cat_data and cat_data.get('label') else None

            if lot_number in existing_lots:
                lot_obj = existing_lots[lot_number]
                lot_obj.title = lot_title
                lot_obj.description = lot_data.get('description', '')
                lot_obj.category = category_obj
                lot_obj.estimate = lot_data.get('estimate', Decimal(0))
                lot_obj.bond = lot_data.get('bond', Decimal(0))
                lot_obj.variant = lot_data.get('variant', False)
                lot_obj.reserved = lot_data.get('reserved', False)
                
                lots_to_update.append(lot_obj)
            else:
                lot_obj = Lot(
                    tender=tender,
                    number=lot_number,
                    title=lot_title,
                    description=lot_data.get('description', ''),
                    category=category_obj,
                    estimate=lot_data.get('estimate', Decimal(0)),
                    bond=lot_data.get('bond', Decimal(0)),
                    variant=lot_data.get('variant', False),
                    reserved=lot_data.get('reserved', False)
                )
                lots_to_create.append(lot_obj)

            lot_pair_map.append((lot_data, lot_obj))

        if lots_to_update:
            Lot.objects.bulk_update(
                lots_to_update,
                fields=['title', 'description', 'category', 'estimate', 'bond', 'variant', 'reserved'],
                batch_size=999
            )
            helper.printMessage('DEBUG', 'm.updateLots', f"++++ Lots updated: {len(lots_to_update)}.")

        if lots_to_create:
            created_lots = Lot.objects.bulk_create(lots_to_create, batch_size=999)
            helper.printMessage('DEBUG', 'm.updateLots', f"++++ Lots created: {len(created_lots)}.")

        all_lot_ids = [lot_obj.id for _, lot_obj in lot_pair_map if lot_obj.id]

        LotQualifThrough = Lot.qualifs.through
        LotAgrementThrough = Lot.agrements.through

        LotQualifThrough.objects.filter(lot_id__in=all_lot_ids).delete()
        LotAgrementThrough.objects.filter(lot_id__in=all_lot_ids).delete()
        Sample.objects.filter(lot_id__in=all_lot_ids).delete()
        Meeting.objects.filter(lot_id__in=all_lot_ids).delete()
        Visit.objects.filter(lot_id__in=all_lot_ids).delete()

        m2m_qualif_instances = []
        m2m_agrement_instances = []
        samples_to_create = []
        meetings_to_create = []
        visits_to_create = []

        for lot_data, lot_obj in lot_pair_map:
            for q_data in lot_data.get('qualifs', []):
                name = q_data.get('name')
                if name and name in qualif_cache:
                    m2m_qualif_instances.append(LotQualifThrough(lot_id=lot_obj.id, qualif_id=qualif_cache[name].id))

            for a_data in lot_data.get('agrements', []):
                name = a_data.get('name')
                if name and name in agrement_cache:
                    m2m_agrement_instances.append(LotAgrementThrough(lot_id=lot_obj.id, agrement_id=agrement_cache[name].id))

            for sample_data in lot_data.get('samples', []):
                samples_to_create.append(Sample(lot_id=lot_obj.id, when=sample_data.get('when'), description=sample_data.get('description')))

            for meeting_data in lot_data.get('meetings', []):
                meetings_to_create.append(Meeting(lot_id=lot_obj.id, when=meeting_data.get('when'), description=meeting_data.get('description')))

            for visit_data in lot_data.get('visits', []):
                visits_to_create.append(Visit(lot_id=lot_obj.id, when=visit_data.get('when'), description=visit_data.get('description')))

        if m2m_qualif_instances:
            LotQualifThrough.objects.bulk_create(m2m_qualif_instances, batch_size=999, ignore_conflicts=True)
        if m2m_agrement_instances:
            LotAgrementThrough.objects.bulk_create(m2m_agrement_instances, batch_size=999, ignore_conflicts=True)
        if samples_to_create:
            Sample.objects.bulk_create(samples_to_create, batch_size=999)
        if meetings_to_create:
            Meeting.objects.bulk_create(meetings_to_create, batch_size=999)
        if visits_to_create:
            Visit.objects.bulk_create(visits_to_create, batch_size=999)


def logChanges(changed_fields, tender):
    if len(changed_fields) > 0 :
        try:
            helper.printMessage('TRACE', 'm.saveTender', ">>>> Saving change record to databse ... ")
            change = Change(tender=tender, changes=changed_fields)
            change.save()
            log_message = f"++++ Tender {tender.chrono} updated. Changes saved."
            helper.printMessage('DEBUG', 'm.saveTender', log_message)
            helper.printMessage('DEBUG', 'm.saveTender', f".... Reported changes: {changed_fields}")
        except:
            helper.printMessage('WARN', 'm.saveTender', "---- Exception raised saving change to database.")
            traceback.print_exc()

        # if tender_date > target_date:
        try:
            helper.printMessage('TRACE', 'm.saveTender', f"++++ Adding DCE request for Tender {tender.chrono} ... ")
            f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Updated'})
        except:
            helper.printMessage('WARN', 'm.saveTender', "---- Exception raised saving DCE request.")
            traceback.print_exc()
    


