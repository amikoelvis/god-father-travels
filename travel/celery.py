import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_root.settings')

app = Celery('project_root')

# Read Celery config from Django settings, using CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Optional: periodic tasks
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Example of periodic tasks:
    - Pre-warm cache for featured safaris and popular vehicles every hour
    """
    # Run warm_featured_cache every hour
    sender.add_periodic_task(
        crontab(minute=0, hour='*'),
        'api.tasks.warm_featured_cache',
        name='Pre-warm cache hourly'
    )


# For debugging, define a simple test task
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
