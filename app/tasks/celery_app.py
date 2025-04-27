from celery import Celery
from app.config.redis import REDIS_URL

celery_app = Celery(
    'tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.tasks.processing_tasks']
)

celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.timezone = 'UTC'

# Ensure results are not ignored
celery_app.conf.update(task_ignore_result=False)
celery_app.conf.update(broker_connection_retry_on_startup=True)

