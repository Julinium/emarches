
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from flows.models import Allowance, Feature, Plan


class Command(BaseCommand):
    help = "Create or update subscription plans from plans.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=Path,
            default=Path(settings.BASE_DIR) / "flows/data/plans.json",
            help="Path to the plans JSON definition file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and simulate synchronization without saving changes.",
        )

    def handle(self, *args, **options):
        path = options["file"]

        try:
            with path.open(encoding="utf-8") as file:
                definition = json.load(file)
        except OSError as exc:
            raise CommandError(f"Cannot read {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        self.stdout.write(f"Reading plans file ...")

        languages = definition.get("languages", [])
        plans_data = definition.get("plans", [])

        if not languages or len(languages) != len(set(languages)):
            raise CommandError("'languages' must be a non-empty unique list.")

        if not isinstance(plans_data, list):
            raise CommandError("'plans' must be a list.")

        # Validate the whole definition before writing anything.
        required_languages = set(languages)
        seen_codes = set()

        self.stdout.write(f"Got {len(plans_data)} plans to synchronize ...")

        for data in plans_data:
            code = data.get("code")
            self.stdout.write(f"\tReading data for plan {code} ...")

            if not code or code in seen_codes:
                raise CommandError(f"Missing or duplicate plan code: {code!r}")

            seen_codes.add(code)

            translations = data.get("translations", {})
            missing = required_languages - set(translations)

            if missing:
                raise CommandError(
                    f"Plan '{code}' is missing translations for: "
                    f"{', '.join(sorted(missing))}"
                )

            for language in languages:
                translated = translations[language]

                if not translated.get("name"):
                    raise CommandError(
                        f"Plan '{code}' has no name for '{language}'."
                    )

                if "description" not in translated:
                    raise CommandError(
                        f"Plan '{code}' has no description for '{language}'."
                    )

            try:
                price = Decimal(str(data["monthly_price"]))
                if not price.is_finite() or price < 0:
                    raise InvalidOperation
            except (KeyError, InvalidOperation, ValueError):
                raise CommandError(
                    f"Plan '{code}' has an invalid monthly_price."
                )

            if price.as_tuple().exponent < -2:
                raise CommandError(
                    f"Plan '{code}' price must have at most 2 decimal places."
                )

            if abs(price) >= Decimal("1000000"):
                raise CommandError(
                    f"Plan '{code}' price exceeds the field's limit."
                )

        dry_run = options["dry_run"]
        created_count = 0
        updated_count = 0
        allowance_count = 0

        try:
            with transaction.atomic():
                for data in plans_data:
                    code = data["code"]
                    self.stdout.write(f"Handling plan {code} ...")

                    plan, created = Plan.objects.get_or_create(
                        code=code,
                        defaults={
                            "rank": data.get("rank", 0),
                            "active": data.get("active", True),
                            "monthly_price": data["monthly_price"],
                            "year_months": data["year_months"],
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        plan.rank = data.get("rank", 0)
                        plan.active = data.get("active", True)
                        plan.monthly_price = data["monthly_price"]
                        plan.year_months = data["year_months"]
                        plan.save()

                    # Store each translation in django-parler.
                    for language in languages:
                        translated = data["translations"][language]

                        plan.set_current_language(language)
                        plan.name = translated["name"]
                        plan.description = translated["description"]
                        plan.save()

                    # Synchronize explicitly supplied allowances.
                    # Empty/missing arrays do not delete existing allowances.
                    for item in data.get("allowances", []):
                        try:
                            feature = Feature.objects.get(
                                code=item["feature"]
                            )
                        except Feature.DoesNotExist as exc:
                            raise CommandError(
                                f"Unknown feature '{item['feature']}' "
                                f"in plan '{code}'."
                            ) from exc

                        capability = item["capability"]

                        if (
                            isinstance(capability, bool)
                            or not isinstance(capability, int)
                        ):
                            raise CommandError(
                                f"Capability for feature '{feature.code}' "
                                f"in plan '{code}' must be an integer."
                            )

                        Allowance.objects.update_or_create(
                            plan=plan,
                            feature=feature,
                            defaults={"capability": capability},
                        )
                        allowance_count += 1

                if dry_run:
                    transaction.set_rollback(True)

        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f"Plan synchronization failed: {exc}"
            ) from exc

        action = "Would synchronize" if dry_run else "Synchronized"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {len(plans_data)} plans "
                f"({created_count} created, {updated_count} updated); "
                f"{allowance_count} allowances processed."
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run: all database changes rolled back.")
            )
