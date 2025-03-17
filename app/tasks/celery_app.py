from celery import Celery

celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',    # Use the Docker service name "redis"
    backend='redis://redis:6379/0',
    include=['app.tasks.processing_tasks']
)

celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.timezone = 'UTC'

# Ensure results are not ignored
celery_app.conf.update(task_ignore_result=False)
celery_app.conf.update(broker_connection_retry_on_startup=True)

