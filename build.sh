#!/usr/bin/env bash

set -o errexit  # Exit on error

# Log the deployment start
echo "Starting deployment..."

# Upgrade pip
python3 -m pip install --upgrade pip

# Install required dependencies from requirements.txt
pip3 install -r requirements.txt

# Run database migrations (important step for Django setup)
python3 manage.py migrate --no-input

# Collect static files (necessary for serving static content in production)
python3 manage.py collectstatic --no-input

# Start the Gunicorn server
echo "Starting Gunicorn server..."
gunicorn aau_internB.wsgi:application --bind 0.0.0.0:$PORT

