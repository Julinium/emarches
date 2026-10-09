import os
import traceback
import pytz
from decimal import Decimal
from django.db import transaction, reset_queries
from datetime import date, datetime, time, timedelta, timezone

from typing import Optional, Tuple, Union, Dict, List, Any, Type
from django.db.models import Model
from rest_framework.serializers import Serializer

from rest_framework import serializers

from base.models import (
    Agrement, Category, Change, Client, Concurrent, Deposit, Domain, FileToGet,
    Kind, Lot, Meeting, Mode, Opening, Procedure, Qualif, RelAgrementLot,
    RelDomainTender, RelQualifLot, Sample, Tender, Visit, Link)

from scraper import constants as C
from scraper import helper
from scraper.downer import getDCE, getExtraFiles
from scraper.getter import getMinutes

from scraper.serializers import (AgrementSerializer, CategorySerializer,
                                 ChangeSerializer, ClientSerializer,
                                 DomainSerializer, KindSerializer,
                                 LotSerializer, MeetingSerializer,
                                 ModeSerializer, ProcedureSerializer,
                                 QualifSerializer, RelAgrementLotSerializer,
                                 RelDomainTenderSerializer,
                                 RelQualifLotSerializer, SampleSerializer,
                                 TenderSerializer, VisitSerializer)



def format(tender_json: dict) -> dict:
    """Parses, normalizes, and cleans raw tender JSON data in-place.

    Converts raw string fields into structured types (dates, floats, booleans),
    maps e-bidding/e-signature flags, standardizes lot metadata, and 
    aggregates totals across all associated lots.

    Args:
        tender_json (dict): Raw tender dictionary containing fields such as 
            published dates, prices, e-submission flags, and lot details.

    Returns:
        dict: The updated, structured tender dictionary. Returns the original 
            dictionary partially processed if an unexpected error occurs during execution.

    Notes:
        - `ebid` and `esign` flags map as follows: 1 (Required), 0 (Optional/Not required), 9 (N/A).
        - Automatically deducts `acronym` from the tender URL parameters.
        - Deduplicates qualification (`qualifs`) and accreditation (`agrements`) lists per lot.
    """

    def lottify(lot_no_str: str, default_int: int = 1) -> int:
        """Parses a raw lot string into a positive integer.

        Strips common lot prefixes (e.g., 'lot', ':', '#') and whitespace, converting
        the remaining numeric string to an integer. Returns a default fallback integer 
        if parsing fails, raises an exception, or yields a non-positive value.

        Args:
            lot_no_str (str): The raw lot identifier string to clean and parse.
            default_int (int, optional): Fallback value to return if parsing fails 
                or yields a value <= 0. Defaults to 1.

        Returns:
            int: The parsed positive lot number, or `default_int` on failure.

        Examples:
            >>> lottify("Lot #3")
            3
            >>> lottify("lot: 12")
            12
            >>> lottify("invalid_lot", default_int=5)
            5
        """
        try:
            s = lot_no_str.lower().replace('lot', '').replace(':', '').replace('#', '')
            n = int(s.strip())
            if n > 0: return n
        except: pass
        return default_int

    helper.printMessage('DEBUG', 'm.format', "### Started formatting Tender data ...")
    j = tender_json
    try:
        j["published"] = j["published"]
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

                
                raw_qualifs = l.get('qualifs', [])
                unique_qualifs = list({obj.get('name'): obj for obj in raw_qualifs if 'name' in obj}.values())
                l['qualifs'] = unique_qualifs
                raw_agrements = l.get('agrements', [])
                unique_agrements = list({obj.get('name'): obj for obj in raw_agrements if 'name' in obj}.values())
                l['agrements'] = unique_agrements

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
def saveTender(tender_data, link=None):
 
    formatted_data = format(tender_data)
    helper.printMessage('DEBUG', 'm.saveTender', f"### Saving formatted Tender data {formatted_data["chrono"]}")

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
    extra_files    = formatted_data["extra_files"]

    category, client, kind, mode, procedure = createCckmp(category_data, client_data, kind_data, mode_data, procedure_data)

    tender = Tender.objects.filter(chrono=chrono).first()
    tender_create = tender == None
    changes = []

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

        numbers_to_create = set(numbers_list) - set(numbers_list_qs)
        numbers_to_update = set(numbers_list) & set(numbers_list_qs)
        numbers_to_delete = set(numbers_list_qs) - set(numbers_list)

        helper.printMessage('DEBUG', 'm.saveTender', f"### Lots: +{len(numbers_to_create)}, -{len(numbers_to_delete)}, ~{len(numbers_to_update)}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_create: {numbers_to_create}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_update: {numbers_to_update}")
        helper.printMessage('TRACE', 'm.saveTender', f"### numbers_to_delete: {numbers_to_delete}")

        if len(numbers_to_delete) > 0:
            dll = deleteLots(list(numbers_to_delete), tender)
            helper.printMessage('DEBUG', 'm.saveTender', f">>> Deleted Lots : \n{dll}\n")
            if tender.lots_count > 1:
                change = {"level": "Tender", "field": "lots", "old_value": "-", "new_value": f"{-len(numbers_to_delete)}"}
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Reported Deletion change : {change}")
                changes.append(change)
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Changed fields so far: {changes}")
        if len(numbers_to_create) > 0 :
            data_to_create = [obj for obj in lots_data if obj.get('number') in numbers_to_create]
            createLots(data_to_create, tender)
            if tender.lots_count > 1:
                change = {"level": "Tender", "field": "lots", "old_value": "-", "new_value": f"+{len(numbers_to_create)}"}
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Reported Creation change: {change}")
                changes.append(change)
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Changed fields so far: {changes}")
        if len(numbers_to_update) > 0 :
            data_to_update = [obj for obj in lots_data if obj.get('number') in numbers_to_update]

            lots_changes = lotsChanged(lots_data, tender)

            if len(lots_changes) > 0:
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Reported Lots change: {lots_changes}")
                updateLots(data_to_update, tender)
                changes += lots_changes
                helper.printMessage('TRACE', 'm.saveTender', f"~~~ Changed fields so far: {changes}")

        tender_changes = updateTender(tender, formatted_data, category, client, kind, mode, procedure)
        changes += tender_changes

        logChanges(changes, tender)
        if len(changes) < 1: 
            helper.printMessage('INFO', 'm.saveTender', '--- No changes were found in Tender.')
    if tender_create or len(changes) > 0:
        helper.printMessage('DEBUG', 'm.saveTender', '+++ Data saved successfully.')
        if tender:
            if not C.SKIP_DCE:
                helper.printMessage('DEBUG', 'm.saveTender', f"### Handling DCE for Tender {tender.chrono} ...")
                handleDCE(tender)
                if len(extra_files) > 0:
                    helper.printMessage('DEBUG', 'm.saveTender', f"### Handling Extra files for Tender {tender.chrono} ...")
                    handleExtra(tender, extra_files)
                else:
                    helper.printMessage('DEBUG', 'm.saveTender', f"--- No Extra files found for Tender {tender.chrono} ...")
            else:
                helper.printMessage('DEBUG', 'm.saveTender', f"~~~ Skipping DCE for Tender {tender.chrono} ...")

            # Handling Results
            if C.GET_RESULTS == True:
                helper.printMessage('DEBUG', 'm.saveTender', f"### Handling Results for Tender {tender.chrono} ...")
                if tender.openings.count() == 0:
                    has_minutes = formatted_data.get('has_minutes', False)
                    if has_minutes:
                        helper.printMessage('DEBUG', 'm.saveTender', f"### Tender {tender.chrono} has minutes. Getting them ...")
                        minutes_digest = getMinutes(tender.chrono, tender.acronym)
                        if minutes_digest and minutes_digest != {}:
                            if mergeResults(minutes_digest) == 0:
                                helper.printMessage('DEBUG', 'm.saveTender', f"+++ Minutes for Tender {tender.chrono} saved successfully.")
                            else:
                                helper.printMessage('ERROR', 'm.saveTender', f"--- Error saving Minutes for Tender {tender.chrono}.")
                        else:
                            helper.printMessage('WARN', 'm.saveTender', f"--- No Minutes found for Tender {tender.chrono}.")
                    else:
                        helper.printMessage('DEBUG', 'm.saveTender', f"### Tender {tender.chrono} has no minutes. Skipping ...")
                else:
                    helper.printMessage('DEBUG', 'm.saveTender', f"### Tender {tender.chrono} already has results. Skipping ...")
            else:
                helper.printMessage('DEBUG', 'm.saveTender', f"### Skipping Results for Tender {tender.chrono} ...")

    if link:
        related_link = Link.objects.filter(chrono=link.chrono).first()
        try:
            helper.printMessage('DEBUG', 'm.saveTender', f"~~~ Matching link to tender on { link.chrono } ...")
            matched = related_link.tender == tender
            if matched:
                helper.printMessage('DEBUG', 'm.saveTender', f"--- Already matched on { link.chrono }.")
            else:
                related_link.tender = tender
                related_link.handled = True
                related_link.save()
                helper.printMessage('DEBUG', 'm.saveTender', f"+++ Link and Tender liked successfully on { link.chrono }.")
        except Exception as xc:
            helper.printMessage('WARN', 'm.saveTender', f"xxx Error matching on {link.chrono}.")
            traceback.print_exc()
    
    return tender, tender_create, len(changes) > 0


