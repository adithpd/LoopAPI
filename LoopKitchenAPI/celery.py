import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE', 
    'LoopKitchenAPI.settings'
)

app = Celery('LoopKitchenAPI')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Executes every day at  12:30 pm.
    'run-every-hour': {
        'task': 'Apps.TaskForMe.tasks.StorePoll',
        'schedule': crontab(minute=0, hour='*/1'),
    },
}

app.set_default()