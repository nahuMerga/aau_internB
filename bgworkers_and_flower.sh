#!/bin/bash

# Start Celery worker in the background
celery -A aau_internB worker -Q internships,students,advisors,celery -l info --concurrency=4 &

# Start Flower in the foreground (so the process doesn't exit)
celery -A aau_internB flower --port=$PORT