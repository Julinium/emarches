import os, sys
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()


def main():
    from datetime import datetime, timedelta
    from scraper import helper, linker, getter , merger, downer, bonner
    from scraper import constants as C
    from base.models import Crawler

    started_time = datetime.now()

    helper.printBanner()
    helper.printMessage('===', 'worker', "▶▷▶▷ The unlazy worker started working ◁◀◁◀", 1, 1)

    av = next((key for key, val in C.LOGS_LEVELS.items() if val == C.VERBOSITY), "None")
    al = 'Import' if C.IMPORT_LINKS else 'Crawl'
    af = 'Skip' if C.SKIP_DCE else 'Download'
    helper.printMessage('===', 'worker', f"Received arguments: Logs:{ av }, Links:{ al }, Files={ af }", 0, 3)

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
    
    def handle_bdcs():
        print('\n\n======================================================')
        helper.printMessage('===', 'worker', f"▶▶▶▶▶ Now, let's do some Purchase orders ◀◀◀◀◀", 1, 1)
        bonner.save_bdcs(30)
        bonner.save_results()
        print('\n======================================================\n')
    
    if not C.IMPORT_LINKS:
        handle_bdcs()


    helper.printMessage('===', 'worker', f"◀◀◀ Saving data finished.", 1)

    files_downloaded, files_failed = 0, 0
    if C.SKIP_DCE:
        helper.printMessage('===', 'worker', "◆◆◆◆◆ SKIP_DCE set. Skipping DCE files ◆◆◆◆◆", 2)
    else:
        i = 0
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
                helper.printMessage('WARN', 'worker', f"⬢⬢ Something went wrong whith DCE download for { d.chrono }.")

            hceed = files_downloaded + files_failed
            if hceed > 0:
                if hceed % C.BURST_LENGTH == 0:
                    helper.printMessage('DEBUG', 'worker', f"Sleeping << DCE: { files_downloaded } success + { files_failed } fails = { hceed }. Burst is { C.BURST_LENGTH }.", 1)
                    helper.printMessage('INFO', 'worker', "⧎⧎⧎ Sleeping for a while ⧎⧎⧎", 1)
                    helper.sleepRandom(10, 30)

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

    work_duration = finished_time - started_time

    helper.printMessage('===', 'worker', f"⇉⇉⇉ Created {tenders_created}, updated {tenders_updated} Tenders.", 2)
    helper.printMessage('===', 'worker', f"⇉⇉⇉ Downloaded {files_downloaded} DCE files, {files_failed} downloads failed.", 2)
    helper.printMessage('===', 'worker', f"⇉⇉⇉ That took our unlazy worker { work_duration }.")
    helper.printMessage('===', 'worker', f"▶▷▶▷▶▷▶▷▶▷ The unlazy worker is done working ◀◁◀◁◀◁◀◁◀◁", 1, 1)
    

if __name__ == '__main__':
    main()
