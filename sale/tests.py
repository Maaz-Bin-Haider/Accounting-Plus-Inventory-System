import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin
from sale.views import get_item_by_serial_for_sale


class SaleEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("sale-test-user")

    def setUp(self):
        self.user.refresh_from_db()
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)
        self.client.force_login(self.user)

    def test_sales_page_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("sale:sales"))
        login = reverse("authentication:login")
        target = reverse("sale:sales")
        self.assertRedirects(response, f"{login}?next={target}")

    def test_sales_page_redirects_without_view_permission(self):
        response = self.client.get(reverse("sale:sales"))
        self.assertRedirects(
            response, reverse("home:home"), fetch_redirect_response=False
        )

    def test_sales_page_renders_with_view_permission(self):
        self.grant_permissions(self.user, "view_sale")
        response = self.client.get(reverse("sale:sales"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sale_templates/sale_template.html")

    def test_sales_post_rejects_invalid_json(self):
        self.grant_permissions(self.user, "view_sale")
        response = self.client.post(
            reverse("sale:sales"), data="{invalid", content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content, {"success": False, "message": "Invalid JSON"}
        )

    def test_sale_submit_requires_party_date_and_items(self):
        self.grant_permissions(self.user, "view_sale")
        url = reverse("sale:sales")

        missing_party = self.client.post(
            url,
            data=json.dumps({"action": "submit"}),
            content_type="application/json",
        )
        self.assertIn("Party name", missing_party.json()["message"])

        missing_date = self.client.post(
            url,
            data=json.dumps({"action": "submit", "party_name": "CUSTOMER"}),
            content_type="application/json",
        )
        self.assertIn("Date", missing_date.json()["message"])

        missing_items = self.client.post(
            url,
            data=json.dumps({
                "action": "submit",
                "party_name": "CUSTOMER",
                "sale_date": "2020-01-01",
            }),
            content_type="application/json",
        )
        self.assertIn("item", missing_items.json()["message"].lower())

    def test_sale_delete_requires_invoice_id(self):
        self.grant_permissions(self.user, "view_sale")
        response = self.client.post(
            reverse("sale:sales"),
            data=json.dumps({"action": "delete"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("Navigate", response.json()["message"])

    def test_sales_post_requires_csrf_token(self):
        self.grant_permissions(self.user, "view_sale")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse("sale:sales"),
            data=json.dumps({"action": "delete", "sale_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_single_serial_lookup_rejects_missing_view_permission(self):
        response = self.client.get(
            reverse("sale:sale_lookup_serial", kwargs={"serial": "SER-001"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("permission", response.json()["message"].lower())

    @patch("sale.views.connection")
    def test_serial_helper_returns_normalized_stock_result(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True, "IPHONE 15", "200000.50")
        result = get_item_by_serial_for_sale("  SER-001  ")
        self.assertEqual(result, {
            "success": True,
            "serial": "SER-001",
            "item_name": "IPHONE 15",
            "purchase_price": 200000.5,
        })
        self.assertEqual(cursor.execute.call_args.args[1], ["SER-001"])

    @patch("sale.views.connection")
    def test_serial_helper_rejects_missing_and_sold_serials(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (False, "IPHONE 15", 200000)]
        missing = get_item_by_serial_for_sale("MISSING")
        sold = get_item_by_serial_for_sale("SOLD")
        self.assertFalse(missing["success"])
        self.assertIn("not found", missing["message"])
        self.assertFalse(sold["success"])
        self.assertIn("not in stock", sold["message"])

    def test_bulk_lookup_requires_post_and_valid_payload(self):
        self.grant_permissions(self.user, "view_sale")
        url = reverse("sale:sale_bulk_serial_lookup")
        get_response = self.client.get(url)
        self.assertIn("POST required", get_response.json()["message"])
        json_response = self.client.post(
            url, data="{invalid", content_type="application/json"
        )
        self.assertIn("Invalid JSON", json_response.json()["message"])
        empty_response = self.client.post(
            url, data=json.dumps({}), content_type="application/json"
        )
        self.assertIn("Provide", empty_response.json()["message"])

    @patch("sale.views.get_item_by_serial_for_sale")
    def test_bulk_lookup_deduplicates_groups_and_reports_invalid(self, lookup):
        self.grant_permissions(self.user, "view_sale")

        def result(serial):
            if serial == "BAD":
                return {"success": False, "message": "not found"}
            return {
                "success": True,
                "serial": serial,
                "item_name": "IPHONE 15",
                "purchase_price": 200000.0,
            }

        lookup.side_effect = result
        response = self.client.post(
            reverse("sale:sale_bulk_serial_lookup"),
            data=json.dumps({"raw": "SER-1\nser-1,SER-2;BAD"}),
            content_type="application/json",
        )
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["total_input"], 4)
        self.assertEqual(payload["unique"], 3)
        self.assertEqual(payload["groups"][0]["serials"], ["SER-1", "SER-2"])
        self.assertEqual(payload["invalid"], [{"serial": "BAD", "reason": "not found"}])

    def test_get_sale_rejects_invalid_navigation_ids(self):
        previous = self.client.get(
            reverse("sale:get_sale"), {"action": "previous", "current_id": "bad"}
        )
        next_response = self.client.get(
            reverse("sale:get_sale"), {"action": "next", "current_id": "bad"}
        )
        current = self.client.get(
            reverse("sale:get_sale"), {"action": "current", "current_id": "bad"}
        )
        self.assertIn("Invalid Previous", previous.json()["message"])
        self.assertIn("No Next", next_response.json()["message"])
        self.assertIn("No Sale", current.json()["message"])

    @patch("sale.views.connection")
    def test_get_sale_returns_current_database_payload(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"sale_id": 42, "party_name": "CUSTOMER"},)
        response = self.client.get(
            reverse("sale:get_sale"), {"action": "current", "current_id": "42"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sale_id"], 42)
        self.assertIn("get_current_sale", cursor.execute.call_args.args[0])
        self.assertEqual(cursor.execute.call_args.args[1], [42])

    def test_sale_summary_rejects_invalid_or_partial_dates(self):
        invalid = self.client.get(
            reverse("sale:get_sale_summary"), {"from": "not-a-date", "to": "2020-01-01"}
        )
        partial = self.client.get(
            reverse("sale:get_sale_summary"), {"from": "2020-01-01"}
        )
        self.assertIn("Invalid date", invalid.json()["message"])
        self.assertIn("Invalid date", partial.json()["message"])

    @patch("sale.views.connection")
    def test_sale_summary_returns_default_database_payload(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ([{"sale_id": 42, "total": "250000"}],)
        response = self.client.get(reverse("sale:get_sale_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["sale_id"], 42)
        self.assertIn("get_sales_summary()", cursor.execute.call_args.args[0])
