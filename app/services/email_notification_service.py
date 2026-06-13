from jinja2 import Environment, FileSystemLoader
from app.models import Users
from app.models.price_negotiation import PriceNegotiation
from app.models.escrow import Escrow
from app.schemas.user import UserRead
from app.workers.tasks.email_service_task import send_email_task

from app.core.background import dispatch_task
from app.dependencies.email_service import EmailService

import os

class NotificationService:
    def __init__(self, template_folder: str = None):
        if template_folder is None:
            # Resolve absolute path to dge-tech/template
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_folder = os.path.join(base_dir, 'template')
        self.env = Environment(loader=FileSystemLoader(template_folder))

    def _render_and_dispatch(self, template_name: str, recipient_email: list[str], subject: str, context: dict):
        """Helper to render a template and dispatch the task."""
        try:
            # Inject common context
            context['subject'] = subject

            template = self.env.get_template(template_name)
            html_output = template.render(context)

            service = EmailService()
            dispatch_task(
                send_email_task,
                service.send_email,
                recipient_email, # maps to recipient (celery) or recipients (sync)
                subject,
                html_output
            )
        except Exception as e:
            # Add logging here!
            print(f"Failed to send email: {e}")

    # ─── Onboarding ─────────────────────────────────────────────────────────

    def send_signup_welcome_mail(self, new_user: UserRead):
        subject = "Welcome to the DGE World! You're One of Us Now."
        context = {
            'name': new_user.username,
            'cta_text': "Explore Your Dashboard",
            'cta_link': "https://your-frontend.com/dashboard" # Configure dynamically in the future
        }
        self._render_and_dispatch('welcome.html', [str(new_user.email)], subject, context)

    def send_verification_email(self, new_user: UserRead, token: str):
        subject = "Welcome to DGE World! Please Verify Your Email"
        verification_link = f"https://your-api.com/v1/users/verify-email?token={token}"
        context = {
            'name': new_user.username,
            'cta_link': verification_link
        }
        self._render_and_dispatch('verify_email.html', [str(new_user.email)], subject, context)

    def send_verification_success_email(self, user: UserRead):
        subject = "You're Verified! Welcome to DGE World 🎉"
        context = {
            'name': user.username,
            'cta_text': "Go to Your Dashboard",
            'cta_link': "https://your-frontend.com/dashboard"
        }
        self._render_and_dispatch('welcome.html', [str(user.email)], subject, context)

    # ─── Payments & Wallets ───────────────────────────────────────────────────

    def send_deposit_success_mail(self, user: Users, amount_cents: int, reference: str, date_str: str):
        subject = "Deposit Successful - DGE World"
        context = {
            'name': user.username,
            'amount': f"₦{amount_cents / 100:,.2f}",
            'reference': reference,
            'date': date_str,
            'cta_link': "https://your-frontend.com/dashboard/wallet"
        }
        self._render_and_dispatch('deposit_success.html', [user.email], subject, context)

    def send_withdrawal_status_mail(self, user: Users, status: str, amount_cents: int, bank_name: str, account_number: str, reference: str = None, rejection_reason: str = None):
        amount_str = f"₦{amount_cents / 100:,.2f}"

        if status == "pending":
            subject = "Withdrawal Request Received ⏳"
            context = {
                'name': user.username,
                'amount': amount_str,
                'bank_name': bank_name,
                'account_number': account_number,
                'cta_link': "https://your-frontend.com/dashboard/wallet"
            }
            self._render_and_dispatch('withdrawal_requested.html', [user.email], subject, context)
        else:
            subject = f"Withdrawal {status.capitalize()} - DGE World"
            context = {
                'name': user.username,
                'status': status,
                'amount': amount_str,
                'bank_name': bank_name,
                'account_number': account_number,
                'reference': reference or 'N/A',
                'rejection_reason': rejection_reason,
                'cta_link': "https://your-frontend.com/dashboard/wallet"
            }
            self._render_and_dispatch('withdrawal_processed.html', [user.email], subject, context)

    # ─── Services & Submissions ─────────────────────────────────────────────

    def send_service_purchase_mail(self, buyer: Users, seller: Users, service_title: str, amount_cents: int, order_id: str):
        amount_str = f"₦{amount_cents / 100:,.2f}"

        # To Buyer (Receipt)
        self._render_and_dispatch('service_purchase.html', [buyer.email], "Your Purchase is Confirmed! 🛒", {
            'is_buyer': True,
            'name': buyer.username,
            'other_party': seller.username,
            'service_title': service_title,
            'amount': amount_str,
            'order_id': order_id,
            'cta_link': "https://your-frontend.com/dashboard/orders"
        })

        # To Seller (New Order)
        self._render_and_dispatch('service_purchase.html', [seller.email], "You Have a New Order! 🎉", {
            'is_buyer': False,
            'name': seller.username,
            'other_party': buyer.username,
            'service_title': service_title,
            'amount': amount_str,
            'order_id': order_id,
            'cta_link': "https://your-frontend.com/dashboard/orders"
        })

    def send_project_submitted_mail(self, client: Users, freelancer_name: str, project_name: str, escrow_id: str, submission_date: str):
        subject = "Project Work Submitted for Review 📝"
        context = {
            'name': client.username,
            'freelancer_name': freelancer_name,
            'project_name': project_name,
            'submission_date': submission_date,
            'escrow_id': escrow_id,
            'cta_link': "https://your-frontend.com/dashboard/orders"
        }
        self._render_and_dispatch('project_submitted.html', [client.email], subject, context)

    def send_price_negotiation_offer(self, receiver: Users, initiator: Users, negotiation: PriceNegotiation):
        subject = f"An Opportunity Awaits!🌟 You've Received a New Offer from {initiator.username}"
        amount_formatted = f"₦{negotiation.proposed_price_cents / 100:,.2f}"

        # We don't have the service title directly here, we could add it or just use "Project"
        context = {
            'name': receiver.username,
            'initiator_name': initiator.username,
            'amount': amount_formatted,
            'related_item': "Project Service",
            'cta_link': "https://your-frontend.com/dashboard/negotiations"
        }
        self._render_and_dispatch('negotiation_received.html', [receiver.email], subject, context)

    # ─── Escrow ─────────────────────────────────────────────────────────────

    def send_escrow_creation_debit(self, payer: Users, negotiation):
        subject = "Account Debited by DGE World Escrow Service"
        context = {
            'event_title': "Funds Sent to Escrow",
            'event_type': 'creation_payer',
            'name': payer.username,
            'escrow_id': "See Dashboard", # Don't have ID here in original code
            'amount': f"₦{negotiation.proposed_price_cents / 100:,.2f}",
            'cta_text': "View Transaction Details",
            'cta_link': "https://your-frontend.com/dashboard/escrows"
        }
        self._render_and_dispatch('escrow_event.html', [payer.email], subject, context)

    def send_escrow_release_credit(self, payee: Users, escrow):
        subject = "Escrow Funds Released"
        context = {
            'event_title': "Funds Released to Your Wallet!",
            'event_type': 'release_payee',
            'name': payee.username,
            'escrow_id': str(escrow.id),
            'amount': f"₦{escrow.amount_cents / 100:,.2f}",
            'cta_text': "View Wallet",
            'cta_link': "https://your-frontend.com/dashboard/wallet"
        }
        self._render_and_dispatch('escrow_event.html', [payee.email], subject, context)

    def send_escrow_creation_mail(self, payer: Users, payee: Users, escrow: Escrow):
        subject = "Escrow Creation"

        # Send to Payee
        payee_context = {
            'event_title': "Escrow Creation",
            'event_type': 'creation_payee',
            'name': payee.username,
            'escrow_id': str(escrow.id),
            'cta_text': "View Transaction Details",
            'cta_link': "https://your-frontend.com/dashboard/escrows"
        }
        self._render_and_dispatch('escrow_event.html', [payee.email], subject, payee_context)

        # Send to Payer
        payer_context = {
            'event_title': "Escrow Creation",
            'event_type': 'creation_payer',
            'name': payer.username,
            'escrow_id': str(escrow.id),
            'amount': f"₦{escrow.amount_cents / 100:,.2f}",
            'cta_text': "View Transaction Details",
            'cta_link': "https://your-frontend.com/dashboard/escrows"
        }
        self._render_and_dispatch('escrow_event.html', [payer.email], subject, payer_context)

    def send_escrow_refund_mail(self, payer: Users, escrow: Escrow):
        subject = f"Your Escrow Refund is Complete! (₦{escrow.amount_cents / 100:,.2f})"
        context = {
            'event_title': "Funds Returned!",
            'event_type': 'refund_payer',
            'name': payer.username,
            'escrow_id': str(escrow.id),
            'amount': f"₦{escrow.amount_cents / 100:,.2f}",
            'cta_text': "View Your Wallet",
            'cta_link': "https://your-frontend.com/dashboard/wallet"
        }
        self._render_and_dispatch('escrow_event.html', [payer.email], subject, context)

    def send_escrow_dispute_mail(self, payer: Users, payee: Users, escrow: Escrow):
        subject = f"Action Required: A Dispute Has Been Opened (Escrow ID {escrow.id})"

        # Payer
        self._render_and_dispatch('escrow_event.html', [payer.email], subject, {
            'event_title': "We're Here to Help",
            'event_type': 'dispute_payer',
            'name': payer.username,
            'escrow_id': str(escrow.id),
            'cta_text': "Go to Dispute Center",
            'cta_link': "https://your-frontend.com/dashboard/support"
        })

        # Payee
        self._render_and_dispatch('escrow_event.html', [payee.email], subject, {
            'event_title': "We're Here to Help",
            'event_type': 'dispute_payee',
            'name': payee.username,
            'escrow_id': str(escrow.id),
            'cta_text': "Go to Dispute Center",
            'cta_link': "https://your-frontend.com/dashboard/support"
        })

    # ─── Rides ──────────────────────────────────────────────────────────────

    def send_ride_completed_mail(self, rider: Users, driver: Users, trip):
        # Rider email
        rider_subject = "Your Ride is Complete! 🚗"
        rider_context = {
            'name': rider.username,
            'service_title': "Ride Completed",
            'provider_name': driver.username,
            'price': f"₦{trip.final_fare:,.2f}",
            'cta_link': "https://your-frontend.com/dashboard/rides",
            'message': "Thank you for riding with us. Your fare has been successfully processed."
        }
        self._render_and_dispatch('service_purchase.html', [rider.email], rider_subject, rider_context)

        # Driver email
        driver_subject = "Ride Successfully Completed! 🎉"
        driver_context = {
            'name': driver.username,
            'service_title': "Ride Earnings Added",
            'provider_name': rider.username,
            'price': f"₦{trip.final_fare:,.2f}",
            'cta_link': "https://your-frontend.com/dashboard/driving",
            'message': "Great job! The fare has been credited to your earnings wallet."
        }
        self._render_and_dispatch('service_purchase.html', [driver.email], driver_subject, driver_context)

    def send_ride_cancelled_mail(self, rider: Users, driver: Users, cancelled_by: Users):
        subject = "Ride Request Cancelled"

        # Rider email
        rider_context = {
            'name': rider.username,
            'service_title': "Ride Cancelled",
            'provider_name': driver.username if driver else "Unknown Driver",
            'price': "₦0.00",
            'cta_link': "https://your-frontend.com/dashboard",
            'message': f"Your ride was cancelled by {cancelled_by.username}. No charges were made."
        }
        self._render_and_dispatch('service_purchase.html', [rider.email], subject, rider_context)

        # Driver email (if assigned)
        if driver:
            driver_context = {
                'name': driver.username,
                'service_title': "Ride Cancelled",
                'provider_name': rider.username,
                'price': "₦0.00",
                'cta_link': "https://your-frontend.com/dashboard/driving",
                'message': f"The ride was cancelled by {cancelled_by.username}."
            }
            self._render_and_dispatch('service_purchase.html', [driver.email], subject, driver_context)
