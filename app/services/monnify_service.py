"""
Monnify payment gateway integration service.
Docs: https://developers.monnify.com/
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MONNIFY_API_KEY = os.getenv("MONNIFY_API_KEY", "")
MONNIFY_SECRET_KEY = os.getenv("MONNIFY_SECRET_KEY", "")
MONNIFY_CONTRACT_CODE = os.getenv("MONNIFY_CONTRACT_CODE", "")
MONNIFY_BASE_URL = os.getenv("MONNIFY_BASE_URL", "https://sandbox.monnify.com")

# In-memory token cache: {token: str, expires_at: float}
_token_cache: dict = {}


class MonnifyService:
    """Async wrapper around the Monnify REST API."""

    def __init__(self):
        self.base_url = MONNIFY_BASE_URL
        self.api_key = MONNIFY_API_KEY
        self.secret_key = MONNIFY_SECRET_KEY
        self.contract_code = MONNIFY_CONTRACT_CODE

    # ──────────────────────────────────────────────────────────────────────────
    # Auth
    # ──────────────────────────────────────────────────────────────────────────

    async def get_access_token(self) -> str:
        """Retrieve a Monnify bearer token, using cached value when still valid."""
        global _token_cache

        now = time.time()
        if _token_cache.get("token") and _token_cache.get("expires_at", 0) > now + 60:
            return _token_cache["token"]

        credentials = f"{self.api_key}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

        token = data["responseBody"]["accessToken"]
        expires_in = data["responseBody"].get("expiresIn", 3600)

        _token_cache = {"token": token, "expires_at": now + expires_in}
        return token

    async def _auth_headers(self) -> dict:
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Payment Link / Checkout Initiation
    # ──────────────────────────────────────────────────────────────────────────

    async def initiate_payment(
        self,
        amount: float,
        customer_email: str,
        customer_name: str,
        payment_reference: str,
        payment_description: str = "Wallet funding",
        redirect_url: str = "",
    ) -> dict:
        """
        Initiate a Monnify checkout session.
        Returns responseBody containing checkoutUrl and transactionReference.
        """
        payload = {
            "amount": amount,
            "customerName": customer_name,
            "customerEmail": customer_email,
            "paymentReference": payment_reference,
            "paymentDescription": payment_description,
            "currencyCode": "NGN",
            "contractCode": self.contract_code,
            "redirectUrl": redirect_url,
            "paymentMethods": ["ACCOUNT_TRANSFER", "CARD"],
        }
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/merchant/transactions/init-transaction",
                json=payload,
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get("responseBody", {})

    # ──────────────────────────────────────────────────────────────────────────
    # Reserved / Dynamic Virtual Account
    # ──────────────────────────────────────────────────────────────────────────

    async def create_reserved_account(
        self,
        account_reference: str,
        account_name: str,
        customer_email: str,
        customer_name: str,
        bvn: Optional[str] = None,
    ) -> dict:
        """
        Create a dedicated virtual bank account for a user (DVA flow).
        Returns responseBody including accountNumber, bankName, accountName.
        """
        payload = {
            "accountReference": account_reference,
            "accountName": account_name,
            "customerEmail": customer_email,
            "customerName": customer_name,
            "currencyCode": "NGN",
            "contractCode": self.contract_code,
            "getAllAvailableBanks": False,
            "preferredBanks": ["232"],  # Sterling Bank code; change as needed
        }
        if bvn:
            payload["bvn"] = bvn

        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/bank-transfer/reserved-accounts",
                json=payload,
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get("responseBody", {})

    # ──────────────────────────────────────────────────────────────────────────
    # Account Verification
    # ──────────────────────────────────────────────────────────────────────────

    async def verify_bank_account(self, account_number: str, bank_code: str) -> dict:
        """
        Resolve account number → account name using Monnify's name enquiry API.
        Returns dict with accountNumber, accountName, bankCode, bankName.
        """
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/disbursements/account/validate",
                params={"accountNumber": account_number, "bankCode": bank_code},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("responseBody", {})

    # ──────────────────────────────────────────────────────────────────────────
    # Disbursements (Withdrawal Transfer)
    # ──────────────────────────────────────────────────────────────────────────

    async def initiate_single_transfer(
        self,
        amount: float,
        reference: str,
        narration: str,
        destination_bank_code: str,
        destination_account_number: str,
        destination_account_name: str,
        source_account_number: Optional[str] = None,
    ) -> dict:
        """
        Initiate a single disbursement from the merchant wallet to a user's bank account.
        Returns responseBody with status and reference.
        """
        payload = {
            "amount": amount,
            "reference": reference,
            "narration": narration,
            "destinationBankCode": destination_bank_code,
            "destinationAccountNumber": destination_account_number,
            "currency": "NGN",
            "sourceAccountNumber": source_account_number or os.getenv("MONNIFY_WALLET_ACCOUNT", ""),
            "destinationAccountName": destination_account_name,
        }
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/disbursements/single",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("responseBody", {})

    # ──────────────────────────────────────────────────────────────────────────
    # Transaction Status
    # ──────────────────────────────────────────────────────────────────────────

    async def get_transaction_status(self, payment_reference: str) -> dict:
        """
        Poll Monnify for current status of a collection transaction.
        Uses the v2 query endpoint with paymentReference as a query param.
        Docs: https://developers.monnify.com/
        """
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v2/merchant/transactions/query",
                params={"paymentReference": payment_reference},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("responseBody", {})

    # ──────────────────────────────────────────────────────────────────────────
    # Webhook Verification
    # ──────────────────────────────────────────────────────────────────────────

    def verify_webhook_signature(self, raw_body: bytes, monnify_signature: str) -> bool:
        """
        Verify that an incoming webhook came from Monnify.
        Monnify signs with HMAC-SHA512 of the raw body using the secret key.
        """
        expected = hmac.new(
            self.secret_key.encode(),
            raw_body,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, monnify_signature)

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_banks_list(self) -> list[dict]:
        """Returns a static list of common Nigerian banks with their Monnify codes."""
        return [
            {"name": "Access Bank", "code": "044"},
            {"name": "Citibank", "code": "023"},
            {"name": "Diamond Bank", "code": "063"},
            {"name": "Ecobank Nigeria", "code": "050"},
            {"name": "Fidelity Bank", "code": "070"},
            {"name": "First Bank of Nigeria", "code": "011"},
            {"name": "First City Monument Bank", "code": "214"},
            {"name": "Guaranty Trust Bank", "code": "058"},
            {"name": "Heritage Bank", "code": "030"},
            {"name": "Keystone Bank", "code": "082"},
            {"name": "Polaris Bank", "code": "076"},
            {"name": "Providus Bank", "code": "101"},
            {"name": "Stanbic IBTC Bank", "code": "221"},
            {"name": "Standard Chartered Bank", "code": "068"},
            {"name": "Sterling Bank", "code": "232"},
            {"name": "Suntrust Bank", "code": "100"},
            {"name": "Union Bank of Nigeria", "code": "032"},
            {"name": "United Bank For Africa", "code": "033"},
            {"name": "Unity Bank", "code": "215"},
            {"name": "Wema Bank", "code": "035"},
            {"name": "Zenith Bank", "code": "057"},
            {"name": "Kuda Bank", "code": "090267"},
            {"name": "OPay", "code": "100004"},
            {"name": "PalmPay", "code": "100033"},
            {"name": "Moniepoint", "code": "50515"},
        ]


# Module-level singleton
monnify_service = MonnifyService()
