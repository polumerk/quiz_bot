#!/usr/bin/env python3
"""
Debug script to check Replit environment variables
Run this on Replit to see what environment variables are available
"""

import os

print("🔍 Replit Environment Debug")
print("=" * 50)

# All environment variables that might be related to Replit
replit_vars = [
    'REPLIT_URL',
    'REPLIT_DEV_DOMAIN',
    'REPL_SLUG', 
    'REPL_OWNER',
    'REPL_ID',
    'REPLIT_DB_URL',
    'HOSTNAME',
    'HOST',
    'PORT',
]

print("📋 Replit-related environment variables:")
for var in replit_vars:
    value = os.getenv(var)
    if value:
        print(f"  ✅ {var}: {value}")
    else:
        print(f"  ❌ {var}: Not set")

print("\n🌐 Common URL patterns:")
print(f"  hostname: {os.getenv('HOSTNAME', 'not set')}")

# Try to construct possible URLs
slug = os.getenv('REPL_SLUG')
owner = os.getenv('REPL_OWNER')
replit_url = os.getenv('REPLIT_URL')
dev_domain = os.getenv('REPLIT_DEV_DOMAIN')

print("\n🔗 Possible webhook URLs:")
if replit_url:
    print(f"  REPLIT_URL: https://{replit_url}")
if dev_domain:
    print(f"  DEV_DOMAIN: https://{dev_domain}")
if slug and owner:
    print(f"  Legacy format: https://{slug}.{owner}.repl.co")

print(f"\n💡 Environment count: {len([k for k in os.environ.keys() if 'REPL' in k.upper()])} Replit variables found")

# Check if we can determine the correct URL
from src.config import config

print(f"\n🤖 Bot config results:")
print(f"  Is Replit detected: {config.is_replit_environment()}")
print(f"  Webhook URL: {config.get_replit_webhook_url()}")

print("\n" + "=" * 50)
print("Copy this output and share if you need help debugging!")