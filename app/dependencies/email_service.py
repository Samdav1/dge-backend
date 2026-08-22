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
    - Resend API (HTTP / SDK).
    - SMTP (Google / cPanel).
    - HTML and plain text content.
    - File attachments.
    """

    def __init__(self):
        """
        Initializes the service by loading configuration from environment variables.
        """
        from app.config import settings

        self.provider = settings.email_provider.lower()
        sender_name = os.getenv("EMAIL_SENDER_NAME", "DGE World")

        if self.provider == "resend":
            self.config = {
                'provider': 'resend',
                'resend_api_key': settings.resend_api_key or os.getenv("RESEND_API_KEY", ""),
                'sender_name': sender_name,
                'sender_address': settings.email_sender_address_resend or os.getenv("EMAIL_SENDER_ADDRESS_RESEND") or os.getenv("EMAIL_SENDER_ADDRESS", "onboarding@resend.dev"),
            }
        elif self.provider == "cpanel":
            self.config = {
                'provider': 'cpanel',
                'host': settings.email_host_cpanel or os.getenv("EMAIL_HOST", "mail.dgetechs.com"),
                'port': settings.email_port_cpanel,
                'use_ssl': settings.email_use_ssl_cpanel,
                'username': settings.username_cpanel or os.getenv("USERNAME"),
                'password': settings.email_pass_cpanel or os.getenv("EMAIL_PASS"),
                'sender_name': sender_name,
                'sender_address': settings.email_sender_address_cpanel or os.getenv("EMAIL_SENDER_ADDRESS"),
            }
        else: # default to google
            self.config = {
                'provider': 'google',
                'host': settings.email_host_google or os.getenv("EMAIL_HOST", "smtp.gmail.com"),
                'port': settings.email_port_google,
                'use_ssl': settings.email_use_ssl_google,
                'username': settings.username_google or os.getenv("USERNAME"),
                'password': settings.email_pass_google or os.getenv("EMAIL_PASS"),
                'sender_name': sender_name,
                'sender_address': settings.email_sender_address_google or os.getenv("EMAIL_SENDER_ADDRESS"),
            }

        if self.provider == "resend":
            if not self.config['sender_address']:
                raise ValueError("Resend sender_address must be configured in your settings or environment.")
        else:
            if not all([self.config.get('username'), self.config.get('password'), self.config.get('sender_address')]):
                raise ValueError(
                    "SMTP username, password, and sender_address must be set in your configuration or environment.")

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

    def _send_via_resend(
            self, recipients: List[str], subject: str, html_body: str, text_body: Optional[str] = None
    ) -> bool:
        """Sends email using Resend Python SDK or REST API fallback."""
        api_key = self.config.get('resend_api_key', '')
        sender = f"{self.config['sender_name']} <{self.config['sender_address']}>"

        if not api_key:
            print(f"[Resend Simulation] No RESEND_API_KEY configured. Mock sending email to: {', '.join(recipients)}")
            return True

        # Try using resend SDK
        try:
            import resend
            resend.api_key = api_key
            params = {
                "from": sender,
                "to": recipients,
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                params["text"] = text_body
            resp = resend.Emails.send(params)
            print(f"Email sent via Resend SDK to {', '.join(recipients)}: {resp}")
            return True
        except ImportError:
            pass
        except Exception as e:
            print(f"Resend SDK error: {e}, falling back to REST API...")

        # HTTP Fallback
        try:
            import httpx
            payload = {
                "from": sender,
                "to": recipients,
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                payload["text"] = text_body
            res = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10.0
            )
            if res.status_code in (200, 201):
                print(f"Email sent via Resend API to {', '.join(recipients)}")
                return True
            else:
                print(f"Resend API error: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            print(f"Resend REST request failed: {e}")
            return False

    def send_email(
            self,
            recipients: List[str],
            subject: str,
            html_body: str,
            text_body: Optional[str] = None,
            attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Sends the composed email using the configured provider (Resend or SMTP).
        """
        if not recipients:
            print("Error: No recipients provided.")
            return False

        if self.provider == "resend":
            return self._send_via_resend(recipients, subject, html_body, text_body)

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