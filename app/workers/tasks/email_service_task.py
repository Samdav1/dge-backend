from typing import Optional

from app.workers.celery_app import celery_app
from app.dependencies.email_service import EmailService
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@celery_app.task(bind=True, name="tasks.send_email", max_retries=3)
def send_email_task(self, recipient: list[str], subject: str, html_body: str, text_body: Optional[str] = None):
    """
    Background task for sending an email.
    Retries automatically up to 3 times if it fails.
    """
    try:
        service = EmailService()
        result = service.send_email(recipients=recipient, subject=subject, html_body=html_body, text_body=text_body)
        logger.info(f"Email sent successfully to {recipient}")
        return result

    except Exception as exc:
        logger.error(f"Error sending email: {exc}")
        raise self.retry(exc=exc, countdown=10)
