from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile


USERS = [
    dict(username='mechanic1',    password='test1234!', role='mechanic',    elevated=False),
    dict(username='manager1',     password='test1234!', role='manager',     elevated=False),
    dict(username='manager_adv',  password='test1234!', role='manager',     elevated=True),
    dict(username='storekeeper1', password='test1234!', role='storekeeper', elevated=False),
    dict(username='accountant1',  password='test1234!', role='accountant',  elevated=False),
]


class Command(BaseCommand):
    help = 'Create test users for every role (idempotent — safe to run twice)'

    def handle(self, *args, **options):
        for spec in USERS:
            user, created = User.objects.get_or_create(username=spec['username'])
            if created:
                user.set_password(spec['password'])
                user.save()
                self.stdout.write(f'  Created user: {spec["username"]}')
            else:
                self.stdout.write(f'  Exists:       {spec["username"]}')

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = spec['role']
            profile.elevated_access = spec['elevated']
            profile.save()
            tag = f'[{spec["role"]}{"  elevated" if spec["elevated"] else ""}]'
            self.stdout.write(f'    {tag}')

        self.stdout.write(self.style.SUCCESS('\nDone. Passwords: test1234!'))