def mergeResults(digest: dict) -> int:
    """Merges processed tender results into the database via Django ORM.

    Retrieves a target Tender model using identifying metadata from the digest, 
    creates or updates its associated Opening record, and iterates through candidate 
    bidders to log individual lot deposits, financial offers, administrative status, 
    and winning attributes.

    Args:
        digest (dict): Dictionary containing raw or parsed result details for a tender.
            Expected keys include:
            - 'chrono' (str): Chronological identifier for the tender.
            - 'acronym' (str): Acronym identifier for the tender.
            - 'date_finished' (str): Completion date formatted as 'DD/MM/YYYY'.
            - 'winner_offers' (list[dict]): Winning bids containing 'amount', 'name', 'lot'.
            - 'financial_offers' (list[dict]): Offers containing 'pre_amount', 'amount', 'name', 'lot'.
            - 'bidders' (list[dict]): Candidate bidder objects containing at least a 'name'.
            - 'rejected_dt', 'rejected_da', 'reserved_da', 'accepted_da' (list[dict]): Status lists
              used to evaluate technical and administrative outcomes per lot.

    Returns:
        int: Execution status code:
            - 0: Successfully merged results into the database.
            - 1: Failed to merge because no matching Tender was found.

    Side Effects:
        - Creates or updates an `Opening` record tied to the matching `Tender`.
        - Creates `Concurrent` (bidder) records if they do not already exist.
        - Creates or updates `Deposit` records mapping bidders to specific tender lots.
        - Logs informational, debug, warning, and error messages via `helper.printMessage`.
    """

    chro = digest.get('chrono', '?')
    acro = digest.get('acronym', '?')    
    helper.printMessage('INFO', 'm.mergeResults', f"### Started merging results for {chro}&{acro}")
    helper.printMessage('DEBUG', 'm.mergeResults', f"\tReceived result digest {digest}")
    tender = Tender.objects.filter(chrono=chro, acronym=acro).first()
    if not tender: 
        helper.printMessage('ERROR', 'm.mergeResults', f"### Error: Tender not found for {chro}&{acro}. No result saved", 1)
        return 1

    failures_text = digest.get('failures_text', '-')
    date_str = digest.get('date_finished', '')
    try: 
        date = datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception as xc:
        # date = None
        helper.printMessage('WARN', 'm.mergeResults', f"\tCould not extract date from [{date_str}]")
        date = tender.deadline.date()
        helper.printMessage('INFO', 'm.mergeResults', f"\tResults date fell back to Tender deadline: [{date}]")
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
        name    = cand.get('name', '-')
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
                    helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Created Deposit, Lot { lot}, for { name }")
                else:
                    helper.printMessage('DEBUG', 'm.mergeResults', f"\t==Updated existing Deposit, Lot { lot}, for { name }")
      
    return 0


