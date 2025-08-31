web: gunicorn aau_internB.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A aau_internB worker -Q internships,students,advisors,celery -l info --pool=solo
