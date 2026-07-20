import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class SaleReturnEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("sale-return-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)

    @staticmethod
    def payload(**changes):
        data = {
            "action": "submit", "party_name": "CUSTOMER",
            "return_date": "2020-01-01", "serials": ["SER-001"],
            "description": "  Customer return  ",
        }
        data.update(changes)
        return data

    def test_page_access_and_rendering(self):
        url = reverse("saleReturn:create_sale_return")
        self.client.logout()
        self.assertRedirects(
            self.client.get(url),
            f'{reverse("authentication:login")}?next={url}',
        )
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(url), reverse("home:home"), fetch_redirect_response=False
        )
        self.grant_permissions(self.user, "view_sale_return")
        response = self.client.get(url)
        self.assertTemplateUsed(
            response, "sale_return_templates/sale_return_template.html"
        )

    def test_invalid_json_and_csrf(self):
        self.grant_permissions(self.user, "view_sale_return")
        url = reverse("saleReturn:create_sale_return")
        response = self.client.post(url, "{bad", content_type="application/json")
        self.assertIn("Invalid JSON", response.json()["message"])
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(
            client.post(url, "{}", content_type="application/json").status_code, 403
        )

    @patch("saleReturn.views.connection")
    def test_lookup_rejects_stocked_and_returns_sold_item(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)
        stocked = self.client.get(
            reverse("saleReturn:sale_return_lookup", kwargs={"serial": "STOCK"})
        )
        self.assertFalse(stocked.json()["success"])
        cursor.fetchone.return_value = (False,)
        cursor.fetchall.return_value = [("IPHONE 15", 250000)]
        sold = self.client.get(
            reverse("saleReturn:sale_return_lookup", kwargs={"serial": "SOLD"})
        )
        self.assertTrue(sold.json()["success"])
        self.assertEqual(sold.json()["item_name"], "IPHONE 15")

    @patch("saleReturn.views.connection")
    def test_create_permission_and_success_contract(self, view_connection):
        self.grant_permissions(self.user, "view_sale_return")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (False,), ("CUSTOMER",)]
        url = reverse("saleReturn:create_sale_return")
        denied = self.client.post(
            url, json.dumps(self.payload()), content_type="application/json"
        )
        self.assertEqual(denied.json()["status"], "error")

        self.grant_permissions(self.user, "create_sale_return")
        cursor.fetchone.side_effect = [(1,), (False,), ("CUSTOMER",), (42,)]
        allowed = self.client.post(
            url, json.dumps(self.payload()), content_type="application/json"
        )
        self.assertTrue(allowed.json()["success"])
        create = next(
            call for call in cursor.execute.call_args_list
            if "create_sale_return" in call.args[0]
        )
        self.assertEqual(create.args[1], ["CUSTOMER", '["SER-001"]', self.user.id])
        description = next(
            call for call in cursor.execute.call_args_list
            if "UPDATE salesreturns" in call.args[0]
        )
        self.assertEqual(description.args[1], ["Customer return", 42])

    @patch("saleReturn.views.connection")
    def test_update_and_delete_contracts(self, view_connection):
        self.grant_permissions(
            self.user, "view_sale_return", "update_sale_return", "delete_sale_return"
        )
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (True,)]
        url = reverse("saleReturn:create_sale_return")
        updated = self.client.post(
            url,
            json.dumps(self.payload(return_id=42)),
            content_type="application/json",
        )
        self.assertTrue(updated.json()["success"])
        update = next(
            call for call in cursor.execute.call_args_list
            if "update_sale_return" in call.args[0]
        )
        self.assertEqual(update.args[1], [42, '["SER-001"]', self.user.id])
        deleted = self.client.post(
            url,
            json.dumps({"action": "delete", "return_id": 42}),
            content_type="application/json",
        )
        self.assertTrue(deleted.json()["success"])

    def test_navigation_and_summary_validate_inputs(self):
        nav = self.client.get(
            reverse("saleReturn:get_sale_return"),
            {"action": "current", "current_id": "bad"},
        )
        self.assertIn("No Sale-Return", nav.json()["message"])
        summary = self.client.get(
            reverse("saleReturn:get_sale_return_summary"),
            {"from": "bad", "to": "2020-01-01"},
        )
        self.assertIn("Invalid date", summary.json()["message"])
