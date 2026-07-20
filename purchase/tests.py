import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class PurchaseEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("purchase-test-user")

    def setUp(self):
        self.user.refresh_from_db()
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)
        self.client.force_login(self.user)

    @staticmethod
    def valid_payload(**overrides):
        payload = {
            "action": "submit",
            "party_name": "VENDOR",
            "purchase_date": "2020-01-01",
            "description": "  Stock purchase  ",
            "items": [{
                "item_name": "IPHONE 15",
                "qty": 1,
                "unit_price": 200000,
                "serials": [{"serial": "SER-001", "comment": "Blue"}],
            }],
        }
        payload.update(overrides)
        return payload

    def test_page_requires_authentication_and_view_permission(self):
        self.client.logout()
        url = reverse("purchase:purchasing")
        response = self.client.get(url)
        self.assertRedirects(
            response, f'{reverse("authentication:login")}?next={url}'
        )
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertRedirects(
            response, reverse("home:home"), fetch_redirect_response=False
        )

    def test_page_renders_with_view_permission(self):
        self.grant_permissions(self.user, "view_purchase")
        response = self.client.get(reverse("purchase:purchasing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "purchase_templates/purchasing_template.html"
        )

    def test_post_rejects_invalid_json_and_missing_fields(self):
        self.grant_permissions(self.user, "view_purchase")
        url = reverse("purchase:purchasing")
        invalid = self.client.post(url, "{bad", content_type="application/json")
        self.assertIn("Invalid JSON", invalid.json()["message"])
        missing = self.client.post(
            url, json.dumps({"action": "submit"}), content_type="application/json"
        )
        self.assertIn("Party name", missing.json()["message"])

    def test_post_requires_csrf(self):
        self.grant_permissions(self.user, "view_purchase")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            reverse("purchase:purchasing"),
            json.dumps({"action": "delete", "purchase_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("purchase.views.connection")
    def test_create_requires_create_permission(self, view_connection):
        self.grant_permissions(self.user, "view_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (1,), None]
        response = self.client.post(
            reverse("purchase:purchasing"),
            json.dumps(self.valid_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.json()["status"], "error")

    @patch("purchase.views.connection")
    def test_create_rejects_view_only_group(self, view_connection):
        self.grant_permissions(self.user, "view_purchase", "create_purchase")
        self.user.groups.add(Group.objects.create(name="view_only_users"))
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (1,), None]
        response = self.client.post(
            reverse("purchase:purchasing"),
            json.dumps(self.valid_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.json()["status"], "error")

    @patch("purchase.views.connection")
    def test_create_executes_procedure_and_saves_description(self, view_connection):
        self.grant_permissions(self.user, "view_purchase", "create_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1,), (1,), None, (7,), (42,)]
        response = self.client.post(
            reverse("purchase:purchasing"),
            json.dumps(self.valid_payload()),
            content_type="application/json",
        )
        self.assertTrue(response.json()["success"])
        calls = cursor.execute.call_args_list
        create = next(call for call in calls if "create_purchase" in call.args[0])
        self.assertEqual(create.args[1][0], 7)
        self.assertEqual(create.args[1][1], "2020-01-01")
        self.assertEqual(create.args[1][3], self.user.id)
        self.assertEqual(json.loads(create.args[1][2])[0]["serials"][0]["serial"], "SER-001")
        description = next(
            call for call in calls if "UPDATE purchaseinvoices" in call.args[0]
        )
        self.assertEqual(description.args[1], ["Stock purchase", 42])

    @patch("purchase.views.connection")
    def test_update_stops_when_validation_rejects(self, view_connection):
        self.grant_permissions(self.user, "view_purchase", "update_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (1,), (1,), (json.dumps({
                "is_valid": False,
                "sold_serials": ["SER-001"],
                "returned_serials": [],
            }),),
        ]
        response = self.client.post(
            reverse("purchase:purchasing"),
            json.dumps(self.valid_payload(purchase_id=42)),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])
        self.assertIn("SER-001", response.json()["message"])
        self.assertFalse(any(
            "update_purchase_invoice" in call.args[0]
            for call in cursor.execute.call_args_list
        ))

    @patch("purchase.views.connection")
    def test_update_executes_procedure_and_description(self, view_connection):
        self.grant_permissions(self.user, "view_purchase", "update_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (1,), (1,), (json.dumps({"is_valid": True}),), (7,), (None,),
        ]
        response = self.client.post(
            reverse("purchase:purchasing"),
            json.dumps(self.valid_payload(purchase_id=42)),
            content_type="application/json",
        )
        self.assertTrue(response.json()["success"])
        update = next(
            call for call in cursor.execute.call_args_list
            if "update_purchase_invoice" in call.args[0]
        )
        self.assertEqual(update.args[1][0], 42)
        self.assertEqual(update.args[1][2:], ["VENDOR", "2020-01-01", self.user.id])

    @patch("purchase.views.connection")
    def test_delete_permission_and_execution(self, view_connection):
        self.grant_permissions(self.user, "view_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (json.dumps({"is_valid": True}),)
        url = reverse("purchase:purchasing")
        body = json.dumps({"action": "delete", "purchase_id": 42})
        denied = self.client.post(url, body, content_type="application/json")
        self.assertEqual(denied.json()["status"], "error")

        self.grant_permissions(self.user, "delete_purchase")
        allowed = self.client.post(url, body, content_type="application/json")
        self.assertTrue(allowed.json()["success"])
        delete = next(
            call for call in cursor.execute.call_args_list
            if "SELECT delete_purchase" in call.args[0]
        )
        self.assertEqual(delete.args[1], [42])

    def test_navigation_rejects_invalid_ids(self):
        url = reverse("purchase:get_purchase")
        previous = self.client.get(url, {"action": "previous", "current_id": "bad"})
        next_response = self.client.get(url, {"action": "next", "current_id": "bad"})
        current = self.client.get(url, {"action": "current", "current_id": "bad"})
        self.assertIn("Invalid Previous", previous.json()["message"])
        self.assertIn("No Next", next_response.json()["message"])
        self.assertIn("No Purchase", current.json()["message"])

    @patch("purchase.views.connection")
    def test_navigation_returns_current_payload(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"purchase_id": 42, "party_name": "VENDOR"},)
        response = self.client.get(
            reverse("purchase:get_purchase"),
            {"action": "current", "current_id": "42"},
        )
        self.assertEqual(response.json()["purchase_id"], 42)
        self.assertIn("get_current_purchase", cursor.execute.call_args.args[0])

    def test_summary_rejects_invalid_dates(self):
        response = self.client.get(
            reverse("purchase:get_purchase_summary"),
            {"from": "bad", "to": "2020-01-01"},
        )
        self.assertIn("Invalid date", response.json()["message"])

    @patch("purchase.views.connection")
    def test_summary_returns_default_payload(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ([{"purchase_id": 42}],)
        response = self.client.get(reverse("purchase:get_purchase_summary"))
        self.assertEqual(response.json()[0]["purchase_id"], 42)
        self.assertIn("get_purchase_summary()", cursor.execute.call_args.args[0])

    def test_serial_check_requires_permission_post_and_list(self):
        url = reverse("purchase:purchase_serial_check")
        denied = self.client.post(url, "{}", content_type="application/json")
        self.assertIn("Permission denied", denied.json()["message"])
        self.grant_permissions(self.user, "view_purchase")
        get_response = self.client.get(url)
        self.assertIn("POST required", get_response.json()["message"])
        invalid = self.client.post(
            url, json.dumps({"serials": "not-list"}), content_type="application/json"
        )
        self.assertIn("must be a list", invalid.json()["message"])

    @patch("purchase.views.connection")
    def test_serial_check_classifies_new_stocked_and_historic(self, view_connection):
        self.grant_permissions(self.user, "view_purchase")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (True,), (False,)]
        response = self.client.post(
            reverse("purchase:purchase_serial_check"),
            json.dumps({"serials": ["NEW", "STOCK", "OLD"]}),
            content_type="application/json",
        )
        results = response.json()["results"]
        self.assertEqual(results["NEW"]["status"], "ok")
        self.assertEqual(results["STOCK"]["status"], "in_stock")
        self.assertEqual(results["OLD"]["status"], "ever_existed")
