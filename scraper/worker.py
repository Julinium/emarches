import os
import sys
import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()


def do_the_work():
    from django.utils import timezone
    from datetime import datetime, timedelta

    from base.models import Crawler, Tender, Link, Machine, Parkour, Harvest
    from scraper import bonner
    from scraper import constants as C
    from scraper import downer, getter, helper, linker, merger

    started_time = timezone.now()

    def linkify():
        unhandled_links = list(Link.objects.filter(handled=False) | Link.objects.filter(tender__isnull=True))
        helper.printMessage('INFO', 'w.linkify', f"Found { len(unhandled_links) } leftover links.")
        # unhandled_links = []

        if not C.IMPORT_LINKS:
            back_days = C.PORTAL_DDL_PAST_DAYS if C.REFRESH_EXISTING else 1
            links_crawled = linker.getLinks(back_days)
            helper.printMessage('INFO', 'w.linkify', f"Crawled { len(links_crawled) } live links.")
            merged_links_crawled = linker.mergeLinks(links_crawled)
            # unhandled_links += merged_links_crawled
            unhandled_links += merged_links_crawled
            # unhandled_links = set(merged_links_crawled)

        if C.REFRESH_EXISTING:
            links_saved = linker.db2Links(C.PORTAL_DDL_PAST_DAYS) if C.REFRESH_EXISTING else []
            helper.printMessage('INFO', 'w.linkify', f"Found { len(links_saved) } saved links.")
            if links_saved != []:
                # unique_saved_links = links_saved.difference(unhandled_links)
                unhandled_chronos = [l.chrono for l in unhandled_links]
                unique_saved_links = [l for l in links_saved if l.get("chrono") not in unhandled_chronos]
                # unique_saved_links = [l for l in links_saved if not l.chrono in unhandled_links.values("chrono") ]

                helper.printMessage('INFO', 'w.linkify', f"Merging { len(unique_saved_links) } unique saved links ...")
                merged_links_saved = linker.mergeLinks(unique_saved_links)
                # unhandled_links += merged_links_saved
                unhandled_links += merged_links_saved

        helper.printMessage('DEBUG', 'w.linkify', f"Count of links to handle: {len(unhandled_links)} ...", 1)
    
        return unhandled_links

    def xinkify():
        # unhandled_links = list(Link.objects.filter(handled=False) | Link.objects.filter(tender__isnull=True))
        unhandled_links = []

        if not C.IMPORT_LINKS:
            back_days = C.PORTAL_DDL_PAST_DAYS if C.REFRESH_EXISTING else 1
            links_crawled = linker.getLinks(back_days)
            helper.printMessage('INFO', 'w.linkify', f"Merging { len(links_crawled) } Crawled links ...")
            merged_links_crawled = linker.mergeLinks(links_crawled)
            # unhandled_links += merged_links_crawled
            # unhandled_links = set(unhandled_links) | set(merged_links_crawled)
            unhandled_links = set(merged_links_crawled)

        if C.REFRESH_EXISTING:
            links_saved = linker.db2Links(C.PORTAL_DDL_PAST_DAYS) if C.REFRESH_EXISTING else []
            helper.printMessage('INFO', 'w.linkify', f"Merging { len(links_saved) } found links ...")
            merged_links_saved = linker.mergeLinks(links_saved)
            # unhandled_links += merged_links_saved
            unhandled_links = set(unhandled_links) | set(merged_links_saved)

        helper.printMessage('DEBUG', 'w.linkify', f"Count of links to handle: {len(unhandled_links)} ...", 1)
    
        return unhandled_links

    def tenderify(links=[]):
        started = datetime.now()        
        saving_errors = False
        tenders_created, tenders_updated = 0 , 0
        ll = len(links)
        if ll > 0:
            i = 0
            handled = 0
            helper.printMessage('INFO', 'w.tenderify', f"▶▶▶ Getting Data for {ll} links ... ", 2, 0)
            for l in links:
                i += 1
                helper.printMessage('INFO', 'w.tenderify', f"▷▷ Getting Data for link {i:03}/{ll:03}", 1)
                jsono = getter.getJson(l, not C.REFRESH_EXISTING)            
                if jsono:
                    handled += 1
                    tender, creation_mode, changes_found = merger.saveTender(jsono, l)
                    # linked = merger.linder(tender, l)
                    if creation_mode == True:
                        tenders_created += 1
                        helper.printMessage('INFO', 'w.tenderify', f"◁◁ Created Tender {tender.chrono}")
                    else:
                        if changes_found == True:
                            tenders_updated += 1
                            helper.printMessage('INFO', 'w.tenderify', f"◁◁ Tender {tender.chrono} updated.")

                if handled > 0:
                    if handled % C.BURST_LENGTH == 0:
                        helper.printMessage('DEBUG', 'w.tenderify', f"Burst ({ C.BURST_LENGTH }) at {i:03}/{ll:03}. Handled { tenders_created + tenders_updated } tenders. ({ tenders_created } + {tenders_updated }).", 1)
                        helper.printMessage('DEBUG', 'w.tenderify', "zzzzzzzzzz Sleeping for a while zzzzzzzzzz", 1)
                        helper.sleepRandom(20, 45)
                        handled = 0
        else:
            saving_errors = True
            helper.printMessage('ERROR', 'w.tenderify', "◆◆◆◆◆◆◆◆◆◆ Links list was empty ◆◆◆◆◆◆◆◆◆◆", 2)

        ############
        try:
            machine_info = helper.get_system_info()
            machine, created = Machine.objects.get_or_create(
                hostname=machine_info['hostname'],
                os_family=machine_info['os_family'],
                processor=machine_info['processor'],
                defaults={
                    "ip_address": machine_info['ip_address'],
                    "os_version": machine_info['os_version'],
                    "os_release": machine_info['os_release'],
                    "architecture": machine_info['architecture'],
                    "python_version": machine_info['python_version'],
                }
            )
            if created:
                helper.printMessage('INFO', 'l.getLinks', f'Created Machine info: {machine_info['hostname']}')
            else:
                helper.printMessage('INFO', 'l.getLinks', f'Machine info already exists: {machine_info['hostname']}')

            harvest = Harvest.objects.create(
                    started       = started,
                    finished      = timezone.now(),
                    machine       = machine,
                    links_handled = ll,
                    tenders_created = tenders_created,
                    tenders_updated = tenders_updated,
                    # tenders_discarded = 0,
                    # dce_files_downloaded = 0,
                    # extra_files_downloaded = 0,
                    # dce_files_failed = 0,
                    # extra_files_failed = 0,
                    successfull = not saving_errors,
                )

            if harvest:
                helper.printMessage('DEBUG', 'l.getLinks', 'Created Harvest record.')
            else:
                helper.printMessage('ERROR', 'l.getLinks', 'Errors occurred while creating Harvest record.')

        except Exception as e:
            helper.printMessage('ERROR', 'l.getLinks', f'Error while handling Machine info: {str(e)}', 2,2)

        ############
        
        return tenders_created, tenders_updated, saving_errors

    def bdcify():
        helper.printMessage('===', 'w.bdcify', f"▶▶▶▶▶ Started Purchase orders ◀◀◀◀◀", 3, 1)
        bonner.save_bdcs()
        bonner.save_results()

    def dceify():
        i = 0
        files_downloaded, files_failed = 0, 0
        try:
            helper.printMessage('INFO', 'w.dceify', "▶▶▶ Getting the list of DCE files to download ...", 1)
            dceables = downer.getFileables()
            c = dceables.count()
            helper.printMessage('INFO', 'w.dceify', f"▶▶▶ Started getting DCE files for { c } items ...", 1)
            for d in dceables:
                i += 1
                helper.printMessage('INFO', 'w.dceify', f"▶▶ Getting DCE files for { i }/{ c } : { d.chrono } ...", 1)
                getdce = merger.handleDCE(d)
                if getdce:
                    files_downloaded += 1
                    helper.printMessage('INFO', 'w.dceify', f"◀◀ DCE download for { d.chrono } was successfull.")
                else:
                    files_failed += 1
                    helper.printMessage('WARN', 'w.dceify', f"⬢⬢⬢⬢ Something went wrong whith DCE download for { d.chrono }.")

                hceed = files_downloaded + files_failed
                if hceed > 0:
                    if hceed % C.BURST_LENGTH == 0:
                        helper.printMessage('DEBUG', 'w.dceify', f"Sleeping << DCE: { files_downloaded } success + { files_failed } fails = { hceed }. Burst is { C.BURST_LENGTH }.", 1)
                        helper.printMessage('INFO', 'w.dceify', "⧎⧎⧎ Sleeping for a while ⧎⧎⧎", 1)
                        helper.sleepRandom(10, 30)
        except Exception as xc:
            helper.printMessage('ERROR', 'w.dceify', f"⬢⬢⬢ Exception while handling DCE files: { xc } ", 1)
            traceback.print_exc()
            
        return files_downloaded, files_failed

    def resultify(back_days=C.PORTAL_RES_PAST_DAYS):

        results_saved, results_searched = 0, 0
        helper.printMessage('INFO', 'w.resultify', f"▶▶▶▶▶ Started handling Tenders Results ◀◀◀◀◀", 0, 0)
        assa = timezone.now().date()
        assenn = assa - timedelta(days=back_days)

        tenders = Tender.objects.filter(
            deadline__date__lte=assa,
            deadline__date__gte=assenn,
            openings__isnull=True,
            has_minutes=False,
            ).order_by('deadline')
        count = tenders.count()

        i = 0
        for tender in tenders:
            i += 1
            if i % C.BURST_LENGTH == 0: helper.sleepRandom(30, 35)

            helper.printMessage('INFO', 'w.resultify', f"▷▷▷ Getting results for item { i }/{ count }", 1)
            result = getter.getMinutes(tender.chrono, tender.acronym)
            if result and result != {}:
                helper.printMessage('INFO', 'w.resultify', f"◁◁◁ Minutes found for item { i }/{ count }")
                try:
                    if merger.mergeResults(result) == 0:
                        results_saved += 1
                        helper.printMessage('DEBUG', 'w.resultify', f"\tSaved Minutes for item { i }/{ count }")
                except Exception as xc : 
                    helper.printMessage('ERROR', 'w.resultify', f"\tError saving Minutes for item { i }/{ count }")
                    helper.printMessage('DEBUG', 'w.resultify', f"Received object: \n{ result }\n")
                    helper.printMessage('DEBUG', 'w.resultify', f"Raised Exception: \n{ xc }\n")
                    traceback.print_exc()
            else:
                helper.printMessage('INFO', 'w.resultify', f"◀◀◀ No Minutes found for item { i }/{ count }")

        return results_saved, i


    ##### Proudly let the magic happen
    helper.printBanner()
    helper.printMessage('INFO', 'worker', "▶▷▶▷ The unlazy worker started working ◁◀◁◀", 0, 0)
    logging_level = next((key for key, val in C.LOGS_LEVELS.items() if val == C.VERBOSITY), "None")
    links_source  = 'Import' if C.IMPORT_LINKS else 'Crawl'
    files_action  = 'Skip' if C.SKIP_DCE else 'Download'
    results_action = 'Get' if C.GET_RESULTS else 'Skip'
    helper.printMessage('INFO', 'worker', f"Arguments: Logging: { logging_level }, Links source: { links_source }, Files: { files_action  }, Results: { results_action  }", 0, 0)

    ##### Collect the list of links to handle
    links = linkify()
    helper.printMessage('INFO', 'worker', f"◀◀◀ Finished getting {len(links)} links.", 0)

    ##### Get the Tenders data
    tenders_created, tenders_updated, saving_errors = tenderify(links)
    helper.printMessage('INFO', 'worker', f"◀◀◀ Finished saving tenders data.", 0)

    ##### Handle Purchase Orders
    if links_source == 'Crawl':
        bdcify()
        helper.printMessage('INFO', 'worker', f"◀◀◀ Finished saving PO's data.", 0)

    ##### Take care of DCE files
    files_downloaded, files_failed = 0, 0
    if C.SKIP_DCE: helper.printMessage('INFO', 'worker', "◆◆◆◆◆ SKIP_DCE set. Skipping DCE files ◆◆◆◆◆", 1)
    else: files_downloaded, files_failed = dceify()

    # TODO: Consider other "types" of publications, like:
    """
        résultats définitifs
        rapports d'achèvement
        rapports de présentation
        décisions de résiliation
        Annonce de programme previsionnel
        Annonce de synthèse de rapport d'audit
        bons de commande attribués
        marchés attribués
        conventions et contrats de droit commun
    """

    ##### Get Tenders results:
    results_saved, results_searched = 0, 0
    if C.GET_RESULTS == False: 
        helper.printMessage('INFO', 'worker', "◆◆◆◆◆ SKIP_RESULTS set. Skipping Results digests ◆◆◆◆◆", 1)
    else:
        results_saved, results_searched = resultify()

    ##### Keep track of update times
    finished_time = timezone.now()
    crawler = Crawler(
            started = started_time,
            finished = finished_time,
            import_links = C.IMPORT_LINKS,
            # links_crawled = links_crawled,
            # links_imported = links_imported,
            # links_from_saved = links_from_saved,
            tenders_created = tenders_created,
            tenders_updated = tenders_updated,
            files_downloaded = files_downloaded,
            files_failed = files_failed,
            saving_errors = saving_errors
        )
    try:
        crawler.save()
    except Exception as xc:
        helper.printMessage('ERROR', 'worker', f"⬢⬢⬢ Exception while saving Crawler object: { xc } ", 1)
        traceback.print_exc()


    ##### Show a digest
    work_duration = finished_time - started_time
    helper.printMessage('INFO', 'worker', f"⇉⇉⇉ Created {tenders_created}, updated {tenders_updated} Tenders.", 3)
    helper.printMessage('INFO', 'worker', f"⇉⇉⇉ Downloaded {files_downloaded} DCE files, {files_failed} downloads failed.")
    helper.printMessage('INFO', 'worker', f"⇉⇉⇉ Scanned {results_searched}, saved {results_saved} Tenders results.")
    helper.printMessage('INFO', 'worker', f"⇉⇉⇉ That took our unlazy worker { work_duration }.")
    helper.printMessage('INFO', 'worker', f"▶▷▶▷▶▷▶▷▶▷ The unlazy worker is done working ◀◁◀◁◀◁◀◁◀◁", 1, 0)


if __name__ == '__main__':
    do_the_work()

