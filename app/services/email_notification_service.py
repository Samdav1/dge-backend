from jinja2 import Environment, FileSystemLoader
from app.models import Users
from app.models.price_negotiation import PriceNegotiation
from app.models.escrow import Escrow
from app.schemas.user import UserRead
from app.workers.tasks.email_service_task import send_email_task

from app.core.background import dispatch_task
from app.dependencies.email_service import EmailService
from app.config import settings

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
            'cta_link': f"{settings.frontend_url}/dashboard"
        }
        self._render_and_dispatch('welcome.html', [str(new_user.email)], subject, context)

    def send_verification_email(self, new_user: UserRead, token: str):
        subject = "Welcome to DGE World! Please Verify Your Email"
        verification_link = f"{settings.api_url}/v1/users/verify-email?token={token}"
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
            'cta_link': f"{settings.frontend_url}/dashboard"
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
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
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
                'cta_link': f"{settings.frontend_url}/dashboard/wallet"
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
                'cta_link': f"{settings.frontend_url}/dashboard/wallet"
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
            'cta_link': f"{settings.frontend_url}/dashboard/orders"
        })

        # To Seller (New Order)
        self._render_and_dispatch('service_purchase.html', [seller.email], "You Have a New Order! 🎉", {
            'is_buyer': False,
            'name': seller.username,
            'other_party': buyer.username,
            'service_title': service_title,
            'amount': amount_str,
            'order_id': order_id,
            'cta_link': f"{settings.frontend_url}/dashboard/orders"
        })

    def send_project_submitted_mail(self, client: Users, freelancer_name: str, project_name: str, escrow_id: str, submission_date: str):
        subject = "Project Work Submitted for Review 📝"
        context = {
            'name': client.username,
            'freelancer_name': freelancer_name,
            'project_name': project_name,
            'submission_date': submission_date,
            'escrow_id': escrow_id,
            'cta_link': f"{settings.frontend_url}/dashboard/orders"
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
            'cta_link': f"{settings.frontend_url}/dashboard/negotiations"
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
            'cta_link': f"{settings.frontend_url}/dashboard/escrows"
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
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
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
            'cta_link': f"{settings.frontend_url}/dashboard/escrows"
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
            'cta_link': f"{settings.frontend_url}/dashboard/escrows"
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
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
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
            'cta_link': f"{settings.frontend_url}/dashboard/support"
        })

        # Payee
        self._render_and_dispatch('escrow_event.html', [payee.email], subject, {
            'event_title': "We're Here to Help",
            'event_type': 'dispute_payee',
            'name': payee.username,
            'escrow_id': str(escrow.id),
            'cta_text': "Go to Dispute Center",
            'cta_link': f"{settings.frontend_url}/dashboard/support"
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
            'cta_link': f"{settings.frontend_url}/dashboard/rides",
            'message': "Thank you for riding with us. Your fare has been successfully processed."
        }
        self._render_and_dispatch('ride_completed.html', [rider.email], rider_subject, rider_context)

        # Driver email
        driver_subject = "Ride Successfully Completed! 🎉"
        driver_context = {
            'name': driver.username,
            'service_title': "Ride Earnings Added",
            'provider_name': rider.username,
            'price': f"₦{trip.final_fare:,.2f}",
            'cta_link': f"{settings.frontend_url}/dashboard/driving",
            'message': "Great job! The fare has been credited to your earnings wallet."
        }
        self._render_and_dispatch('ride_completed.html', [driver.email], driver_subject, driver_context)

    def send_ride_cancelled_mail(self, rider: Users, driver: Users, cancelled_by: Users):
        subject = "Ride Request Cancelled"

        # Rider email
        rider_context = {
            'name': rider.username,
            'service_title': "Ride Cancelled",
            'provider_name': driver.username if driver else "Unknown Driver",
            'price': "₦0.00",
            'cta_link': f"{settings.frontend_url}/dashboard",
            'message': f"Your ride was cancelled by {cancelled_by.username}. No charges were made."
        }
        self._render_and_dispatch('ride_cancelled.html', [rider.email], subject, rider_context)

        # Driver email (if assigned)
        if driver:
            driver_context = {
                'name': driver.username,
                'service_title': "Ride Cancelled",
                'provider_name': rider.username,
                'price': "₦0.00",
                'cta_link': f"{settings.frontend_url}/dashboard/driving",
                'message': f"The ride was cancelled by {cancelled_by.username}."
            }
            self._render_and_dispatch('ride_cancelled.html', [driver.email], subject, driver_context)

    # ─── Job Board & Service Marketplace ───────────────────────────────────

    def send_job_posted_mail(self, user: Users, job):
        subject = f"Job Posted Successfully: {job.title} 🚀"
        context = {
            'name': user.username,
            'job_title': job.title,
            'price_range': f"${job.min_price_cents / 100:.2f} - ${job.max_price_cents / 100:.2f}",
            'payment_method': (job.payment_method or "platform").capitalize(),
            'cta_link': f"{settings.frontend_url}/dashboard/my-jobs"
        }
        self._render_and_dispatch('job_posted.html', [user.email], subject, context)

    def send_job_application_mail(self, poster: Users, applicant: Users, job, proposed_price_cents: int):
        subject = f"New Bid on Your Job: '{job.title}' 📩"
        context = {
            'poster_name': poster.username,
            'applicant_name': applicant.username,
            'job_title': job.title,
            'proposed_price': f"${proposed_price_cents / 100:.2f}",
            'cta_link': f"{settings.frontend_url}/dashboard/my-jobs"
        }
        self._render_and_dispatch('job_application.html', [poster.email], subject, context)

    def send_kyc_status_mail(self, user: Users, status: str, rejection_reason: str = None):
        if status in ["verified", "approved"]:
            subject = "KYC Verification Approved 🎉 - DGE World"
        else:
            subject = "KYC Verification Status Update - DGE World"

        context = {
            'name': user.username,
            'status': status,
            'rejection_reason': rejection_reason,
            'cta_link': f"{settings.frontend_url}/dashboard/profile"
        }
        self._render_and_dispatch('kyc_status.html', [user.email], subject, context)

    def send_service_status_mail(self, user: Users, service, status: str):
        if status in ["approved", "ACTIVE"]:
            subject = f"Service Approved: '{service.name}' 🎉"
        else:
            subject = f"Service Submitted for Review: '{service.name}' 📋"

        context = {
            'name': user.username,
            'service_name': service.name,
            'status': status,
            'cta_link': f"{settings.frontend_url}/dashboard/marketplace"
        }
        self._render_and_dispatch('service_status.html', [user.email], subject, context)

    def send_job_approved_mail(self, poster: Users, freelancer: Users, job_title: str, price_cents: int):
        subject = f"Your Job Bid Was Accepted: '{job_title}' 🎉"
        amount_formatted = f"₦{price_cents / 100:,.2f}"
        context = {
            'name': freelancer.username,
            'client_name': poster.username,
            'job_title': job_title,
            'amount': amount_formatted,
            'cta_link': f"{settings.frontend_url}/dashboard/my-jobs"
        }
        self._render_and_dispatch('job_accepted.html', [freelancer.email], subject, context)

    def send_negotiation_status_mail(self, target_user: Users, acting_user: Users, negotiation, status: str, proposed_price_cents: int = None):
        subject = f"Negotiation Update: Offer {status.capitalize()} by {acting_user.username}"
        price_val = proposed_price_cents or getattr(negotiation, 'proposed_price_cents', None)
        amount_formatted = f"₦{price_val / 100:,.2f}" if price_val else None

        if status.lower() == "accepted":
            msg = "Your price negotiation offer was accepted! An escrow transaction has been initiated."
        elif status.lower() == "rejected":
            msg = "Your price negotiation offer was declined."
        elif status.lower() == "countered":
            msg = f"{acting_user.username} sent a counter-offer for your negotiation."
        else:
            msg = f"Your price negotiation status has been updated to {status}."

        context = {
            'name': target_user.username,
            'acting_user_name': acting_user.username,
            'status': status,
            'status_display': status.capitalize(),
            'amount': amount_formatted,
            'message': msg,
            'cta_link': f"{settings.frontend_url}/dashboard/negotiations"
        }
        self._render_and_dispatch('negotiation_status.html', [target_user.email], subject, context)


