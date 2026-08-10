import logging

import requests

from config.payment_gateway import (
    APP_URL,
    FRONTEND_URL,
    KHALTI_GATEWAY_URL,
    KHALTI_PUBLIC_KEY,
    KHALTI_SECRET_KEY,
)

logger = logging.getLogger(__name__)


class KhaltiGatewayError(Exception):
    """Raised whenever Khalti can't be reached or returns an error response."""


class KhaltiGateway:
    def __init__(self):
        self.base_url = str(KHALTI_GATEWAY_URL).rstrip("/")
        self.secret_key = KHALTI_SECRET_KEY
        self.public_key = KHALTI_PUBLIC_KEY
        self.website_url = str(APP_URL).rstrip("/")
        self.default_return_url = (
            f"{str(FRONTEND_URL).rstrip('/')}/payment/callback/"
        )

    def _headers(self):
        return {
            "Authorization": f"Key {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initiate(self, payment, user_info, return_url=None):
        url = f"{self.base_url}/epayment/initiate/"

        service = payment.order.service
        product_name = (
            service.title if service else f"NepWork Order {payment.order_id}"
        )

        payload = {
            "return_url": return_url or self.default_return_url,
            "website_url": self.website_url,
            "amount": int(payment.amount * 100),
            "purchase_order_id": payment.reference,
            "purchase_order_name": product_name,
            "customer_info": {
                "name": user_info.get("name", ""),
                "email": user_info.get("email", ""),
                "phone": user_info.get("phone", ""),
            },
        }

        try:
            response = requests.post(
                url, json=payload, headers=self._headers(), timeout=15
            )
        except requests.RequestException as exc:
            logger.exception(
                "Khalti initiate request failed for payment %s", payment.id
            )
            raise KhaltiGatewayError(f"Could not reach Khalti: {exc}") from exc

        data = response.json() if response.content else {}

        if response.status_code != 200:
            message = (
                data.get("detail")
                or data.get("error_key")
                or "Khalti payment initiation failed."
            )
            logger.error(
                "Khalti initiate failed for payment %s: %s", payment.id, message
            )
            raise KhaltiGatewayError(message)

        return data

    def lookup(self, pidx):
        url = f"{self.base_url}/epayment/lookup/"

        try:
            response = requests.post(
                url, json={"pidx": pidx}, headers=self._headers(), timeout=15
            )
        except requests.RequestException as exc:
            logger.exception("Khalti lookup request failed for pidx %s", pidx)
            raise KhaltiGatewayError(f"Could not reach Khalti: {exc}") from exc

        data = response.json() if response.content else {}

        if response.status_code != 200:
            message = data.get("detail") or "Khalti payment lookup failed."
            logger.error("Khalti lookup failed for pidx %s: %s", pidx, message)
            raise KhaltiGatewayError(message)

        return data
