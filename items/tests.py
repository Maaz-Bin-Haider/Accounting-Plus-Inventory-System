import json
from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class ItemEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("item-test-user")

    def setUp(self):
        self.user.refresh_from_db()
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)
        self.client.force_login(self.user)

    def test_items_hub_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("items:itemsDash"))
        login = reverse("authentication:login")
        target = reverse("items:itemsDash")
        self.assertRedirects(response, f"{login}?next={target}")

    def test_items_hub_redirects_user_without_view_permission(self):
        response = self.client.get(reverse("items:itemsDash"))
        self.assertRedirects(
            response, reverse("home:home"), fetch_redirect_response=False
        )

    def test_items_hub_renders_for_authorized_user(self):
        self.grant_permissions(self.user, "view_item")
        response = self.client.get(reverse("items:itemsDash"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "items_templates/items.html")

    @patch("items.views.connection")
    def test_autocomplete_returns_database_suggestions(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("IPHONE 15",), ("USED IPHONE 15",)]
        response = self.client.get(
            reverse("items:autocomplete_item"), {"term": "iphone"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, ["IPHONE 15", "USED IPHONE 15"])
        self.assertEqual(cursor.execute.call_args.args[1], ["%IPHONE%", "IPHONE%"])

    @patch("items.views.connection")
    def test_autocomplete_without_term_does_not_query_database(self, view_connection):
        response = self.client.get(reverse("items:autocomplete_item"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, [])
        view_connection.cursor.assert_not_called()

    def test_items_list_rejects_user_without_view_permission(self):
        response = self.client.get(reverse("items:items_list"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")

    @patch("items.views.connection")
    def test_items_list_serializes_authorized_database_rows(self, view_connection):
        self.grant_permissions(self.user, "view_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        created = datetime(2026, 7, 20, 10, 30, tzinfo=timezone.utc)
        updated = datetime(2026, 7, 21, 11, 45, tzinfo=timezone.utc)
        cursor.fetchall.return_value = [(
            42, "IPHONE 15", 250000, "SHELF A", "IP15", "PHONE", "APPLE",
            "item-test-user", created, updated,
        )]
        response = self.client.get(reverse("items:items_list"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["item_id"], 42)
        self.assertEqual(payload["items"][0]["item_name"], "IPHONE 15")
        self.assertEqual(payload["items"][0]["sale_price"], "250000")
        self.assertEqual(payload["items"][0]["created_by"], "item-test-user")

    def test_create_item_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse("items:add_new_item"), {"item_name": "IPHONE 15"}
        )
        self.assertEqual(response.status_code, 403)

    @patch("items.views.connection")
    def test_create_item_rejects_missing_create_permission(self, view_connection):
        self.grant_permissions(self.user, "view_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        response = self.client.post(reverse("items:add_new_item"), {
            "item_name": "IPHONE 15", "sale_price": "250000"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("permission", response.json()["message"].lower())

    @patch("items.views.connection")
    def test_create_item_rejects_view_only_group(self, view_connection):
        self.grant_permissions(self.user, "view_item", "create_item")
        self.user.groups.add(Group.objects.create(name="view_only_users"))
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        response = self.client.post(reverse("items:add_new_item"), {
            "item_name": "IPHONE 15", "sale_price": "250000"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("permission", response.json()["message"].lower())

    @patch("items.views.connection")
    def test_create_item_rejects_duplicate_name(self, view_connection):
        self.grant_permissions(self.user, "view_item", "create_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        response = self.client.post(reverse("items:add_new_item"), {
            "item_name": "IPHONE 15", "sale_price": "250000"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("already exists", response.json()["message"])

    @patch("items.views.connection")
    def test_create_item_passes_normalized_payload_to_database(self, view_connection):
        self.grant_permissions(self.user, "view_item", "create_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        response = self.client.post(reverse("items:add_new_item"), {
            "item_name": "iPhone 15",
            "sale_price": "250000.50",
            "storage": "256GB",
            "item_code": "IP15",
            "category": "Phone",
            "brand": "Apple",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        sql, parameters = cursor.execute.call_args_list[-1].args
        self.assertIn("add_item_from_json", sql)
        payload = json.loads(parameters[0])
        self.assertEqual(payload["item_name"], "IPHONE 15")
        self.assertEqual(payload["sale_price"], 250000.5)
        self.assertEqual(payload["created_by_id"], self.user.id)

    @patch("items.views.connection")
    def test_create_item_hides_internal_database_error(self, view_connection):
        self.grant_permissions(self.user, "view_item", "create_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        cursor.execute.side_effect = [None, RuntimeError("secret SQL details")]
        response = self.client.post(reverse("items:add_new_item"), {
            "item_name": "IPHONE 15", "sale_price": "250000"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertNotIn("secret SQL details", response.json()["message"])
        self.assertIn("Unable to create", response.json()["message"])

    def test_ajax_update_rejects_request_without_selected_item(self):
        self.grant_permissions(self.user, "update_item")
        response = self.client.post(
            reverse("items:update_item"),
            {"item_name": "IPHONE 15"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("No item selected", response.json()["message"])

    @patch("items.views.connection")
    def test_ajax_update_passes_normalized_payload_to_database(self, view_connection):
        self.grant_permissions(self.user, "update_item")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        response = self.client.post(
            reverse("items:update_item"),
            {
                "item_id": "42",
                "item_name": "iPhone 15",
                "sale_price": "255000.50",
                "storage": "256GB",
                "item_code": "IP15",
                "category": "Phone",
                "brand": "Apple",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        sql, parameters = cursor.execute.call_args.args
        self.assertIn("update_item_from_json", sql)
        payload = json.loads(parameters[0])
        self.assertEqual(payload["item_id"], 42)
        self.assertEqual(payload["item_name"], "IPHONE 15")
        self.assertEqual(payload["sale_price"], 255000.5)
        self.assertEqual(payload["created_by_id"], self.user.id)
