import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()


class EmailService:
    """
    An advanced email service for sending transactional emails.

    This service supports:
    - HTML and plain text content.
    - File attachments.
    - Secure connection via SMTP_SSL or STARTTLS.
    - Configuration via environment variables for easy deployment.
    """

    def __init__(self):
        """
        Initializes the service by loading configuration from environment variables.
        """
        self.config = {
            'host': os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            'port': int(os.getenv("EMAIL_PORT", 465)),
            'use_ssl': os.getenv("EMAIL_USE_SSL", "false").lower() == "true",
            'username': os.getenv("USERNAME"),
            'password': os.getenv("EMAIL_PASS"),
            'sender_name': os.getenv("EMAIL_SENDER_NAME", "Your App"),
            'sender_address': os.getenv("EMAIL_SENDER_ADDRESS"),
        }

        if not all([self.config['username'], self.config['password'], self.config['sender_address']]):
            raise ValueError(
                "EMAIL_USERNAME, EMAIL_PASSWORD, and EMAIL_SENDER_ADDRESS must be set in your environment.")

    def _create_message(
            self, recipients: List[str], subject: str, html_body: str,
            text_body: Optional[str] = None, attachments: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """
        Constructs the email message object.
        """
        msg_root = MIMEMultipart('mixed')
        msg_root['Subject'] = subject
        msg_root['From'] = f"{self.config['sender_name']} <{self.config['sender_address']}>"
        msg_root['To'] = ", ".join(recipients)

        msg_alternative = MIMEMultipart('alternative')

        if text_body:
            msg_alternative.attach(MIMEText(text_body, 'plain', 'utf-8'))

        msg_alternative.attach(MIMEText(html_body, 'html', 'utf-8'))

        msg_root.attach(msg_alternative)

        if attachments:
            for file_path_str in attachments:
                file_path = Path(file_path_str)
                if not file_path.is_file():
                    print(f"Warning: Attachment not found at {file_path}, skipping.")
                    continue

                with open(file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={file_path.name}',
                )
                msg_root.attach(part)

        return msg_root

    def send_email(
            self,
            recipients: List[str],
            subject: str,
            html_body: str,
            text_body: Optional[str] = None,
            attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Connects to the SMTP server and sends the composed email.

        Args:
            recipients: A list of email addresses to send to.
            subject: The subject of the email.
            html_body: The HTML content of the email.
            text_body: A plain text version of the email for compatibility.
            attachments: A list of string paths to files to attach.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not recipients:
            print("Error: No recipients provided.")
            return False

        try:
            message = self._create_message(recipients, subject, html_body, text_body, attachments)

            if self.config['use_ssl']:
                context = smtplib.ssl.create_default_context()
                conn_class = smtplib.SMTP_SSL
                conn_args = {'host': self.config['host'], 'port': self.config['port'], 'context': context}
            else:
                conn_class = smtplib.SMTP
                conn_args = {'host': self.config['host'], 'port': self.config['port']}

            with conn_class(**conn_args) as server:
                if not self.config['use_ssl']:
                    server.starttls()

                server.login(self.config['username'], self.config['password'])
                server.send_message(message)
                print(f"Email sent successfully to: {', '.join(recipients)}")
                return True

        except smtplib.SMTPException as e:
            print(f"Failed to send email. SMTP Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return False