from celery import Celery

celery_app = Celery(
    "dge task",
    broker="amqp://guest:guest@localhost:5672",
    backend="redis://localhost:6379/0",
    include=["app.workers.tasks.email_service_task"],

)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)