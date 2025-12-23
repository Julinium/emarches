import os, sys, traceback
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()


def main():
    from datetime import datetime, timedelta
    from scraper import helper, linker, getter , merger, downer, bonner
    from scraper import constants as C
    from base.models import Tender, Crawler

    started_time = datetime.now()

    
    def handle_bdcs():
        if links_source == 'Crawl':
            helper.printMessage('===', 'worker', f"▶▶▶▶▶ Started Purchase orders ◀◀◀◀◀", 3, 1)
            bonner.save_bdcs()
            bonner.save_results()


    def handle_dce():
        i = 0
        files_downloaded, files_failed = 0, 0
        try:
            helper.printMessage('INFO', 'worker', "▶▶▶ Getting the list of DCE files to download ...", 1)
            dceables = downer.getFileables()
            c = dceables.count()
            helper.printMessage('INFO', 'worker', f"▶▶▶ Started getting DCE files for { c } items ...", 1)
            for d in dceables:
                i += 1
                helper.printMessage('INFO', 'worker', f"▶▶ Getting DCE files for { i }/{ c } : { d.chrono } ...", 1)
                getdce = downer.getDCE(d)
                if getdce == 0:
                    files_downloaded += 1
                    helper.printMessage('INFO', 'worker', f"◀◀ DCE download for { d.chrono } was successfull.")
                else:
                    files_failed += 1
                    helper.printMessage('WARN', 'worker', f"⬢⬢⬢⬢⬢ Something went wrong whith DCE download for { d.chrono }.")

                hceed = files_downloaded + files_failed
                if hceed > 0:
                    if hceed % C.BURST_LENGTH == 0:
                        helper.printMessage('DEBUG', 'worker', f"Sleeping << DCE: { files_downloaded } success + { files_failed } fails = { hceed }. Burst is { C.BURST_LENGTH }.", 1)
                        helper.printMessage('INFO', 'worker', "⧎⧎⧎ Sleeping for a while ⧎⧎⧎", 1)
                        helper.sleepRandom(10, 30)
        except Exception as xc:
            helper.printMessage('ERROR', 'worker', f"⬢⬢⬢ Exception while handling DCE files: { xc } ", 1)
            traceback.print_exc()
            
        return files_downloaded, files_failed


    def handle_results():

        results_saved, results_searched = 0, 0
        helper.printMessage('INFO', 'worker', f"▶▶▶▶▶ Started handling Tenders Results ◀◀◀◀◀", 2, 1)
        assa = datetime.now().date()


        # @property
        # def won_lots(self):
        #     return self.winner_bids.aggregate(won_lots=Count("lot_number", distinct = True))["won_lots"]
        
        # @property
        # def total_win(self):
        #     return self.won_lots == self.tender.lots_count

        # tenders = Tender.objects.annotate(
        #     won_lots = Count("minutes__winner_bids__lot_number", distinct = True)
        # )


        tenders = Tender.objects.filter(
            deadline__date__lte=assa,
            minutes__isnull=True, 
            ).order_by('-deadline')
        count = tenders.count()

        i = 0
        for tender in tenders:
            i += 1
            if i % C.BURST_LENGTH == 0: helper.sleepRandom(30, 35)

            helper.printMessage('INFO', 'worker', f"Working on item { i }/{ count } = {tender.chrono}&{tender.acronym}")
            result = getter.getMinutes(tender.chrono, tender.acronym)
            if result and result != {}:
                helper.printMessage('INFO', 'worker', f"\tMinutes found for item { i }/{ count }")
                try:
                    if merger.mergeResults(result) == 0:
                        results_saved += 1
                        helper.printMessage('DEBUG', 'worker', f"\tSaved Minutes for item { i }/{ count }")
                except Exception as xc : 
                    helper.printMessage('ERROR', 'worker', f"\tError saving Minutes for item { i }/{ count }: \n\n { result }\n\n")
                    traceback.print_exc()
            else:
                helper.printMessage('INFO', 'worker', f"\tMinutes emty or not found for item { i }/{ count }")
        
        return results_saved, i



    ##### Proudly let the magic happen
    helper.printBanner()
    helper.printMessage('===', 'worker', "▶▷▶▷ The unlazy worker started working ◁◀◁◀", 1, 1)
    logging_level = next((key for key, val in C.LOGS_LEVELS.items() if val == C.VERBOSITY), "None")
    links_source  = 'Import' if C.IMPORT_LINKS else 'Crawl'
    files_action  = 'Skip' if C.SKIP_DCE else 'Download'
    helper.printMessage('===', 'worker', f"Arguments: Logging: { logging_level }, Links source: { links_source }, Files: { files_action  }", 0, 3)



    ##### Collect the list of links to handle
    links_crawled, links_imported, links_from_saved = 0,0,0
    links = []
    if not C.IMPORT_LINKS:
        links = linker.getLinks()
        links_crawled = len(links)
        links_saved = linker.getSavedLinks()
        links_from_saved = len(links_saved)
        helper.printMessage('INFO', 'worker', f"Merging links:{ links_crawled } live and { links_from_saved } from saved")
        ml = 0
        for l in links_saved:
            if l not in links:
                ml += 1
                links.append(l)
        helper.printMessage('INFO', 'worker', f"+++ Merged { ml } saved links to live")

        linker.exportLinks(links)
    else:
        links = helper.importLinks()
        links_imported = len(links)

    ll = len(links)
    helper.printMessage('DEBUG', 'worker', f"Count of links to handle: {ll} ...", 1)



    ##### Get the Tenders data
    saving_errors = False
    tenders_created, tenders_updated = 0 , 0
    if ll > 0:
        i = 0
        handled = 0
        helper.printMessage('INFO', 'worker', f"▶▶▶ Getting Data for {ll} links ... ", 2, 0)
        for l in links:
            i += 1
            helper.printMessage('INFO', 'worker', f"▷▷ Getting Data for link {i:03}/{ll:03}", 1)
            jsono = getter.getJson(l, not C.REFRESH_EXISTING)            
            if jsono:
                handled += 1
                tender, creation_mode = merger.save(jsono)
                if creation_mode == True:
                    tenders_created += 1
                    helper.printMessage('INFO', 'worker', f"◁◁ Created Tender {tender.chrono}")
                elif creation_mode == False: 
                    tenders_updated += 1
                    helper.printMessage('INFO', 'worker', f"◁◁ Updated Tender {tender.chrono}")

            if handled > 0:
                if handled % C.BURST_LENGTH == 0:
                    helper.printMessage('DEBUG', 'worker', f"Sleeping << { handled } Tenders handled. Burst is { C.BURST_LENGTH }.", 1)
                    helper.printMessage('INFO', 'worker', "zzzzzzzzzz Sleeping for a while zzzzzzzzzz", 1)
                    helper.sleepRandom(10, 30)
                    handled = 0
    else:
        saving_errors = True
        helper.printMessage('ERROR', 'worker', "◆◆◆◆◆◆◆◆◆◆ Links list was empty ◆◆◆◆◆◆◆◆◆◆", 2)



    ##### Handle Purchase Orders
    handle_bdcs()
    helper.printMessage('===', 'worker', f"◀◀◀ Saving data finished.", 1)



    ##### Take care of DCE files
    files_downloaded, files_failed = 0, 0
    if C.SKIP_DCE: helper.printMessage('===', 'worker', "◆◆◆◆◆ SKIP_DCE set. Skipping DCE files ◆◆◆◆◆", 2)
    else: files_downloaded, files_failed = handle_dce()



    ##### Get Tenders results:
    results_saved, results_searched = 0, 0
    if links_source == 'Crawl':
        results_saved, results_searched = handle_results()



    ##### Keep track of update times
    finished_time = datetime.now()
    crawler = Crawler(
        started = started_time,
        finished = finished_time,
        import_links = C.IMPORT_LINKS,
        links_crawled = links_crawled,
        links_imported = links_imported,
        links_from_saved = links_from_saved,
        tenders_created = tenders_created,
        tenders_updated = tenders_updated,
        files_downloaded = files_downloaded,
        files_failed = files_failed,
        saving_errors = saving_errors
    )
    crawler.save()



    ##### Show a digest
    work_duration = finished_time - started_time
    helper.printMessage('===', 'worker', f"⇉⇉⇉ Created {tenders_created}, updated {tenders_updated} Tenders.")
    helper.printMessage('===', 'worker', f"⇉⇉⇉ Downloaded {files_downloaded} DCE files, {files_failed} downloads failed.")
    helper.printMessage('===', 'worker', f"⇉⇉⇉ Scanned {results_searched}, saved {results_saved} Tenders results.")
    helper.printMessage('===', 'worker', f"⇉⇉⇉ That took our unlazy worker { work_duration }.")
    helper.printMessage('===', 'worker', f"▶▷▶▷▶▷▶▷▶▷ The unlazy worker is done working ◀◁◀◁◀◁◀◁◀◁", 1, 1)
    

if __name__ == '__main__':
    main()


