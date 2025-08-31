# aau_internB/celery.py
import os
import ssl
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aau_internB.settings")

app = Celery("aau_internB")

# Get Redis URL from .env
redis_url = os.getenv("REDIS_URL")

# Base Celery config
app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
)

# Attach SSL config if using rediss://
if redis_url and redis_url.startswith("rediss://"):
    ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE}  # Upstash works with CERT_NONE
    app.conf.broker_use_ssl = ssl_config
    app.conf.redis_backend_use_ssl = ssl_config

# Discover tasks
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
