#!/usr/bin/env bash
set -o errexit  # Exit on error

echo "Starting deployment..."

# Upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies
pip3 install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --no-input

# Run database migrations
echo "Running migrations..."
python3 manage.py migrate --no-input

# Start Gunicorn server
echo "Starting Gunicorn..."
gunicorn aau_internB.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120
