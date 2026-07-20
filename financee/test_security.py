from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.http_errors import internal_server_error
from financee.test_support import UserPermissionTestMixin


class CsrfAndErrorDisclosureTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("security-user")

    def test_login_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("authentication:login"),
            {"username": "security-user", "password": self.test_password},
        )
        self.assertEqual(response.status_code, 403)

    def setUp(self):
        self.user.refresh_from_db()
        self.client.force_login(self.user)

    def test_every_business_mutation_route_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        mutation_routes = [
            "parties:add_new_party",
            "parties:update_party",
            "items:add_new_item",
            "items:update_item",
            "payments:payment",
            "receipts:receipt",
            "contra:contra",
            "purchase:purchasing",
            "sale:sales",
            "purchaseReturn:create_purchase_return",
            "saleReturn:create_sale_return",
        ]
        for route in mutation_routes:
            with self.subTest(route=route):
                response = client.post(
                    reverse(route), data="{}", content_type="application/json"
                )
                self.assertEqual(response.status_code, 403)

    @patch("financee.http_errors.logger")
    def test_internal_error_helper_logs_but_never_returns_exception_text(self, logger):
        secret = "SELECT password FROM auth_user; database host=db.internal"
        response = internal_server_error(RuntimeError(secret))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.content,
            b'{"error": "An internal server error occurred."}',
        )
        self.assertNotIn(secret.encode(), response.content)
        logger.exception.assert_called_once()

    @patch("accountsReports.views.connection")
    def test_report_database_failure_does_not_leak_sql_details(self, connection):
        self.grant_permissions(
            self.user, "view_accounts_reports_page", "view_trial_balance"
        )
        connection.cursor.return_value.__enter__.side_effect = RuntimeError(
            "secret SQL: SELECT * FROM private_ledger"
        )
        response = self.client.post(reverse("accountsReports:trial_balance"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(), {"error": "An internal server error occurred."}
        )
        self.assertNotContains(response, "private_ledger", status_code=500)
