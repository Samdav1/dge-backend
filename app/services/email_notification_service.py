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

    def send_verification_email(self, new_user, token: str):
        subject = "Welcome to DGE World! Please Verify Your Email"
        api_base = settings.api_url.rstrip("/") if settings.api_url else "https://dge.dgetechs.com"
        verification_link = f"{api_base}/v1/users/verify-email?token={token}"
        email = getattr(new_user, 'email', None)
        if not email:
            print("Cannot send verification email: missing user email")
            return

        context = {
            'name': getattr(new_user, 'username', 'Valued User'),
            'cta_link': verification_link
        }
        self._render_and_dispatch('verify_email.html', [str(email)], subject, context)

    def send_verification_success_email(self, user):
        subject = "You're Verified! Welcome to DGE World 🎉"
        email = getattr(user, 'email', None)
        if not email:
            print("Cannot send verification success email: missing user email")
            return

        frontend_base = settings.frontend_url.rstrip("/") if settings.frontend_url else "https://dgespace.com"
        context = {
            'name': getattr(user, 'username', 'Valued User'),
            'cta_link': f"{frontend_base}/dashboard"
        }
        self._render_and_dispatch('welcome.html', [str(email)], subject, context)

    def send_password_reset_mail(self, user, token: str):
        subject = "Reset Your DGE World Password 🔐"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        context = {
            'name': username,
            'cta_link': reset_link
        }
        self._render_and_dispatch('password_reset.html', [str(email)], subject, context)

    def send_password_changed_mail(self, user):
        from datetime import datetime, timezone
        subject = "Security Alert: Password Changed Successfully 🛡️"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        context = {
            'name': username,
            'email': email,
            'date_time': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            'cta_link': f"{settings.frontend_url}/dashboard"
        }
        self._render_and_dispatch('password_changed.html', [str(email)], subject, context)

    def send_profile_updated_mail(self, user, first_name: str = None, last_name: str = None, phone: str = None, country: str = None):
        from datetime import datetime, timezone
        subject = "Your DGE World Profile Was Updated 👤"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        context = {
            'name': username,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'country': country,
            'updated_at': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            'cta_link': f"{settings.frontend_url}/dashboard/profile"
        }
        self._render_and_dispatch('profile_updated.html', [str(email)], subject, context)

    def send_portfolio_updated_mail(self, user, portfolio_title: str):
        subject = f"Portfolio Updated: '{portfolio_title}' 🎨"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        context = {
            'name': username,
            'portfolio_title': portfolio_title,
            'cta_link': f"{settings.frontend_url}/dashboard/portfolio"
        }
        self._render_and_dispatch('portfolio_updated.html', [str(email)], subject, context)

    # ─── Payments & Wallets ───────────────────────────────────────────────────

    def send_deposit_success_mail(self, user, amount_cents: int, reference: str, date_str: str = None):
        from datetime import datetime, timezone
        subject = "Deposit Successful - DGE World"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        formatted_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        context = {
            'name': username,
            'amount': f"₦{amount_cents / 100:,.2f}",
            'reference': reference,
            'date': formatted_date,
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        }
        self._render_and_dispatch('deposit_success.html', [str(email)], subject, context)

    def send_wallet_credit_mail(self, user, amount_cents: int, reference: str, description: str = None, date_str: str = None):
        from datetime import datetime, timezone
        subject = f"Wallet Credited (+₦{amount_cents / 100:,.2f}) - DGE World 💰"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        formatted_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        context = {
            'name': username,
            'amount': f"₦{amount_cents / 100:,.2f}",
            'reference': reference,
            'description': description or "Wallet Credit Transaction",
            'date': formatted_date,
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        }
        self._render_and_dispatch('wallet_credit.html', [str(email)], subject, context)

    def send_wallet_debit_mail(self, user, amount_cents: int, reference: str, description: str = None, date_str: str = None):
        from datetime import datetime, timezone
        subject = f"Wallet Debited (-₦{amount_cents / 100:,.2f}) - DGE World 💳"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        formatted_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        context = {
            'name': username,
            'amount': f"₦{amount_cents / 100:,.2f}",
            'reference': reference,
            'description': description or "Wallet Debit Transaction",
            'date': formatted_date,
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        }
        self._render_and_dispatch('wallet_debit.html', [str(email)], subject, context)

    def send_transaction_status_mail(
        self, user, status: str, amount_cents: int, reference: str, 
        transaction_type: str = "Wallet Transaction", description: str = None, 
        failure_reason: str = None, date_str: str = None
    ):
        from datetime import datetime, timezone
        status_clean = status.lower().strip()
        status_title = status_clean.capitalize()
        subject = f"Transaction Update ({status_title}): {reference}"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        formatted_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        if status_clean in ["successful", "completed", "approved"]:
            msg = f"Your {transaction_type.lower()} of ₦{amount_cents / 100:,.2f} was successfully completed."
        elif status_clean in ["failed", "rejected", "declined"]:
            msg = f"Your {transaction_type.lower()} of ₦{amount_cents / 100:,.2f} failed or was declined."
        else:
            msg = f"Your {transaction_type.lower()} of ₦{amount_cents / 100:,.2f} is currently pending processing."

        context = {
            'name': username,
            'status_key': status_clean,
            'status_display': status_title,
            'transaction_type': transaction_type,
            'amount': f"₦{amount_cents / 100:,.2f}",
            'reference': reference,
            'message': description or msg,
            'failure_reason': failure_reason,
            'date': formatted_date,
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        }
        self._render_and_dispatch('transaction_status.html', [str(email)], subject, context)

    def send_withdrawal_status_mail(self, user, status: str, amount_cents: int, bank_name: str, account_number: str, reference: str = None, rejection_reason: str = None):
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        amount_str = f"₦{amount_cents / 100:,.2f}"

        if status.lower() == "pending":
            subject = "Withdrawal Request Received ⏳"
            context = {
                'name': username,
                'amount': amount_str,
                'bank_name': bank_name,
                'account_number': account_number,
                'cta_link': f"{settings.frontend_url}/dashboard/wallet"
            }
            self._render_and_dispatch('withdrawal_requested.html', [str(email)], subject, context)
        else:
            subject = f"Withdrawal {status.capitalize()} - DGE World"
            context = {
                'name': username,
                'status': status.lower(),
                'amount': amount_str,
                'bank_name': bank_name,
                'account_number': account_number,
                'reference': reference or 'N/A',
                'rejection_reason': rejection_reason,
                'cta_link': f"{settings.frontend_url}/dashboard/wallet"
            }
            self._render_and_dispatch('withdrawal_processed.html', [str(email)], subject, context)


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

    def send_escrow_release_credit(self, payee: Users, escrow, payer: Users = None, is_dispute_resolution: bool = False):
        amount_str = f"₦{escrow.amount_cents / 100:,.2f}"
        
        # Send to Payee
        payee_event = 'dispute_resolved_release_payee' if is_dispute_resolution else 'release_payee'
        payee_title = "Dispute Resolved: Escrow Funds Released!" if is_dispute_resolution else "Escrow Funds Released"
        self._render_and_dispatch('escrow_event.html', [payee.email], payee_title, {
            'event_title': payee_title,
            'event_type': payee_event,
            'name': payee.username,
            'escrow_id': str(escrow.id),
            'amount': amount_str,
            'cta_text': "View Wallet",
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        })

        # Send to Payer if provided
        if payer and hasattr(payer, 'email') and payer.email:
            payer_event = 'dispute_resolved_release_payer' if is_dispute_resolution else 'release_payer'
            payer_title = "Dispute Resolved: Escrow Payment Released" if is_dispute_resolution else "Escrow Payment Released"
            self._render_and_dispatch('escrow_event.html', [payer.email], payer_title, {
                'event_title': payer_title,
                'event_type': payer_event,
                'name': payer.username,
                'escrow_id': str(escrow.id),
                'amount': amount_str,
                'cta_text': "View Escrow Details",
                'cta_link': f"{settings.frontend_url}/dashboard/escrows"
            })

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

    def send_escrow_refund_mail(self, payer: Users, escrow: Escrow, payee: Users = None, is_dispute_resolution: bool = False):
        amount_str = f"₦{escrow.amount_cents / 100:,.2f}"

        # Send to Payer
        payer_event = 'dispute_resolved_refund_payer' if is_dispute_resolution else 'refund_payer'
        payer_title = "Dispute Resolved: Escrow Refunded" if is_dispute_resolution else f"Your Escrow Refund is Complete! ({amount_str})"
        self._render_and_dispatch('escrow_event.html', [payer.email], payer_title, {
            'event_title': payer_title,
            'event_type': payer_event,
            'name': payer.username,
            'escrow_id': str(escrow.id),
            'amount': amount_str,
            'cta_text': "View Your Wallet",
            'cta_link': f"{settings.frontend_url}/dashboard/wallet"
        })

        # Send to Payee if provided
        if payee and hasattr(payee, 'email') and payee.email:
            payee_event = 'dispute_resolved_refund_payee' if is_dispute_resolution else 'refund_payee'
            payee_title = "Dispute Resolved: Escrow Refunded to Client" if is_dispute_resolution else "Escrow Refunded to Client"
            self._render_and_dispatch('escrow_event.html', [payee.email], payee_title, {
                'event_title': payee_title,
                'event_type': payee_event,
                'name': payee.username,
                'escrow_id': str(escrow.id),
                'amount': amount_str,
                'cta_text': "View Dashboard",
                'cta_link': f"{settings.frontend_url}/dashboard"
            })

    def send_escrow_dispute_mail(self, payer: Users, payee: Users, escrow: Escrow):
        subject = f"Action Required: A Dispute Has Been Opened (Escrow ID {escrow.id})"

        # Payer
        if payer and hasattr(payer, 'email') and payer.email:
            self._render_and_dispatch('escrow_event.html', [payer.email], subject, {
                'event_title': "We're Here to Help",
                'event_type': 'dispute_payer',
                'name': payer.username,
                'escrow_id': str(escrow.id),
                'cta_text': "Go to Dispute Center",
                'cta_link': f"{settings.frontend_url}/dashboard/support"
            })

        # Payee
        if payee and hasattr(payee, 'email') and payee.email:
            self._render_and_dispatch('escrow_event.html', [payee.email], subject, {
                'event_title': "We're Here to Help",
                'event_type': 'dispute_payee',
                'name': payee.username,
                'escrow_id': str(escrow.id),
                'cta_text': "Go to Dispute Center",
                'cta_link': f"{settings.frontend_url}/dashboard/support"
            })

    def send_escrow_status_change_mail(self, payer: Users, payee: Users, escrow: Escrow, status_name: str):
        subject = f"Escrow Status Updated to {status_name.upper()} (ID: {escrow.id})"
        amount_str = f"₦{escrow.amount_cents / 100:,.2f}"

        if payer and hasattr(payer, 'email') and payer.email:
            self._render_and_dispatch('escrow_event.html', [payer.email], subject, {
                'event_title': f"Escrow Status: {status_name.upper()}",
                'event_type': 'status_update_payer',
                'name': payer.username,
                'escrow_id': str(escrow.id),
                'amount': amount_str,
                'status_display': status_name.upper(),
                'cta_text': "View Escrows",
                'cta_link': f"{settings.frontend_url}/dashboard/escrows"
            })

        if payee and hasattr(payee, 'email') and payee.email:
            self._render_and_dispatch('escrow_event.html', [payee.email], subject, {
                'event_title': f"Escrow Status: {status_name.upper()}",
                'event_type': 'status_update_payee',
                'name': payee.username,
                'escrow_id': str(escrow.id),
                'amount': amount_str,
                'status_display': status_name.upper(),
                'cta_text': "View Escrows",
                'cta_link': f"{settings.frontend_url}/dashboard/escrows"
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

        email = getattr(user, 'email', None)
        if not email:
            print("Cannot send KYC status email: missing user email")
            return

        context = {
            'name': getattr(user, 'username', 'Valued User'),
            'status': status,
            'rejection_reason': rejection_reason,
            'cta_link': f"{settings.frontend_url}/dashboard/profile"
        }
        self._render_and_dispatch('kyc_status.html', [str(email)], subject, context)

    def send_driver_license_status_mail(self, user: Users, status: str, rejection_reason: str = None):
        if status in ["verified", "approved"]:
            subject = "Driver License Verification Approved 🎉 - DGE World"
        else:
            subject = "Driver License Verification Update - DGE World"

        email = getattr(user, 'email', None)
        if not email:
            print("Cannot send Driver License status email: missing user email")
            return

        context = {
            'name': getattr(user, 'username', 'Valued User'),
            'status': status,
            'rejection_reason': rejection_reason,
            'cta_link': f"{settings.frontend_url}/dashboard/profile?tab=driver"
        }
        self._render_and_dispatch('driver_license_status.html', [str(email)], subject, context)

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

    def send_job_status_mail(self, user, job_title: str, status: str, message: str = None, reason: str = None):
        subject = f"Job Update ({status.capitalize()}): '{job_title}'"
        username = getattr(user, 'username', 'Valued User')
        email = getattr(user, 'email', '')
        default_msg = f"The status of your job '{job_title}' has been updated to {status.lower()}."
        context = {
            'name': username,
            'job_title': job_title,
            'status': status,
            'status_display': status.capitalize(),
            'message': message or default_msg,
            'reason': reason,
            'cta_link': f"{settings.frontend_url}/dashboard/my-jobs"
        }
        self._render_and_dispatch('job_status.html', [str(email)], subject, context)

    # ─── Support Tickets ───────────────────────────────────────────────────

    def send_ticket_created_mail(self, user, ticket):
        username = getattr(user, 'username', 'Valued User')
        user_email = getattr(user, 'email', '')
        short_id = str(ticket.id)[:8].upper()
        subject = f"Support Ticket Created: [{short_id}] {ticket.subject}"

        # To User
        if user_email:
            user_context = {
                'name': username,
                'event_title': "Support Ticket Received",
                'header_message': f"Your support ticket #{short_id} has been created and received by our support team.",
                'message': ticket.description,
                'subject': ticket.subject,
                'ticket_id': short_id,
                'status_display': (ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)).upper(),
                'author_name': username,
                'cta_link': f"{settings.frontend_url}/dashboard/support/{ticket.id}"
            }
            self._render_and_dispatch('ticket_notification.html', [str(user_email)], subject, user_context)

        # Alert Admin Support
        admin_email = os.getenv("SUPPORT_ADMIN_EMAIL") or os.getenv("EMAIL_SENDER_ADDRESS")
        if admin_email:
            admin_context = {
                'name': "Support Admin",
                'event_title': "New Support Ticket Opened",
                'header_message': f"A new support ticket #{short_id} was submitted by {username} ({user_email}).",
                'message': ticket.description,
                'subject': ticket.subject,
                'ticket_id': short_id,
                'status_display': (ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)).upper(),
                'author_name': username,
                'cta_link': f"{settings.frontend_url}/admin/support"
            }
            self._render_and_dispatch('ticket_notification.html', [str(admin_email)], f"New Ticket Alert: [{short_id}] {ticket.subject}", admin_context)

    def send_ticket_reply_mail(self, recipient_email: str, recipient_name: str, ticket, reply_message: str, author_name: str, is_admin_reply: bool):
        if not recipient_email:
            return
        short_id = str(ticket.id)[:8].upper()
        subject = f"New Reply on Ticket: [{short_id}] {ticket.subject}"
        cta = f"{settings.frontend_url}/admin/support" if not is_admin_reply else f"{settings.frontend_url}/dashboard/support/{ticket.id}"

        context = {
            'name': recipient_name or "Valued User",
            'event_title': "New Support Reply",
            'header_message': f"{author_name} posted a reply on support ticket #{short_id}.",
            'message': reply_message,
            'subject': ticket.subject,
            'ticket_id': short_id,
            'status_display': (ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)).upper(),
            'author_name': author_name,
            'cta_link': cta
        }
        self._render_and_dispatch('ticket_notification.html', [str(recipient_email)], subject, context)




