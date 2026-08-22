import asyncio
import uuid
import sys
import os
from datetime import datetime, timezone
import time

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.email_notification_service import NotificationService

class MockUser:
    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.id = uuid.uuid4()

def main():
    notifier = NotificationService()
    
    # Target test email address
    test_email = "adoxop1@gmail.com"
    user = MockUser("JohnDoe", test_email)
    
    print(f"--- Sending Newly Added Wallet & Transaction Email Notifications ---")
    print(f"Target Recipient: {test_email}\n")
    
    try:
        print("1. Sending Wallet Credit Notification (+₦50,000.00)...")
        notifier.send_wallet_credit_mail(
            user=user,
            amount_cents=5000000,
            reference="REF-CREDIT-9901",
            description="Service Milestone Payout Credit"
        )
        time.sleep(1)

        print("2. Sending Wallet Debit Notification (-₦15,000.00)...")
        notifier.send_wallet_debit_mail(
            user=user,
            amount_cents=1500000,
            reference="REF-DEBIT-4402",
            description="Job Application Fee & Escrow Deposit"
        )
        time.sleep(1)

        print("3. Sending Transaction Status (Successful)...")
        notifier.send_transaction_status_mail(
            user=user,
            status="successful",
            amount_cents=2500000,
            reference="TXN-SUCCESS-771",
            transaction_type="Wallet Deposit",
            description="Bank transfer deposit was confirmed."
        )
        time.sleep(1)

        print("4. Sending Transaction Status (Pending)...")
        notifier.send_transaction_status_mail(
            user=user,
            status="pending",
            amount_cents=1000000,
            reference="TXN-PENDING-332",
            transaction_type="Card Payment",
            description="Awaiting gateway payment processing response."
        )
        time.sleep(1)

        print("5. Sending Transaction Status (Failed / Declined)...")
        notifier.send_transaction_status_mail(
            user=user,
            status="failed",
            amount_cents=500000,
            reference="TXN-FAILED-104",
            transaction_type="Online Checkout",
            failure_reason="Insufficient funds or card bank rejection."
        )
        time.sleep(1)

        print("6. Sending Withdrawal Submitted (Pending)...")
        notifier.send_withdrawal_status_mail(
            user=user,
            status="pending",
            amount_cents=3500000,
            bank_name="Guaranty Trust Bank (GTBank)",
            account_number="0123456789"
        )
        time.sleep(1)

        print("7. Sending Withdrawal Processed (Approved)...")
        notifier.send_withdrawal_status_mail(
            user=user,
            status="approved",
            amount_cents=3500000,
            bank_name="Guaranty Trust Bank (GTBank)",
            account_number="0123456789",
            reference="WDR-SUCCESS-8819"
        )

        print("\n🎉 All newly added wallet & transaction email tests sent successfully!")

    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    main()


