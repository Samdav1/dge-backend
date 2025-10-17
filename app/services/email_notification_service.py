from jinja2 import Environment, FileSystemLoader
from app.models import Users
from app.models.price_negotiation import PriceNegotiation
from app.models.escrow import Escrow
from app.schemas.user import UserRead
from app.workers.tasks.email_service_task import send_email_task


class NotificationService:
    def __init__(self, template_folder: str = '../template'):
        self.env = Environment(loader=FileSystemLoader(template_folder))

    def _render_and_dispatch(self, template_name: str, recipient_email: list[str], subject: str, context: dict):
        """Helper to render a template and dispatch the Celery task."""
        try:
            template = self.env.get_template(template_name)
            html_output = template.render(context)

            send_email_task.delay(
                recipient=recipient_email,
                subject=subject,
                html_body=html_output
            )
        except Exception as e:
            # Add logging here!
            print(f"Failed to send email: {e}")

    def send_escrow_creation_debit(self, payer: Users, negotiation):
        """Sends the "you paid" email to the payer."""

        subject = "Account Debited by DGE World Escrow Service"

        email_context = {
            'title': "Some Funds Have Left Your Account",
            'name': payer.username,
            'body': f"Just a quick confirmation! Your escrow payment for ${negotiation.proposed_price_cents / 100:.2f} has been successfully sent from your wallet. The funds are on their way!",
            'cta_text': "View Transaction Details",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payer.email],
            subject=subject,
            context=email_context
        )

    def send_escrow_release_credit(self, payee: Users, escrow):
        """Sends the "you got paid" email to the payee."""

        subject = "Escrow Funds Released"

        email_context = {
            'title': "Funds Released to Your Wallet!",
            'name': payee.username,
            'body': f"Great news! The escrow payment for ${escrow.amount_cents / 100:.2f} has been successfully released and deposited into your wallet.",
            'cta_text': "View Wallet",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payee.email, payee.email],
            subject=subject,
            context=email_context
        )

    def send_escrow_creation_mail(self, payer: Users, payee: Users, escrow: Escrow):
        """Sends the confirmation for escrow creation for both parties"""

        subject = "Escrow Creation"

        email_context = {
            'title': "Escrow Creation",
            'name': payee.username,
            'body': f"This is a confirmation email for your current active escrow service. Escrow ID {escrow.id} ",
            'cta_text': "View Transaction Details",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payee.email, payer.email],
            subject=subject,
            context=email_context
        )

    def send_escrow_refund_mail(self, payer: Users, escrow: Escrow):
        """
        Sends a confirmation email to the PAYER when an escrow is refunded.
        """

        subject = f"Your Escrow Refund is Complete! (${escrow.amount_cents / 100:.2f})"
        amount_formatted = f"${escrow.amount_cents / 100:.2f}"

        email_context = {
            'title': "Funds Returned!",
            'name': payer.username,
            'body': (
                f"<p>We've successfully processed your refund of <strong>{amount_formatted}</strong> for Escrow ID {escrow.id}. The funds are now back in your wallet.</p>"
                "<p>We believe in a fair and transparent community, and we're here to ensure every interaction feels secure. While this one didn't work out, we're ready for your next connection!</p>"
            ),
            'cta_text': "View Your Wallet",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payer.email],
            subject=subject,
            context=email_context
        )

    def send_escrow_dispute_mail(self, payer: Users, payee: Users, escrow: Escrow):
        """
        Notifies BOTH parties that an escrow has been moved into dispute.
        """

        subject = f"Action Required: A Dispute Has Been Opened (Escrow ID {escrow.id})"

        payer_context = {
            'title': "We're Here to Help",
            'name': payer.username,
            'body': (
                f"<p>We've received a dispute request for Escrow ID {escrow.id}. Don't worry, your funds are held securely while our team reviews the situation.</p>"
                "<p>Our goal is always a fair outcome. We see this not as a conflict, but as a chance to find clarity together. Please provide any details that can help us understand your side of the story.</p>"
            ),
            'cta_text': "Go to Dispute Center",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payer.email],
            subject=subject,
            context=payer_context
        )

        payee_context = {
            'title': "We're Here to Help",
            'name': payee.username,
            'body': (
                f"<p>A dispute has been opened by the other party for Escrow ID {escrow.id}. Your pending payment is held securely while our team reviews the situation.</p>"
                "<p>Our goal is always a fair outcome. We see this not as a conflict, but as a chance to find clarity together. Please provide any details that can help us understand your side of the story.</p>"
            ),
            'cta_text': "Go to Dispute Center",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[payee.email],
            subject=subject,
            context=payee_context
        )

    def send_signup_welcome_mail(self, new_user: UserRead):
        """
        Sends a warm welcome email to a new user upon signup.
        (I renamed this from 'send_signup_creation_mail' for clarity
         and fixed the arguments, as it doesn't need escrow info)
        """

        subject = "Welcome to the DGE World! You're One of Us Now."

        email_context = {
            'title': f"Welcome, {new_user.username}!",
            'name': new_user.username,
            'body': (
                "<p>You've officially joined a community where every connection matters. We're not just building a platform; we're building a world centered on trust, unity, and unique experiences.</p>"
                "<p>This is where your ideas meet opportunity, and where every interaction is protected. We're so excited to see what you'll achieve.</p>"
                "<p>Ready to make your first move?</p>"
            ),
            'cta_text': "Explore Your Dashboard",
            'cta_link': "#"
        }

        self._render_and_dispatch(
            template_name='email_template.html',
            recipient_email=[str(new_user.email)],
            subject=subject,
            context=email_context
        )