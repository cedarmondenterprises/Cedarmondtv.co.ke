#!/usr/bin/env python3
"""Create a private .env once, with random secrets. Never overwrites an existing file."""
import os
import secrets
from pathlib import Path
root=Path(__file__).resolve().parent.parent
config=(root/'.env.example').read_text()
config=config.replace('SECRET_KEY=\n','SECRET_KEY='+secrets.token_hex(48)+'\n')
config=config.replace('POSTGRES_PASSWORD=\n','POSTGRES_PASSWORD='+secrets.token_hex(32)+'\n')
try:
    descriptor=os.open(root/'.env',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
except FileExistsError:
    raise SystemExit('.env already exists; leaving it unchanged.')
with os.fdopen(descriptor,'w') as handle: handle.write(config)
print('Created .env with random secrets. Set your domain and SMTP details before launch.')