def timeRabat(snap: Union[datetime, date, None], default_time: time = time(0, 0)) -> Optional[datetime]:
    """Converts a date or naive datetime object to a timezone-aware Casablanca datetime.

    If given a `date` instance (and not already a `datetime`), it combines the date 
    with `default_time` and attaches the `Africa/Casablanca` timezone. If given a 
    `datetime` instance, it returns it as-is without modification.

    Args:
        snap (Union[datetime, date, None]): The input date, datetime, or None.
        default_time (time, optional): Time component used when `snap` is a `date` 
            object. Defaults to midnight (`time(0, 0)`).

    Returns:
        Optional[datetime]: A localized `datetime` object in Casablanca timezone, 
            the unchanged `datetime` if already provided, or `None` if `snap` is falsy.

    Note:
        This function assumes that non-datetime inputs can be safely passed to 
        `datetime.combine()` (e.g., standard `datetime.date` instances). Passing an 
        already timezone-aware `datetime` will return it unmodified without converting 
        its timezone to Casablanca.
    """
    rabat_tz = pytz.timezone("Africa/Casablanca")
    if not snap: return None
    if not isinstance(snap, datetime):
        naive_dt = datetime.combine(snap, default_time)
        return rabat_tz.localize(naive_dt)
    return snap


def createCckmp(
        category_data: Optional[Dict[str, Any]],
        client_data: Optional[Dict[str, Any]],
        kind_data: Optional[Dict[str, Any]],
        mode_data: Optional[Dict[str, Any]],
        procedure_data: Optional[Dict[str, Any]]
    ) -> Tuple[
        Optional[Category], 
        Optional[Client], 
        Optional[Kind], 
        Optional[Mode], 
        Optional[Procedure]
    ]:
    """Ensures presence of core reference entities (Category, Client, Kind, Mode, Procedure).

    Checks if each entity exists by its unique lookup field. If found, returns the 
    existing record; otherwise, validates the payload using its corresponding DRF 
    serializer and persists a new instance to the database.

    Args:
        category_data (dict, optional): Serializer data for Category (lookup field: 'label').
        client_data (dict, optional): Serializer data for Client (lookup field: 'name').
        kind_data (dict, optional): Serializer data for Kind (lookup field: 'name').
        mode_data (dict, optional): Serializer data for Mode (lookup field: 'name').
        procedure_data (dict, optional): Serializer data for Procedure (lookup field: 'name').

    Returns:
        tuple: A 5-element tuple containing (Category, Client, Kind, Mode, Procedure) instances.
    """

    def _get_or_create_entity(
            model_cls: Type[Model],
            serializer_cls: Type[Serializer],
            data: Optional[Dict[str, Any]],
            lookup_field: str = 'name',
            caller_name: str = 'm.createCckmp'
        ) -> Optional[Model]:
        """Helper to retrieve an existing model instance or validate and save a new one via serializer."""
        entity_type = model_cls.__name__
        helper.printMessage('TRACE', caller_name, f"### Handling {entity_type} ... ")

        if not data:
            return None

        lookup_val = data.get(lookup_field)
        if not lookup_val:
            return None

        # Check if instance already exists
        instance = model_cls.objects.filter(**{lookup_field: lookup_val}).first()
        if instance:
            display_name = getattr(instance, lookup_field, str(instance))
            helper.printMessage('TRACE', caller_name, f"--- {entity_type} found. Skipping: {display_name}")
            return instance

        # Validate and create via serializer
        serializer = serializer_cls(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        display_name = getattr(instance, lookup_field, str(instance))
        helper.printMessage('TRACE', caller_name, f"+++ Created {entity_type}: {display_name}")
        return instance


    category = _get_or_create_entity(Category, CategorySerializer, category_data, lookup_field='label')
    client = _get_or_create_entity(Client, ClientSerializer, client_data, lookup_field='name')
    kind = _get_or_create_entity(Kind, KindSerializer, kind_data, lookup_field='name')
    mode = _get_or_create_entity(Mode, ModeSerializer, mode_data, lookup_field='name')
    procedure = _get_or_create_entity(Procedure, ProcedureSerializer, procedure_data, lookup_field='name')

    return category, client, kind, mode, procedure


def handleDCE(tender: Optional[Tender]) -> Optional[str]:
    """Downloads and syncs DCE (Dossier de Consultation Eléctronique) documents for a tender.

    Attempts to doenload DCE files to a local DCE directory for the specified tender. 
    If running on a remote machine (`C.MACHINE == 'remote'`), it synchronizes the local 
    media directory with the remote server. If retrieval or synchronization fails, it logs 
    a failure record in the `FileToGet` tracking table.

    Args:
        tender (Tender): The Django model instance representing the target tender. 
            Must have a `chrono` attribute.

    Returns:
        Optional[str]: The local directory path (`dce_dir`) to the DCE files if retrieval 
            and synchronization succeed; otherwise `None`.

    Side Effects:
        - May invoke external file download logic (`getDCE`).
        - May perform directory network synchronization (`helper.syncDir`).
        - On failure or incomplete execution, creates or updates a `FileToGet` record 
          with `reason='Failed'`.
        - Logs progress, warnings, and errors using `helper.printMessage`.
        - Prints stack traces on exceptions via `traceback.print_exc()`.
    """

    dce_dir, synced = None, None
    if tender:
        try:
            helper.printMessage('DEBUG', 'm.handleDCE', f"#### Getting DCE for Tender {tender.chrono} ... ")
            dce_dir = getDCE(tender)
            if dce_dir:
                helper.printMessage('DEBUG', 'm.handleDCE', f"++++ Got DCE for Tender {tender.chrono} ... ")
                if C.MACHINE == 'remote':
                    helper.printMessage('TRACE', 'm.handleDCE', f"#### Syncing DCE to remote server ... ")
                    media_dce = os.path.join(dce_dir, '..')
                    synced = helper.syncDir(media_dce)
                else:
                    synced = True
            else:
                helper.printMessage('WARN', 'm.handleDCE', f"---- Could not get DCE for Tender {tender.chrono} ... ")

        except:
            helper.printMessage('WARN', 'm.handleDCE', "---- Exception raised saving DCE request.")
            traceback.print_exc()

    if dce_dir == None or synced == None:
        helper.printMessage('WARN', 'm.handleDCE', f"---- DCE handling failed for Tender {tender.chrono} ...")
        try:
            f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Failed'})
            helper.printMessage('TRACE', 'm.handleDCE', f"~~~~ Filed a DCE request for Tender {tender.chrono}.")
        except:
            helper.printMessage('WARN', 'm.handleDCE', "---- Exception raised saving DCE request.")
            traceback.print_exc()

    return dce_dir if synced else None


def handleExtra(tender: Optional[Tender], extra_files):

    extra_dir, synced = None, None
    if tender:
        try:
            helper.printMessage('DEBUG', 'm.handleExtra', f"#### Getting Extra for Tender {tender.chrono} ... ")
            added_files = getExtraFiles(tender, extra_files)
            if added_files == None:
                return None
            extra_dir = added_files.get('path', None)
            if extra_dir:
                helper.printMessage('DEBUG', 'm.handleExtra', f"++++ Got Extra for Tender {tender.chrono} ... ")
                if C.MACHINE == 'remote':
                    helper.printMessage('TRACE', 'm.handleExtra', f"#### Syncing Extra to remote server ... ")
                    media_extra = os.path.join(extra_dir, '..')
                    synced = helper.syncDir(media_extra)
                else:
                    synced = True
            else:
                helper.printMessage('WARN', 'm.handleExtra', f"---- Could not get Extra for Tender {tender.chrono} ... ")

        except:
            helper.printMessage('WARN', 'm.handleExtra', "---- Exception raised saving Extra request.")
            traceback.print_exc()

    if extra_dir == None or synced == None:
        helper.printMessage('WARN', 'm.handleExtra', f"---- Extra handling failed for Tender {tender.chrono} ...")
        # try:
        #     f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Failed'})
        #     helper.printMessage('TRACE', 'm.handleExtra', f"~~~~ Filed a Extra request for Tender {tender.chrono}.")
        # except:
        #     helper.printMessage('WARN', 'm.handleExtra', "---- Exception raised saving Extra request.")
        #     traceback.print_exc()

    return extra_dir if synced else None


def createTender(
        input_data: Dict[str, Any],
        category: Optional[Category],
        client: Optional[Client],
        kind: Optional[Kind],
        mode: Optional[Mode],
        procedure: Optional[Procedure]
    ) -> Tender:
    """Validates raw input data and creates a new Tender database record.

    Logs the raw dictionary payload for tracing, validates the data using 
    `TenderSerializer`, and persists the new instance while binding its associated 
    foreign key relations (Category, Client, Kind, Mode, and Procedure).

    Args:
        input_data (Dict[str, Any]): Dictionary containing raw attributes to build 
            the tender object.
        category (Optional[Category]): Resolved Category model instance to attach.
        client (Optional[Client]): Resolved Client model instance to attach.
        kind (Optional[Kind]): Resolved Kind model instance to attach.
        mode (Optional[Mode]): Resolved Mode model instance to attach.
        procedure (Optional[Procedure]): Resolved Procedure model instance to attach.

    Returns:
        Tender: The newly created and saved Tender Django model instance.

    Raises:
        rest_framework.exceptions.ValidationError: If `input_data` fails 
            serializer validation rules.
    """
    validated_data = input_data
    chrono = validated_data.get('chrono')
    tender = None
    tender_serializer = TenderSerializer(data=validated_data)    
    helper.printMessage("TRACE", 'm.createTender', f"Tender raw data:\n\t+++++###############\n{input_data}\n\t+++++###############")
    tender_serializer.is_valid(raise_exception=True)
    tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)

    return tender


