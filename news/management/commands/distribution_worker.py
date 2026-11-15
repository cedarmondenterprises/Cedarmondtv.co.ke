"""Independent distribution process. Shares published content, owns its delivery ledger."""
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from news.models import Article

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Audit published article metadata and notify IndexNow of changed URLs.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        key = os.getenv('INDEXNOW_KEY', '')
        if not re.fullmatch(r'[a-zA-Z0-9-]{8,128}', key):
            raise CommandError('Set INDEXNOW_KEY to an 8–128 character verification key.')
        origin = settings.SITE_URL.rstrip('/')
        if urlsplit(origin).scheme != 'https':
            raise CommandError('Distribution requires an HTTPS SITE_URL.')
        database = os.getenv('DISTRIBUTION_STATE', '/app/distribution-state/delivery.sqlite3')
        os.makedirs(os.path.dirname(os.path.abspath(database)), exist_ok=True)
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS delivery (url TEXT PRIMARY KEY, version TEXT NOT NULL, submitted_at REAL NOT NULL)')
            while True:
                try:
                    self.distribute(db, origin, key)
                except Exception:
                    logger.exception('Distribution pass failed; next pass will retry.')
                    if options['once']:
                        raise CommandError('Distribution failed. Inspect the worker logs.')
                if options['once']:
                    break
                time.sleep(300)

    def distribute(self, db, origin, key):
        # Verify the public key before disclosing article URLs to the submission endpoint.
        verification = origin + '/indexnow-key.txt'
        request = Request(verification, headers={'User-Agent': 'CedarmondDistribution/1.0'})
        with urlopen(request, timeout=20) as response:
            if response.read(1024).decode().strip() != key:
                raise CommandError('Public IndexNow verification file does not match.')
        batch = []
        for article in Article.objects.live().iterator(chunk_size=100):
            url = origin + article.get_absolute_url()
            version = hashlib.sha256((article.updated_at.isoformat() + key).encode()).hexdigest()
            previous = db.execute('SELECT version FROM delivery WHERE url = ?', (url,)).fetchone()
            if previous and previous[0] == version:
                continue
            issues = []
            if not (article.seo_description or article.summary).strip():
                issues.append('missing description')
            if not article.display_image:
                issues.append('missing share image')
            if issues:
                self.stdout.write(json.dumps({'url': url, 'seo_issues': issues}))
            batch.append((url, version))
            if len(batch) == 100:
                self.submit(db, origin, verification, key, batch)
                batch = []
        if batch:
            self.submit(db, origin, verification, key, batch)

    def submit(self, db, origin, verification, key, batch):
        payload = json.dumps({
            'host': urlsplit(origin).netloc, 'key': key,
            'keyLocation': verification, 'urlList': [url for url, _ in batch],
        }).encode()
        request = Request('https://api.indexnow.org/indexnow', data=payload, headers={
            'Content-Type': 'application/json', 'User-Agent': 'CedarmondDistribution/1.0',
        })
        with urlopen(request, timeout=30) as response:
            status = response.status
        if status not in (200, 202):
            raise CommandError(f'Unexpected IndexNow response {status}')
        # 202 is pending key verification. Retry next pass until accepted with 200.
        if status == 200:
            with db:
                db.executemany(
                    'INSERT OR REPLACE INTO delivery VALUES (?, ?, ?)',
                    [(url, version, time.time()) for url, version in batch],
                )
        self.stdout.write(json.dumps({'submitted': len(batch), 'http_status': status}))
