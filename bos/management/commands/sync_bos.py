import io
import re
import time
import random
from datetime import datetime
from urllib.parse import urljoin
import requests
from pypdf import PdfReader
from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector

from bos.models import Bulletin
from bos.helper import remove_accents

class Command(BaseCommand):
    help = "Syncs bulletin metadata from SGG and indexes PDF text content"

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-text',
            action='store_true',
            help='Only sync metadata, skip downloading and parsing PDFs.',
        )

    def handle(self, *args, **options):
        base_url = "https://www.sgg.gov.ma"
        api_url = f"{base_url}/DesktopModules/MVC/TableListBO/BO/AjaxMethod"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "X-Requested-With": "XMLHttpRequest",
            "ModuleId": "2873",
            "TabId": "775"
        }

        self.stdout.write("Fetching bulletin metadata from SGG...")
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            items = response.json()
            ll = len(items)
            self.stdout.write(f"Fetched {ll} bulletin metadata from website.")
 
            created_count = 0
            counter = 0
            for item in items:
                counter += 1
                self.stdout.write(f"Handling item {counter} / {ll}...")
                bo_num = item.get("BoNum")
                raw_date = item.get("BoDate")
                relative_url = item.get("BoUrl")
                
                if not bo_num or not relative_url:
                    continue
                
                bo_date = None
                if raw_date:
                    match = re.search(r"/Date\((-?\d+)\)/", str(raw_date))
                    if match:
                        timestamp_ms = int(match.group(1))
                        bo_date = datetime.fromtimestamp(timestamp_ms / 1000.0).date()
                
                full_url = urljoin(base_url, relative_url)
                
                obj, created = Bulletin.objects.update_or_create(
                    bo_num=bo_num,
                    defaults={
                        "bo_date": bo_date,
                        "bo_url": full_url
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"\tCreated item N°:{bo_num}, Date: {bo_date}.")
                else:
                    self.stdout.write(f"\tUpdated existing N°:{bo_num}, Date: {bo_date}.")
                    
            self.stdout.write(self.style.SUCCESS(f"Metadata sync complete. Added {created_count} new bulletins."))
            
            # If metadata-only flag is set, stop here
            if options['no_text']:
                self.stdout.write("Skipping text extraction (--no-text flag active).")
                return

            # Text Indexing Phase (Only parse records where extracted_text is missing)
            unindexed = Bulletin.objects.filter(extracted_text__isnull=True) | Bulletin.objects.filter(search_vector__isnull=True) | Bulletin.objects.filter(extracted_text="")
            total_unindexed = unindexed.count()
            
            if total_unindexed == 0:
                self.stdout.write(self.style.SUCCESS("All bulletins already have extracted text!"))
                return

            self.stdout.write(f"Starting text extraction for {total_unindexed} unindexed bulletins...")
            
            for index, bulletin in enumerate(unindexed, 1):
                self.stdout.write(f"[{index}/{total_unindexed}] Parsing BO {bulletin.bo_num}...")
                try:
                    # Polite randomized delay to avoid 503 WAF blocks
                    time.sleep(random.uniform(2.0, 3.0))
                    
                    pdf_res = requests.get(
                        bulletin.bo_url, 
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}, 
                        timeout=25
                    )
                    
                    if pdf_res.status_code == 503:
                        self.stdout.write(self.style.WARNING("Received 503 Server Error. Backing off for 61 seconds..."))
                        time.sleep(61)
                        pdf_res = requests.get(bulletin.bo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
                        
                    if pdf_res.status_code == 200:
                        reader = PdfReader(io.BytesIO(pdf_res.content))
                        raw_text = "".join([page.extract_text() or "" for page in reader.pages])

                        cleaned_text = remove_accents(raw_text)
                        bulletin.extracted_text = cleaned_text
                        bulletin.search_vector = SearchVector('extracted_text', config='french_unaccent')
                        bulletin.save()

                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to download PDF (HTTP {pdf_res.status_code})"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing BO {bulletin.bo_num}: {e}"))

            self.stdout.write(self.style.SUCCESS("Text indexing finished successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync failed: {e}"))

