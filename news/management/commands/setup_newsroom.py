from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from news.models import Category
class Command(BaseCommand):
    help = 'Create newsroom roles and sections; no accounts or passwords are created.'
    def handle(self,*args,**options):
        for index,name in enumerate(['Kenya','Politics','Counties','Business','Technology','Culture','Sports','Opinion']):
            Category.objects.get_or_create(slug=name.lower(),defaults={'name':name,'position':index})
        reporter,_ = Group.objects.get_or_create(name='Reporter')
        editor,_ = Group.objects.get_or_create(name='Editor')
        reporter.permissions.set(Permission.objects.filter(content_type__app_label='news',codename__in=['add_article','view_article','change_article','view_category','view_author','view_tag']))
        editor.permissions.set(Permission.objects.filter(content_type__app_label='news').exclude(content_type__model='subscription'))
        self.stdout.write(self.style.SUCCESS('Newsroom roles and sections ready. Grant staff status and assign groups in admin.'))
