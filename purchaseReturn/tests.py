import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class PurchaseReturnEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("purchase-return-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)

    @staticmethod
    def payload(**changes):
        data = {
            "action": "submit", "party_name": "VENDOR",
            "return_date": "2020-01-01", "serials": ["SER-001"],
            "description": "  Vendor return  ",
        }
        data.update(changes)
        return data

    def test_page_access_rendering_invalid_json_and_csrf(self):
        url = reverse("purchaseReturn:create_purchase_return")
        self.client.logout()
        self.assertRedirects(
            self.client.get(url),
            f'{reverse("authentication:login")}?next={url}',
        )
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(url), reverse("home:home"), fetch_redirect_response=False
        )
        self.grant_permissions(self.user, "view_purchase_return")
        self.assertTemplateUsed(
            self.client.get(url),
            "purchase_return_templates/purchase_return_template.html",
        )
        self.assertIn(
            "Invalid JSON",
            self.client.post(url, "{bad", content_type="application/json").json()["message"],
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(
            client.post(url, "{}", content_type="application/json").status_code, 403
        )

    @patch("purchaseReturn.views.connection")
    def test_lookup_rejects_unavailable_and_returns_stock_item(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (False,)
        missing = self.client.get(
            reverse("purchaseReturn:purchase_return_lookup", kwargs={"serial": "OLD"})
        )
        self.assertFalse(missing.json()["success"])
        cursor.fetchone.return_value = (True,)
        cursor.fetchall.return_value = [("IPHONE 15", 200000)]
        stocked = self.client.get(
            reverse("purchaseReturn:purchase_return_lookup", kwargs={"serial": "STOCK"})
        )
        self.assertTrue(stocked.json()["success"])
        self.assertEqual(stocked.json()["item_price"], 200000)

    @patch("purchaseReturn.views.connection")
    def test_create_permission_and_success_contract(self, view_connection):
        self.grant_permissions(self.user, "view_purchase_return")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (True,), ("VENDOR",)]
        url = reverse("purchaseReturn:create_purchase_return")
        denied = self.client.post(
            url, json.dumps(self.payload()), content_type="application/json"
        )
        self.assertEqual(denied.json()["status"], "error")
        self.grant_permissions(self.user, "create_purchase_return")
        cursor.fetchone.side_effect = [(1,), (True,), ("VENDOR",), (42,)]
        allowed = self.client.post(
            url, json.dumps(self.payload()), content_type="application/json"
        )
        self.assertTrue(allowed.json()["success"])
        create = next(
            call for call in cursor.execute.call_args_list
            if "create_purchase_return" in call.args[0]
        )
        self.assertEqual(create.args[1], ["VENDOR", '["SER-001"]', self.user.id])
        description = next(
            call for call in cursor.execute.call_args_list
            if "UPDATE purchasereturns" in call.args[0]
        )
        self.assertEqual(description.args[1], ["Vendor return", 42])

    @patch("purchaseReturn.views.connection")
    def test_update_and_delete_contracts(self, view_connection):
        self.grant_permissions(
            self.user,
            "view_purchase_return",
            "update_purchase_return",
            "delete_purchase_return",
        )
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (True,)]
        url = reverse("purchaseReturn:create_purchase_return")
        updated = self.client.post(
            url, json.dumps(self.payload(return_id=42)), content_type="application/json"
        )
        self.assertTrue(updated.json()["success"])
        update = next(
            call for call in cursor.execute.call_args_list
            if "update_purchase_return" in call.args[0]
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
            reverse("purchaseReturn:get_purchase_return"),
            {"action": "current", "current_id": "bad"},
        )
        self.assertIn("No Purchase-Return", nav.json()["message"])
        summary = self.client.get(
            reverse("purchaseReturn:get_purchase_return_summary"),
            {"from": "bad", "to": "2020-01-01"},
        )
        self.assertIn("Invalid date", summary.json()["message"])
