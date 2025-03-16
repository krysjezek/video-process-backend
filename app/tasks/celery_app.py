# app/tasks/celery_app.py

from celery import Celery

celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # Adjust if necessary.
    backend='redis://localhost:6379/0',
    include=['app.tasks.processing_tasks']  # Explicitly include your tasks module.
)

celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.timezone = 'UTC'


# Autodiscover tasks from the 'app.workers' package.
celery_app.autodiscover_tasks(['app.tasks'])

