import asyncio
import uuid
import sys
import os
from datetime import datetime, timezone
import time

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.email_notification_service import NotificationService

# Mock classes to simulate the database models expected by the NotificationService
class MockUser:
    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.id = uuid.uuid4()

class MockNegotiation:
    def __init__(self, proposed_price_cents):
        self.proposed_price_cents = proposed_price_cents
        self.id = uuid.uuid4()

class MockEscrow:
    def __init__(self, amount_cents):
        self.amount_cents = amount_cents
        self.id = uuid.uuid4()

def main():
    notifier = NotificationService()
    
    # Target email address specified by the user
    test_email = "adoxop1@gmail.com"
    
    # Two mock users that both point to the test email address
    user1 = MockUser("JohnDoe", test_email)
    user2 = MockUser("JaneSmith", test_email)
    
    print(f"Sending all test emails to: {test_email}\n")
    
    try:
        print("1. Sending welcome email...")
        notifier.send_signup_welcome_mail(user1)
        time.sleep(1) # Sleep to prevent rate limits or console spam
        
        print("2. Sending verification email...")
        notifier.send_verification_email(user1, "test-token-12345")
        time.sleep(1)
        
        print("3. Sending verification success email...")
        notifier.send_verification_success_email(user1)
        time.sleep(1)
        
        print("4. Sending deposit success email...")
        notifier.send_deposit_success_mail(
            user1, 1500000, "REF-12345", 
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        time.sleep(1)
        
        print("5. Sending withdrawal requested email (Pending)...")
        notifier.send_withdrawal_status_mail(
            user1, "pending", 500000, "GTBank", "0123456789"
        )
        time.sleep(1)
        
        print("6. Sending withdrawal processed email (Approved)...")
        notifier.send_withdrawal_status_mail(
            user1, "approved", 500000, "GTBank", "0123456789", "REF-W-123"
        )
        time.sleep(1)
        
        print("7. Sending withdrawal processed email (Rejected)...")
        notifier.send_withdrawal_status_mail(
            user1, "rejected", 500000, "GTBank", "0123456789", 
            rejection_reason="Invalid account details."
        )
        time.sleep(1)
        
        print("8. Sending service purchase email (Buyer & Seller)...")
        # This will send 2 emails (one to buyer, one to seller)
        notifier.send_service_purchase_mail(
            buyer=user1, seller=user2, 
            service_title="Custom Web Development", 
            amount_cents=7500000, order_id="ORD-999"
        )
        time.sleep(1)
        
        print("9. Sending project submitted email...")
        notifier.send_project_submitted_mail(
            client=user1, freelancer_name="JaneSmith", 
            project_name="E-commerce Website", 
            escrow_id=str(uuid.uuid4()), 
            submission_date="2024-05-16 14:30"
        )
        time.sleep(1)
        
        print("10. Sending negotiation received email...")
        neg = MockNegotiation(1200000)
        notifier.send_price_negotiation_offer(receiver=user1, initiator=user2, negotiation=neg)
        time.sleep(1)
        
        # --- Escrow Events ---
        
        escrow = MockEscrow(1200000)
        
        print("11. Sending escrow creation debit email...")
        notifier.send_escrow_creation_debit(payer=user1, negotiation=neg)
        time.sleep(1)
        
        print("12. Sending escrow creation emails (both parties)...")
        notifier.send_escrow_creation_mail(payer=user1, payee=user2, escrow=escrow)
        time.sleep(1)
        
        print("13. Sending escrow release credit email...")
        notifier.send_escrow_release_credit(payee=user1, escrow=escrow)
        time.sleep(1)
        
        print("14. Sending escrow refund email...")
        notifier.send_escrow_refund_mail(payer=user1, escrow=escrow)
        time.sleep(1)
        
        print("15. Sending escrow dispute email (both parties)...")
        notifier.send_escrow_dispute_mail(payer=user1, payee=user2, escrow=escrow)
        
        print("\nAll test emails dispatched successfully!")
        
    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    main()
