"""Set up default groups and permissions"""

from django.core.management.base import BaseCommand, CommandError  
from django.contrib.auth.models import User, Group, Permission
from wld.dictionary.models import Entry

advanced_search = Permission.objects.get(codename='search_gloss', content_type__model__exact='gloss')

class Command(BaseCommand):

    help = 'set up default groups and permissions'
    args = ''

    def handle(self, *args, **options):

        # Publisher
        publisher, created = Group.objects.get_or_create(name='Publisher')
        publisher.permissions.add(advanced_search)

        # Editor
        editor, created = Group.objects.get_or_create(name='Editor')
        editor.permissions.add(advanced_search)

        # Interpreter
        interpreter, created = Group.objects.get_or_create(name='Interpreter')
        interpreter.permissions.add(advanced_search)

        # Interpreter Supervisor
        supervisor, created = Group.objects.get_or_create(name='Interpreter Supervisor')
        supervisor.permissions.add(advanced_search)

        # Researcher
        researcher, created = Group.objects.get_or_create(name='Researcher')
        researcher.permissions.add(advanced_search)

        # Public
        public, created = Group.objects.get_or_create(name='Public')

        # create sample users if we don't have them already
        if len(User.objects.filter(username='publisher')) == 0:

            # create some sample users            
            erwin = User.objects.create_user('publisher', 'example@example.com', 'publisher', first_name='Erwin', last_name='Publisher')
            public = User.objects.create_user('public', 'example@example.com', 'public', first_name='Pamela', last_name='Public')

            erwin.groups.add(publisher)