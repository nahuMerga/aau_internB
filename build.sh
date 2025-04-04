#!/usr/bin/env bash

set -o errexit

echo "🚀 Starting deployment..."

# Use python3 & pip3
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt

# Migrate and collectstatic
python3 manage.py migrate --no-input
python3 manage.py collectstatic --no-input