@transaction.atomic
def updateTender(
        tender: Any,
        input_data: Dict[str, Any],
        category: Optional[Category],
        client: Optional[Client],
        kind: Optional[Kind],
        mode: Optional[Mode],
        procedure: Optional[Procedure]
    ) -> List[Dict[str, Any]]:
    """Evaluates an existing Tender for changes and updates it atomically if modified.

    Uses inner helpers (`tenderChanged` and `domainsChanged`) to detect discrepancies 
    between the current Tender model state and the incoming dictionary payload. If a change 
    is detected, the function validates the updated data via `TenderSerializer`, persists 
    the model changes along with foreign key relations, updates domain mappings via `setDomains`, 
    and returns a summary of the modification.

    Args:
        tender (Tender): The existing Django model instance to evaluate and update.
        input_data (Dict[str, Any]): Updated raw dictionary attributes for the tender.
        category (Optional[Category]): Foreign key Category model instance to attach.
        client (Optional[Client]): Foreign key Client model instance to attach.
        kind (Optional[Kind]): Foreign key Kind model instance to attach.
        mode (Optional[Mode]): Foreign key Mode model instance to attach.
        procedure (Optional[Procedure]): Foreign key Procedure model instance to attach.

    Returns:
        List[Dict[str, Any]]: A list containing a change descriptor dictionary if an 
            update occurred (e.g., `[{'level': 'Tender', 'field': ..., 'old_value': ..., 'new_value': ...}]`), 
            or an empty list `[]` if no changes were detected.

    Side Effects:
        - Executes within a database transaction block (`@transaction.atomic`). Any failure 
          during serializer validation or domain updates rolls back all database operations.
        - Mutates the `tender` record in the database if differences are detected.
        - Invokes `setDomains` to replace or update related `Domain` records on the tender.
        - Logs tracing and debugging output via `helper.printMessage`.

    Raises:
        rest_framework.exceptions.ValidationError: If `input_data` fails serializer validation 
            when changes are detected.
    """

    def domainsChanged(tender: Any, domains_data: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """Detects changes between a tender's existing database domains and new incoming domains data.

        Compares domain counts first. If counts differ, returns a change dictionary summarizing
        the count discrepancy. If counts match, evaluates set differences between domain names.
        Returns details on modified domain names if differences are detected.

        Args:
            tender (Tender): The Django model instance containing existing domain relations.
            domains_data (List[Dict[str, Any]]): A list of dictionaries containing updated domain
                payloads (e.g., `[{'name': 'IT'}, {'name': 'Telecom'}]`).

        Returns:
            Optional[Dict[str, str]]: A dictionary detailing the detected change with keys:
                `level`, `field`, `old_value`, and `new_value`. Returns `None` if no changes
                are detected.

        Note:
            - If domain counts differ, the returned dictionary sets `field` to `"domains"` 
            and reports counts as string values.
            - If counts match but contents differ, the returned dictionary sets `field` to `"domain"` 
            and lists comma-separated domain names sorted alphabetically.
            - Duplicate names in `domains_data` may trigger set logic checks even if list lengths match.
        """
        existing_names = list(tender.domains.values_list("name", flat=True))
        new_names = [data.get("name") for data in domains_data if "name" in data]

        if len(domains_data) != len(existing_names):
            return {
                "level": "Tender",
                "field": "domains",
                "old_value": f"{len(existing_names)}",
                "new_value": f"{len(domains_data)}",
            }
        
        added = set(new_names) - set(existing_names)
        removed = set(existing_names) - set(new_names)
        
        if added or removed:
            return {
                "level": "Tender",
                "field": "domain",
                "old_value": ", ".join(sorted(existing_names)),
                "new_value": ", ".join(sorted(new_names)),
            }

        return None

    def tenderChanged(tender: Any, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compares an existing Tender model instance against incoming payload data for changes.

        Evaluates simple model fields, foreign key relationships, and attached domain lists 
        in order. Returns immediately on the first detected field discrepancy.

        Args:
            tender (Tender): The existing Django model instance representing the tender.
            input_data (Dict[str, Any]): Dictionary containing updated key-value attributes 
                to compare against the current tender state.

        Returns:
            Optional[Dict[str, Any]]: A dictionary describing the first detected change with keys:
                - `level` (str): Scope of the change (always `"Tender"`).
                - `field` (str): Name of the changed attribute or entity.
                - `old_value` (Any): Formatted string representation of the old value.
                - `new_value` (Any): Formatted string representation of the new value.
                Returns `None` if no changes are detected across all checked fields.

        Notes:
            - Evaluation follows a strict order: primitive fields -> foreign key attributes -> domains list.
            - `datetime` objects are formatted as `YYYY-MM-THH:MZ` for display.
            - `date` objects are formatted as `YYYY-MM-DD` for display.
            - Foreign key relationships (`category`, `mode`, `procedure`, `client`, `kind`) are only 
            evaluated if the target related object already exists on `tender`.
        """

        helper.printMessage('DEBUG', 'm.tenderChanged', f"#### Checking domains for changes ...")
        CHECK_FIELDS = (
            "cancelled", "deadline", "estimate", "bond", "size_read", "size_bytes",
            "contact_name", "contact_phone", "contact_email", "contact_fax",
            "address_withdrawal", "address_bidding", "address_opening",
            "title", "reference", "published", "ebid", "esign",
            "plans_price", "reserved", "variant", "location", "acronym", "link"
        )

        for field in CHECK_FIELDS:
            if field in input_data:
                helper.printMessage('TRACE', 'm.tenderChanged', f"##### Checking changes for {field} ...")
                new_value = input_data[field]
                old_value = getattr(tender, field, None)

                old_value_display = old_value
                if type(old_value) is datetime: old_value_display = old_value.strftime('%Y-%m-%dT%H:%MZ')
                elif type(old_value) is date: old_value_display = old_value.strftime('%Y-%m-%d')

                new_value_display = new_value
                if type(new_value) is datetime: new_value_display = new_value.strftime('%Y-%m-%dT%H:%MZ')
                elif type(new_value) is date: new_value_display = new_value.strftime('%Y-%m-%d')

                if new_value != old_value:
                    return {
                        "level": "Tender",
                        "field": field,
                        "old_value": old_value_display,
                        "new_value": new_value_display,
                    }

        RELATION_CONFIGS = (
            ("category",  "Category",  "category",  "label"),
            ("mode",      "Mode",      "mode",      "name"),
            ("procedure", "Procedure", "procedure", "name"),
            ("client",    "Client",    "client",    "name"),
            ("kind",      "Type",      "kind",      "name"),
        )

        for input_key, field_name, attr_name, val_key in RELATION_CONFIGS:
            rel_data = input_data.get(input_key)
            if rel_data and isinstance(rel_data, dict):
                new_val = rel_data.get(val_key)

                related_obj = getattr(tender, attr_name, None)
                old_val = getattr(related_obj, val_key, None) if related_obj else None

                if related_obj and new_val != old_val:
                    return {
                        "level": "Tender",
                        "field": field_name,
                        "old_value": old_val,
                        "new_value": new_val,
                    }

        domains_change = domainsChanged(tender, input_data.get('domains'))
        if domains_change: 
            helper.printMessage('TRACE', 'm.tenderChanged', f"++++ Change detected in Tender domains {domains_change}.")
            return domains_change

        helper.printMessage('DEBUG', 'm.tenderChanged', f"---- No changes found in domains.")        
        return None

    helper.printMessage('DEBUG', 'm.updateTender', f"### Checking Tender {tender.chrono} for changes")
    helper.printMessage("TRACE", 'm.updateTender', f"Tender raw data:\n\t~~~~~###############\n{input_data}\n\t~~~~~###############")

    changes = []

    tc = tenderChanged(tender, input_data)
    if tc:
        tender_serializer = TenderSerializer(tender, data=input_data)
        tender_serializer.is_valid(raise_exception=True)
        tender = tender_serializer.save(category=category, client=client, kind=kind, mode=mode, procedure=procedure)
        setDomains(input_data.get('domains'), tender)
        helper.printMessage('DEBUG', 'm.updateTender', f"+++ Tender updated with changes: {tender.chrono}")
        changes.append(tc)

    return changes


def lotsChanged(lots_data, tender):

    def format_wd(w, d, r, a):            
        common_w = {w for w, _ in r} & {w for w, _ in a}
        common_d = {d for _, d in r} & {d for _, d in a}

        if w in common_w: return f"... {d}"
        if d in common_d: return f"{w} ..."
        return f"{w} ({d})" 
    
    def lotChanged(lot, lot_data):
        cat = lot_data.get('category')
        dict_cat_label = cat.get('label') if cat else ""
        obj_cat_label = lot.category.label if lot.category else None       
        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"

        if dict_cat_label != obj_cat_label:
            return {"level": level, "field": "category" , "old_value": obj_cat_label, "new_value": dict_cat_label}
        attrs = ("estimate", "bond", "reserved", "variant", "title", "number") 

        return next(
            (
                {
                    "level": level,
                    "field": attr,
                    "old_value": getattr(lot, attr),
                    "new_value": lot_data.get(attr),
                }
                for attr in attrs
                if lot_data.get(attr) != getattr(lot, attr)
            ),
            None,
        )

    def qualifsChanged(lot, qualifs_data):
        existing_names = list(lot.qualifs.values_list('name', flat=True))
        new_names = [data.get("name") for data in qualifs_data if "name" in data]
        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"
        
        if len(qualifs_data) != len(existing_names):
            return {
                "level": level,
                "field": "Qualifs",
                "old_value": f"{len(existing_names)}",
                "new_value": f"{len(qualifs_data)}",
            }
        
        added = set(new_names) - set(existing_names)
        removed = set(existing_names) - set(new_names)
        
        if added or removed:
            return {
                "level": level,
                "field": "Qualif",
                "old_value": ", ".join(sorted(existing_names)),
                "new_value": ", ".join(sorted(new_names)),
            }
                
        return None
        
    def agrementsChanged(lot, agrements_data):
        existing_names = list(lot.agrements.values_list('name', flat=True))
        new_names = [data.get("name") for data in agrements_data if "name" in data]
        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"

        if len(agrements_data) != len(existing_names):
            return {
                "level": level,
                "field": "Agrements",
                "old_value": f"{len(existing_names)}",
                "new_value": f"{len(agrements_data)}",
            }
        
        added = set(new_names) - set(existing_names)
        removed = set(existing_names) - set(new_names)
        
        if added or removed:
            return {
                "level": level,
                "field": "Agrement",
                "old_value": ", ".join(sorted(existing_names)),
                "new_value": ", ".join(sorted(new_names)),
            }

        return None

    def samplesChanged(lot, samples_data):
        existing_samples = list(lot.samples.values_list('when', 'description'))        
        new_samples = [(data.get("when"), data.get("description")) for data in samples_data]

        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"
        if len(samples_data) != len(existing_samples):
            return {
                "level": level,
                "field": "Samples",
                "old_value": f"{len(existing_samples)}",
                "new_value": f"{len(samples_data)}",
            }
        
        if set(existing_samples) != set(new_samples):
            removed = set(existing_samples) - set(new_samples)
            added = set(new_samples) - set(existing_samples)

            old_summary = "; ".join([format_wd(w, d, removed, added) for w, d in removed]) if removed else "-"
            new_summary = "; ".join([format_wd(w, d, removed, added) for w, d in added]) if added else "-"
            
            return {
                "level": level,
                "field": "Samples",
                "old_value": old_summary,
                "new_value": new_summary,
            }

        return None

    def meetingsChanged(lot, meetings_data):
        existing_meetings = list(lot.meetings.values_list('when', 'description'))        
        new_meetings = [(data.get("when"), data.get("description")) for data in meetings_data]
        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"
        if len(meetings_data) != len(existing_meetings):
            return {
                "level": level,
                "field": "Meetings",
                "old_value": f"{len(existing_meetings)}",
                "new_value": f"{len(meetings_data)}",
            }
        
        if set(existing_meetings) != set(new_meetings):
            removed = set(existing_meetings) - set(new_meetings)
            added = set(new_meetings) - set(existing_meetings)

            old_summary = "; ".join([format_wd(w, d, removed, added) for w, d in removed]) if removed else "-"
            new_summary = "; ".join([format_wd(w, d, removed, added) for w, d in added]) if added else "-"
            
            return {
                "level": level,
                "field": "Meetings",
                "old_value": old_summary,
                "new_value": new_summary,
            }
                
        return None

    def visitsChanged(lot, visits_data):
        existing_visits = list(lot.visits.values_list('when', 'description'))
        new_visits = [(data.get("when"), data.get("description")) for data in visits_data]

        level = f"Lot #{lot.number}" if lot.tender.lots_count > 1 else "Tender"
        if len(visits_data) != len(existing_visits):
            return {
                "level": level,
                "field": "Visits",
                "old_value": f"{len(existing_visits)}",
                "new_value": f"{len(visits_data)}",
            }

        if set(existing_visits) != set(new_visits):
            removed = set(existing_visits) - set(new_visits)
            added = set(new_visits) - set(existing_visits)

            old_summary = "; ".join([format_wd(w, d, removed, added) for w, d in removed]) if removed else "-"
            new_summary = "; ".join([format_wd(w, d, removed, added) for w, d in added]) if added else "-"

            return {
                "level": level,
                "field": "Visits",
                "old_value": old_summary,
                "new_value": new_summary,
            }

        return None


    lots = tender.lots.all().prefetch_related("agrements", "qualifs", "samples", "meetings", "visits")
    ll = len(lots)
    helper.printMessage('DEBUG', 'm.lotsChanged', f"### Checking {ll} Lots for changes ...")
    data_by_number = {lot_data.get('number'): lot_data for lot_data in lots_data}

    changes = []
    i = 0
    for lot in lots:
        i += 1
        helper.printMessage('TRACE', 'm.lotsChanged', f"#### Checking Lot {i}/{ll} ...")
        lot_number = lot.number
        lot_data = data_by_number.get(lot_number)

        if tender.lots_count > 1:
            details_change = lotChanged(lot, lot_data)
            if details_change:
                helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} details changed: {details_change}")
                changes.append(details_change)
                return changes
            helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot_number} details.")

        qualifs_change = qualifsChanged(lot, lot_data.get('qualifs'))
        if qualifs_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} qualifs changed: {qualifs_change}")
            changes.append(qualifs_change)
            return changes
        helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot.number} Qualifs.")

        agrements_change = agrementsChanged(lot, lot_data.get('agrements'))
        if agrements_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} agrements changed: {agrements_change}")
            changes.append(agrements_change)
            return changes
        helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot.number} Agrements.")
       
        samples_change = samplesChanged(lot, lot_data.get('samples'))
        if samples_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} samples changed: {samples_change}")
            changes.append(samples_change)
            return changes
        helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot.number} Samples.")
       
        meetings_change = meetingsChanged(lot, lot_data.get('meetings'))
        if meetings_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} meetings changed: {meetings_change}")
            changes.append(meetings_change)
            return changes
        helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot.number} Meetings.")
       
        visits_change = visitsChanged(lot, lot_data.get('visits'))
        if visits_change:
            helper.printMessage('TRACE', 'm.lotsChanged', f"++++ Lot #{lot_number} visits changed: {visits_change}")
            changes.append(visits_change)
            return changes
        helper.printMessage('TRACE', 'm.lotsChanged', f"---- No changes found in Lot #{lot.number} Visits.")

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
                    helper.printMessage("TRACE", 'm.createLots', f">>>> Category to be created: {label}")

        if new_categories:
            created_cats = Category.objects.bulk_create(new_categories.values())
            for cat in created_cats:
                category_cache[cat.label] = cat
                helper.printMessage("TRACE", 'm.createLots', f"++++ Created Category: {cat.label}")


        qualif_cache = {x.name: x for x in Qualif.objects.all()}
        new_qualifs = {}
        agrement_cache = {x.name: x for x in Agrement.objects.all()}
        new_agrements = {}


        helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Tender Qualifs and Agrements ... ")
        for lot_data in input_data:
            for q_data in lot_data.get('qualifs', []):
                name = q_data.get('name')
                if name and name not in qualif_cache and name not in new_qualifs:
                    new_qualifs[name] = Qualif(name=name)
                    helper.printMessage("TRACE", 'm.createLots', f">>>> Qualif to be created: {name}")

            for a_data in lot_data.get('agrements', []):
                name = a_data.get('name')
                if name and name not in agrement_cache and name not in new_agrements:
                    new_agrements[name] = Agrement(name=name)
                    helper.printMessage("TRACE", 'm.createLots', f">>>> Agrement to be created: {name}")

        if new_qualifs:
            created_qualifs = Qualif.objects.bulk_create(new_qualifs.values())
            helper.printMessage("TRACE", 'm.createLots', f"++++ Created Qualifs: {len(created_qualifs)}")
            for x in created_qualifs:
                qualif_cache[x.name] = x
        else:
            helper.printMessage("TRACE", 'm.createLots', "---- Tender has no new Qualifs.")

        if new_agrements:
            created_agrements = Qualif.objects.bulk_create(new_agrements.values())
            helper.printMessage("TRACE", 'm.createLots', f"++++ Created Agrements: {len(created_agrements)}")
            for x in created_agrements:
                agrement_cache[x.name] = x
        else:
            helper.printMessage("TRACE", 'm.createLots', "---- Tender has no new Agrements.")

        lots_to_create = []
        samples_to_create = []
        meetings_to_create = []
        visits_to_create = []

        m2m_qualif_instances = []
        m2m_agrement_instances = []
        LotQualifThrough = Lot.qualifs.through
        LotAgrementThrough = Lot.agrements.through

        i = 0
        for lot_data in input_data:
            i += 1
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot details {i}/{ll} ... ")
            helper.printMessage("TRACE", 'm.createLots', f"Lot {i} raw data:\n\t+++++---------------\n{lot_data}\n\t+++++---------------")
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


        helper.printMessage('DEBUG', 'm.createLots', f">>>> Handling Lots relationships ...")
        i = 0
        print
        for lot_data, created_lot in zip(input_data, created_lots):
            i += 1
            helper.printMessage('DEBUG', 'm.createLots', f">>>>> Handling #{i} relationships ...")
            qualifs_data = lot_data.get('qualifs')
            if len(qualifs_data) > 0 :
                for data_item in qualifs_data:
                    name = data_item.get('name')
                    if name and name in qualif_cache:
                        qualif_obj = qualif_cache[name]
                        m2m_qualif_instances.append(LotQualifThrough(lot=created_lot, qualif=qualif_obj))
                        helper.printMessage('TRACE', 'm.createLots', f">>>>> Lot Qualif to be linked {name} ...")

            agrements_data = lot_data.get('agrements')
            if len(agrements_data) > 0 :
                for data_item in agrements_data:
                    name = data_item.get('name')
                    if name and name in agrement_cache:
                        agrement_obj = agrement_cache[name]
                        m2m_agrement_instances.append(LotAgrementThrough(lot=created_lot, agrement=agrement_obj))
                        helper.printMessage('TRACE', 'm.createLots', f">>>>> Lot Agrement to be linked {name} ...")


            samples_data = lot_data.get('samples')
            if len(samples_data) > 0 :
                for data_item in samples_data:
                    sample_to_create = Sample(lot=created_lot, when=data_item.get('when'), description=data_item.get("description"))
                    samples_to_create.append(sample_to_create)
                    helper.printMessage('TRACE', 'm.createLots', f">>>>> Lot Sample to be created {sample_to_create.when} ...")

            meetings_data = lot_data.get('meetings')
            if len(meetings_data) > 0 :
                for data_item in meetings_data:
                    meeting_to_create = Meeting(lot=created_lot, when=data_item.get('when'), description=data_item.get("description"))
                    meetings_to_create.append(meeting_to_create)
                    helper.printMessage('TRACE', 'm.createLots', f">>>>> Lot Meeting to be created {meeting_to_create.when} ...")

            visits_data = lot_data.get('visits')
            if len(visits_data) > 0 :
                for data_item in visits_data:
                    visit_to_create = Visit(lot=created_lot, when=data_item.get('when'), description=data_item.get("description"))
                    visits_to_create.append(visit_to_create)
                    helper.printMessage('TRACE', 'm.createLots', f">>>>> Lot Visit to be created {visit_to_create.when} ...")


        if m2m_qualif_instances:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Linking Lot Qualifs ... ")
            linked_qualifs = LotQualifThrough.objects.bulk_create(m2m_qualif_instances, batch_size=999, ignore_conflicts=True)
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Linked Qualifs: {len(linked_qualifs)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"--- Tender has no Qualifs.")

        if m2m_agrement_instances:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Linking Lot Agrements ... ")
            linked_agrements = LotAgrementThrough.objects.bulk_create(m2m_agrement_instances, batch_size=999, ignore_conflicts=True)
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Linked Agrements: {len(linked_agrements)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"--- Tender has no Agrements.")

        if samples_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Samples ... ")
            created_samples = Sample.objects.bulk_create(samples_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Samples: {len(created_samples)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"--- Tender has no Samples.")

        if meetings_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Meetings ... ")
            created_meetings = Meeting.objects.bulk_create(meetings_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Meetings: {len(created_meetings)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"--- Tender has no Samples.")

        if visits_to_create:
            helper.printMessage('DEBUG', 'm.createLots', f"#### Handling Lot Visits ... ")
            created_visits = Visit.objects.bulk_create(visits_to_create, batch_size=999) 
            helper.printMessage('DEBUG', 'm.createLots', f"++++ Created Visits: {len(created_visits)}.")
        else:
            helper.printMessage('DEBUG', 'm.createLots', f"--- Tender has no Visits.")

        tender.save()


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
                fields=["title", "description", "category", "estimate", "bond", "variant", "reserved"],
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

        tender_to_update = False
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
            tender_to_update = True
        if m2m_agrement_instances:
            LotAgrementThrough.objects.bulk_create(m2m_agrement_instances, batch_size=999, ignore_conflicts=True)
            tender_to_update = True
        if samples_to_create:
            Sample.objects.bulk_create(samples_to_create, batch_size=999)
            tender_to_update = True
        if meetings_to_create:
            Meeting.objects.bulk_create(meetings_to_create, batch_size=999)
            tender_to_update = True
        if visits_to_create:
            Visit.objects.bulk_create(visits_to_create, batch_size=999)
            tender_to_update = True

        if tender_to_update:
            tender.save()


def logChanges(changed_fields, tender):
    if len(changed_fields) > 0 :
        try:
            helper.printMessage('TRACE', 'm.logChanges', ">>>> Saving change record to databse ... ")
            change = Change(tender=tender, changes=changed_fields)
            change.save()
            log_message = f"++++ Tender {tender.chrono} updated. Changes saved."
            helper.printMessage('DEBUG', 'm.logChanges', log_message)
            helper.printMessage('DEBUG', 'm.logChanges', f".... Reported changes: {changed_fields}")
        except:
            helper.printMessage('WARN', 'm.logChanges', "---- Exception raised saving change to database.")
            traceback.print_exc()

        # if tender_date > target_date:
        try:
            helper.printMessage('TRACE', 'm.logChanges', f"++++ Adding DCE request for Tender {tender.chrono} ... ")
            f2d, _ = FileToGet.objects.update_or_create(tender=tender, defaults={'reason': 'Updated'})
        except:
            helper.printMessage('WARN', 'm.logChanges', "---- Exception raised saving DCE request.")
            traceback.print_exc()

