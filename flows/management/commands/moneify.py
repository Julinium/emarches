import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from flows.models import Currency


class Command(BaseCommand):
    help = 'Imports or updates currencies from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'currencies_json_file', 
            type=str, 
            help='Path to the JSON file containing currencies.'
        )

    def handle(self, *args, **options):

        currencies_file_path = options['currencies_json_file']

        try:
            with open(currencies_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stdout.write('Loaded currencies json file.')
        except Exception as e:
            raise CommandError(f'Failed to read JSON file: {e}')

        try:
            with transaction.atomic():
                # 1. Ensure all relevant Plans exist in the database
                self.stdout.write(f'Handling currencies ...')
                i = 0
                cc = len(data)

                for currency_data in data:
                    i += 1
                    label = currency_data.get('code')
                    self.stdout.write(f'\tWorking on currency: {label}: {i:02d}/{cc:02d}')

                    currency, created = Currency.objects.update_or_create(
                        label = label,
                        defaults = {
                            'symbol': currency_data.get('symbol'),
                            'name': currency_data.get('name'),
                            'value_in_dhs': int(currency_data.get('rate', 0)),
                            'active': bool(currency_data.get('use', 1)),
                            'symbol_first': bool(currency_data.get('symbol_first', 1))
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'\tCurrency to create: {label}.'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'\tCurrency to update: {label}.'))
                self.stdout.write(self.style.SUCCESS(f'===== Done handling Currencies.\n'))

                self.stdout.write('Saving data to database and cleanup ...')

            self.stdout.write(self.style.SUCCESS('Successfully updated currencies.'))

        except Exception as e:
            raise CommandError(f'An error occurred during database update: {e}')