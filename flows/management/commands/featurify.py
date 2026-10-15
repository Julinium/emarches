import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from flows.models import Category, Feature, Plan, Allowance


class Command(BaseCommand):
    help = 'Imports or updates categories, features, and plan allowances from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'features_json_file', 
            type=str, 
            help='Path to the JSON file containing categories and features.'
        )

    def handle(self, *args, **options):

        features_file_path = options['features_json_file']

        try:
            with open(features_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stdout.write('Loaded features json file.')
                self.stdout.write(self.style.WARNING(f'Database operation is atomic: All success or no changes.'))
        except Exception as e:
            raise CommandError(f'Failed to read JSON file: {e}')

        # Map JSON plan keys to your Plan model identifiers
        # Adjust the plan name/lookup field based on your Plan model definition
        plan_mapping = {
            'plan_free': 'Free',
            'plan_startup': 'Startup',
            'plan_pro': 'Pro',
        }

        try:
            with transaction.atomic():
                # 1. Ensure all relevant Plans exist in the database
                self.stdout.write(f'Handling plan records ...')
                plans = {}
                for json_key, plan_code in plan_mapping.items():
                    self.stdout.write(f'\tWorking on plan {plan_code}')
                    plan, created = Plan.objects.get_or_create(
                        code=plan_code,  # Change to code/slug if your Plan model uses that
                        defaults={'name': plan_code.capitalize()}
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'\tPlan to create: {plan_code}.'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'\tPlan to update: {plan_code}.'))
                    plans[json_key] = plan
                
                self.stdout.write(f'===== Handled plans: {len(plans)}.\n')

                # 2. Iterate through categories and nested features
                self.stdout.write(f'Handling Category records ...')
                i = 0
                cc = len(data)
                for cat_data in data:
                    i += 1
                    name = cat_data.get('category')
                    self.stdout.write(f'\tWorking on category: {name}: {i:02d}/{cc:02d}')
                    category, created = Category.objects.update_or_create(
                        code=cat_data['code'],
                        defaults={
                            'name': name,
                            'active': bool(cat_data.get('active', 1)),
                            'rank': int(cat_data.get('rank', 0)),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'\tCategory to create: {name}.'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'\tCategory to update: {name}.'))

                    j = 0
                    for feat_data in cat_data.get('features', []):
                        j += 1
                        kind = feat_data.get('kind', 'integer')
                        code = feat_data['code']
                        self.stdout.write(f'\t\tWorking on Feature {j}: {code}')
                        feature, created = Feature.objects.update_or_create(
                            code=code,
                            defaults={
                                'active': bool(feat_data.get('active', 1)),
                                'name': feat_data.get('name'),
                                'description': feat_data.get('description', ''),
                                'is_binary': True if kind == "binary" else False,
                                'category': category,
                            }
                        )
                        if created:
                            self.stdout.write(self.style.SUCCESS(f'\t\tFeature to create: {code}.'))
                        else:
                            self.stdout.write(self.style.SUCCESS(f'\t\tFeature to update: {code}.'))
                        
                        # 3. Update/Create Allowances for each plan capability
                        self.stdout.write(f'\t\tHandling Plans and Features relationships ...')
                        for json_key, plan_obj in plans.items():
                            capability = feat_data.get(json_key)
                            if capability is not None:
                                Allowance.objects.update_or_create(
                                    plan=plan_obj,
                                    feature=feature,
                                    defaults={'capability': capability}
                                )
                        self.stdout.write(self.style.SUCCESS(f'\t\t=== Done binding Feature to Plans: {feature.code}.\n'))
                    self.stdout.write(self.style.SUCCESS(f'\t==== Done handling Features.\n'))
                self.stdout.write(self.style.SUCCESS(f'===== Done handling Categories.\n'))

                self.stdout.write('Saving data to database and cleanup ...')

            self.stdout.write(self.style.SUCCESS('Successfully updated categories, features, and allowances!'))

        except Exception as e:
            raise CommandError(f'An error occurred during database update: {e}')