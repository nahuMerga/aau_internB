# aau_internB/celery.py
import os
import ssl
from celery import Celery
from dotenv import load_dotenv

# Load environment variables (optional if using Render env vars)
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aau_internB.settings')

app = Celery('aau_internB')

# SSL options for Upstash Redis
ssl_opts = {'ssl_cert_reqs': ssl.CERT_NONE}

app.conf.update(
    broker_url=os.getenv("REDIS_URL"),
    result_backend=os.getenv("REDIS_URL"),
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',
    broker_use_ssl=ssl_opts,
    result_backend_transport_options=ssl_opts,
)

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
