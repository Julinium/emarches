import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from parler.utils.context import switch_language

from flows.models import Category, Feature, Plan, Allowance

LANGUAGES = ("en", "fr", "ar", "zg", "es", "de")


class Command(BaseCommand):
    help = "Create or update Categories and Features from a translated JSON catalog."

    def add_arguments(self, parser):
        parser.add_argument("json_file", help="Path to catalog_translated.json")
        parser.add_argument("--deactivate-missing", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["json_file"])
        try:
            with path.open(encoding="utf-8") as stream:
                catalog = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Cannot read {path}: {exc}") from exc

        category_codes, feature_codes = set(), set()
        stats = {"categories_created": 0, "categories_updated": 0,
                 "features_created": 0, "features_updated": 0}

        def save_translations(obj, translations, fields, code):
            for lang in LANGUAGES:
                values = translations.get(lang)
                if not values or not values.get("name"):
                    raise CommandError(f"Missing {lang} name translation for {code}")
                with switch_language(obj, lang):
                    for field in fields:
                        setattr(obj, field, values.get(field) or None if field == "description"
                                else values[field])
                    obj.save()

        plan_codes = {
            "plan_free": "plan_free",
            "plan_startup": "plan_startup",
            "plan_pro": "plan_pro",
        }
        
        i = 0
        for item in catalog:
            i += 1
            code = item["code"]
            self.stdout.write(f"Handling category {i:02d}: {code} ...")
            category_codes.add(code)
            category, created = Category.objects.get_or_create(
                code=code,
                defaults={"active": bool(item.get("active", True)),
                          "rank": int(item.get("rank", 0))},
            )
            stats["categories_created" if created else "categories_updated"] += 1
            category.active = bool(item.get("active", True))
            category.rank = int(item.get("rank", 0))
            category.save(update_fields=["active", "rank"])
            save_translations(category, item.get("translations", {}), ("name",), code)

            j = 0
            for fitem in item.get("features", []):
                j += 1
                fcode = fitem["code"]
                self.stdout.write(f"\tHandling feature {j:02d}: {fcode} ...")
                feature_codes.add(fcode)
                feature, created = Feature.objects.get_or_create(
                    code=fcode,
                    defaults={"active": bool(fitem.get("active", True)),
                              "rank": int(fitem.get("rank", 10)),
                              "category": category,
                              "is_binary": bool(fitem.get("is_binary", True))},
                )
                stats["features_created" if created else "features_updated"] += 1
                feature.active = bool(fitem.get("active", True))
                feature.rank = int(fitem.get("rank", 10))
                feature.category = category
                feature.is_binary = bool(fitem.get("is_binary", True))
                feature.save(update_fields=["active", "rank", "category", "is_binary"])
                save_translations(feature, fitem.get("translations", {}),
                                  ("name", "description"), fcode)

                self.stdout.write("\tUpdating plans capabilties ...")
                for json_field, plan_code in plan_codes.items():
                    plan = Plan.objects.get(code=plan_code)
                    Allowance.objects.update_or_create(
                        plan=plan,
                        feature=feature,
                        defaults={
                            "capability": int(fitem.get(json_field, 0)),
                        },
                    )

        if options["deactivate_missing"]:
            self.stdout.write("Deactivating missing items ...")
            Category.objects.exclude(code__in=category_codes).update(active=False)
            Feature.objects.exclude(code__in=feature_codes).update(active=False)


        self.stdout.write(self.style.SUCCESS(
            f"Done: {stats['categories_created']} categories created, "
            f"{stats['categories_updated']} updated; "
            f"{stats['features_created']} features created, "
            f"{stats['features_updated']} updated."
        ))
