import signal
import threading
from django.conf import settings
from django.core.management import BaseCommand, call_command
class Command(BaseCommand):
    help='Run the persistent Post Office mail queue. Use one worker instance.'
    def handle(self,*args,**options):
        stop=threading.Event()
        signal.signal(signal.SIGTERM,lambda *args:stop.set())
        signal.signal(signal.SIGINT,lambda *args:stop.set())
        while not stop.is_set():
            if settings.NEWSLETTER_ENABLED:
                call_command('send_queued_mail',processes=1,lockfile='/tmp/cedarmond-mail.lock')
            stop.wait(30)
