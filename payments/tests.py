import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class PaymentEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("payment-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)

    def test_page_access_rendering_and_csrf(self):
        url = reverse("payments:payment")
        self.client.logout()
        self.assertRedirects(
            self.client.get(url), f'{reverse("authentication:login")}?next={url}'
        )
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(url), reverse("home:home"), fetch_redirect_response=False
        )
        self.grant_permissions(self.user, "view_payment")
        self.assertTemplateUsed(
            self.client.get(url), "payments_templates/payment.html"
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(url, {"action": "delete"}).status_code, 403)

    @patch("payments.views.connection")
    def test_create_and_update_procedure_payloads(self, view_connection):
        self.grant_permissions(
            self.user, "view_payment", "create_payment", "update_payment"
        )
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        url = reverse("payments:payment")
        form = {
            "action": "submit", "search_name": "vendor", "amount": "1250.50",
            "payment_date": "2020-01-01", "description": "Cash payment",
        }
        created = self.client.post(url, form)
        self.assertRedirects(created, url, fetch_redirect_response=False)
        make = next(
            call for call in cursor.execute.call_args_list
            if "make_payment" in call.args[0]
        )
        payload = json.loads(make.args[1][0])
        self.assertEqual(payload["party_name"], "VENDOR")
        self.assertEqual(payload["amount"], 1250.5)
        self.assertEqual(payload["created_by_id"], self.user.id)
        updated = self.client.post(url, {**form, "current_id": "42"})
        self.assertRedirects(updated, url, fetch_redirect_response=False)
        update = next(
            call for call in cursor.execute.call_args_list
            if "update_payment" in call.args[0]
        )
        self.assertEqual(update.args[1][0], "42")

    def test_navigation_dates_and_balance_validate_inputs(self):
        nav = self.client.get(reverse("payments:get_payment"), {"current_id": "bad"})
        self.assertEqual(nav.status_code, 400)
        dates = self.client.get(reverse("payments:get_payments_date_wise"))
        self.assertEqual(dates.status_code, 400)
        balance = self.client.get(reverse("payments:get_party_balance"))
        self.assertEqual(balance.status_code, 400)

    @patch("payments.views.connection")
    def test_balance_returns_database_payload(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"found": True, "balance": 5000},)
        response = self.client.get(
            reverse("payments:get_party_balance"), {"name": "VENDOR"}
        )
        self.assertTrue(response.json()["found"])
        self.assertEqual(response.json()["balance"], 5000)
