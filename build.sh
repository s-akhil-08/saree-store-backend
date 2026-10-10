#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files for WhiteNoise
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate

# Seed demo accounts and initial data (safe/idempotent)
python manage.py setup_demo_accounts
