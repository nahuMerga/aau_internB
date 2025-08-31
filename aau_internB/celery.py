import os
import ssl
from celery import Celery
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aau_internB.settings')

app = Celery('aau_internB')

redis_url = os.getenv("REDIS_URL")

app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,

    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',
)

# Add SSL only if using rediss://
if redis_url.startswith("rediss://"):
    ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE}  # or CERT_REQUIRED if you want real validation
    app.conf.broker_use_ssl = ssl_config
    app.conf.redis_backend_use_ssl = ssl_config

app.autodiscover_tasks()
