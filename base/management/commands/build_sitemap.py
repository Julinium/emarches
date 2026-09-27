import os
import urllib.parse
import urllib.request
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string

from emarches.sitemaps import ConcurrentSitemap, TenderSitemap


MAX_URLS_PER_SITEMAP = 5000

class Command(BaseCommand):
    help = "Generates static sitemap_index.xml and chunked sitemap XML files on disk for NGINX."

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default=getattr(settings, 'SITE_HOST', 'https://new.emarches.com'),
            help='Base domain (with protocol) used to generate sitemap index URLs.'
        )
        # parser.add_argument(
        #     '--ping',
        #     action='store_true',
        #     help='Ping Google with the new sitemap index URL after generation.'
        # )

    def handle(self, *args, **options):
        base_domain = options['domain'].rstrip('/')
        # ping_google = options['ping']

        sitemaps = {
            'tenders': TenderSitemap,
            'concurrents': ConcurrentSitemap,
        }

        # 1. Exhaustively collect ALL items across ALL pages of ALL sitemap classes
        self.stdout.write("--- Started generating sitemap structure ...")
        
        all_items = []
        for section, site_cls in sitemaps.items():
            site = site_cls() if callable(site_cls) else site_cls
            
            # Check total pages provided by Django's BaseSitemap paginator
            paginator = site.paginator
            total_pages = paginator.num_pages

            # Iterate through every page explicitly
            for page in range(1, total_pages + 1):
                self.stdout.write(f"---- Handling { section } page { page } from { total_pages } ...")
                try:
                    urls = site.get_urls(page=page)
                    all_items.extend(urls)
                except (EmptyPage, PageNotAnInteger) as e:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping empty/invalid page {page} for section '{section}': {e}")
                    )

        total_items = len(all_items)
        if total_items == 0:
            self.stdout.write(self.style.WARNING("No sitemap items found. Skipping generation."))
            return

        self.stdout.write(self.style.SUCCESS(f"Collected total of {total_items} URLs across all sitemaps."))

        # Output directory (e.g., project_root/sitemaps/)
        output_dir = os.path.join(settings.BASE_DIR, 'sitemaps')
        os.makedirs(output_dir, exist_ok=True)

        # 2. Chunk items into individual sitemap files
        chunks = [
            all_items[i : i + MAX_URLS_PER_SITEMAP]
            for i in range(0, total_items, MAX_URLS_PER_SITEMAP)
        ]

        generated_sitemap_urls = []

        for index, chunk in enumerate(chunks, start=1):
            filename = f"sitemap-{index}.xml"
            filepath = os.path.join(output_dir, filename)

            # Render standard sitemap template for this chunk
            xml_content = render_to_string('sitemap.xml', {'urlset': chunk})

            # Atomic write via temp file
            temp_filepath = filepath + '.tmp'
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            os.replace(temp_filepath, filepath)

            sitemap_url = f"{base_domain}/sitemaps/{filename}"
            generated_sitemap_urls.append(sitemap_url)

            self.stdout.write(self.style.SUCCESS(f"Generated {filename} ({len(chunk)} URLs)"))

        # 3. Build and render sitemap_index.xml
        index_items = [{'location': url} for url in generated_sitemap_urls]
        index_xml_content = render_to_string('sitemap_index.xml', {'sitemaps': index_items})

        index_filepath = os.path.join(output_dir, 'sitemap_index.xml')
        temp_index_filepath = index_filepath + '.tmp'
        
        with open(temp_index_filepath, 'w', encoding='utf-8') as f:
            f.write(index_xml_content)
        os.replace(temp_index_filepath, index_filepath)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated sitemap_index.xml referencing {len(generated_sitemap_urls)} file(s)."
            )
        )

        # 4. Optional: Ping Google Search Console
        # if ping_google:
        #     index_url = f"{base_domain}/sitemap.xml"
        #     self.stdout.write(f"Pinging Google with {index_url}...")
        #     try:
        #         ping_endpoint = f"https://www.google.com/ping?sitemap={urllib.parse.quote(index_url)}"
        #         req = urllib.request.Request(ping_endpoint, headers={'User-Agent': 'Mozilla/5.0'})
        #         with urllib.request.urlopen(req) as response:
        #             if response.status == 200:
        #                 self.stdout.write(self.style.SUCCESS("Google ping successful."))
        #     except Exception as e:
        #         self.stdout.write(self.style.ERROR(f"Failed to ping Google: {e}")) 