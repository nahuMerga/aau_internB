# aau_internB/celery.py
import os
import ssl
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aau_internB.settings')

app = Celery('aau_internB')

# Core Celery configuration
app.conf.update(
    broker_url=os.getenv("REDIS_URL"),       # e.g. rediss://...
    result_backend=os.getenv("REDIS_URL"),   # e.g. rediss://...

    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',

    # --- SSL configs for Upstash Redis ---
    broker_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,  # disable cert validation (Upstash allows)
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
)

# Load task modules from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
