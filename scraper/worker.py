import os, sys
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

# from base.models import Kind  # Replace with your actual models
# ⸻⸺—⇉→←⇇⇾⇽▶▷◆◀◁⚌➣⟼⟻⧎⬢

def main():
    from datetime import datetime, timedelta

    from scraper import helper, linker, getter , merger, downer
    from scraper import constants as C

    started_time = datetime.now()

    helper.printBanner()
    helper.printMessage('===', 'worker', "▶▷▶▷ The unlazy worker started working ◁◀◁◀◁", 1, 1)
    # av = C.VERBOSITY
    av = next((key for key, val in C.LOGS_LEVELS.items() if val == C.VERBOSITY), "None")
    al = 'Import' if C.IMPORT_LINKS else 'Crawl'
    af = 'Skip' if C.SKIP_DCE else 'Download'
    helper.printMessage('===', 'worker', f"Received arguments: Logs:{ av }, Links:{ al }, Files={ af }", 0, 3)

    links = []
    if not C.IMPORT_LINKS:
        links_live = linker.getlinks_live()
        links_saved = linker.getSavedLinks()
        links = list(set(links_live + links_saved))
        
        linker.exportLinks(links)
    else:
        links = helper.importLinks()



    ll = len(links)
    helper.printMessage('DEBUG', 'worker', f"Count of links to handle: {ll} ...", 1)

    created, updated = 0 , 0
    if ll > 0:
        i = 0
        handled = 0
        helper.printMessage('INFO', 'worker', f"▶▶▶ Getting Data for {ll} links ... ", 2, 0)
        for l in links:
            i += 1
            helper.printMessage('DEBUG', 'worker', f"▷▷ Getting Data for link {i:03}/{ll:03}", 1)
            jsono = getter.getJson(l, not C.REFRESH_EXISTING)            
            if jsono:
                handled += 1
                tender, creation_mode = merger.save(jsono)
                if creation_mode == True:
                    created += 1
                    helper.printMessage('INFO', 'worker', f"◁◁ Created Tender {tender.chrono}")
                elif creation_mode == False: 
                    updated += 1
                    helper.printMessage('INFO', 'worker', f"◁◁ Updated Tender {tender.chrono}")

            if handled > 0:
                if handled % C.BURST_LENGTH == 0:
                    helper.printMessage('DEBUG', 'worker', f"Sleeping << { handled } Tenders handled. Burst is { C.BURST_LENGTH }.", 1)
                    helper.printMessage('INFO', 'worker', "zzzzzzzzzz Sleeping for a while zzzzzzzzzz", 1)
                    helper.sleepRandom(10, 30)
                    handled = 0
    else:
        helper.printMessage('ERROR', 'worker', "◆◆◆◆◆◆◆◆◆◆ Links list was empty ◆◆◆◆◆◆◆◆◆◆", 2)

    helper.printMessage('===', 'worker', f"◀◀◀ Saving data finished.", 1)

    dceed, fceed = 0, 0
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
                dceed += 1
                helper.printMessage('INFO', 'worker', f"◀◀ DCE download for { d.chrono } was successfull.")
            else:
                fceed += 1
                helper.printMessage('WARN', 'worker', f"⬢⬢ Something went wrong whith DCE download for { d.chrono }.")

            hceed = dceed + fceed
            if hceed > 0:
                if hceed % C.BURST_LENGTH == 0:
                    helper.printMessage('DEBUG', 'worker', f"Sleeping << DCE: { dceed } success + { fceed } fails = { hceed }. Burst is { C.BURST_LENGTH }.", 1)
                    helper.printMessage('INFO', 'worker', "⧎⧎⧎ Sleeping for a while ⧎⧎⧎", 1)
                    helper.sleepRandom(10, 30)
        # helper.printMessage('INFO', 'worker', f"◀◀◀ Downloaded DCE files for {dceed} items", 2)
        # if fceed > 0:
        #     helper.printMessage('INFO', 'worker', f"⬢⬢⬢ Failed to download DCE files for {fceed} items")

    finished_time = datetime.now()
    work_duration = finished_time - started_time

    helper.printMessage('===', 'worker', f"⇉⇉⇉ Created {created}, updated {updated} Tenders.", 2)
    helper.printMessage('===', 'worker', f"⇉⇉⇉ Downloaded {dceed} DCE files, {fceed} downloads failed.", 2)
    formatted_duration = f"{work_duration.hours}:{work_duration.minutes:02d}:{int(work_duration.seconds):02d}"
    helper.printMessage('===', 'worker', f"⇉⇉⇉ That took our unlazy worker { formatted_duration }.")
    helper.printMessage('===', 'worker', f"▶▷▶▷▶▷▶▷▶▷ The unlazy worker is done working ◀◁◀◁◀◁◀◁◀◁", 1, 1)


if __name__ == '__main__':
    main()
