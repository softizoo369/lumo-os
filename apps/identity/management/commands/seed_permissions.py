from django.core.management.base import BaseCommand
from apps.identity.models import Feature, Permission

class Command(BaseCommand):
    help = 'Seeds the global features and atomic permissions into the database.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting Permission Seeding Process...'))

        # The Master Registry Definition
        REGISTRY = [
            {
                'code': 'company', 'name': 'Company Profile',
                'permissions': [
                    {'code': 'company.read', 'name': 'View Company Details'},
                    {'code': 'company.update', 'name': 'Edit Company Details'},
                ]
            },
            {
                'code': 'team', 'name': 'Users & Team',
                'permissions': [
                    {'code': 'team.create', 'name': 'Invite Team Members'},
                    {'code': 'team.read', 'name': 'View Team List'},
                    {'code': 'team.update', 'name': 'Edit Team Roles'},
                    {'code': 'team.delete', 'name': 'Remove Team Members'},
                ]
            },
            {
                'code': 'role', 'name': 'Roles & Permissions',
                'permissions': [
                    {'code': 'role.create', 'name': 'Create Custom Roles'},
                    {'code': 'role.read', 'name': 'View Roles Matrix'},
                    {'code': 'role.update', 'name': 'Update Role Permissions'},
                    {'code': 'role.delete', 'name': 'Delete Roles'},
                ]
            },
            {
                'code': 'billing', 'name': 'Billing & Subscription',
                'permissions': [
                    {'code': 'billing.read', 'name': 'View Billing & Invoices'},
                    {'code': 'billing.update', 'name': 'Manage Plans & Payments'},
                ]
            }
        ]

        features_created = 0
        perms_created = 0

        for module in REGISTRY:
            feature, created = Feature.objects.get_or_create(
                code=module['code'],
                defaults={'name': module['name']}
            )
            if created: features_created += 1

            for perm in module['permissions']:
                _, p_created = Permission.objects.get_or_create(
                    code=perm['code'],
                    defaults={'name': perm['name'], 'feature': feature}
                )
                if p_created: perms_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {features_created} Features and {perms_created} Permissions!'
        ))