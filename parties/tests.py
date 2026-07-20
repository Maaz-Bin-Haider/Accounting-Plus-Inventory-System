from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class PartyEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("party-test-user")

    def setUp(self):
        self.user.refresh_from_db()
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)
        self.client.force_login(self.user)

    def test_parties_hub_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("parties:partiesDash"))
        login = reverse("authentication:login")
        target = reverse("parties:partiesDash")
        self.assertRedirects(response, f"{login}?next={target}")

    def test_parties_hub_redirects_user_without_view_permission(self):
        response = self.client.get(reverse("parties:partiesDash"))
        self.assertRedirects(
            response, reverse("home:home"), fetch_redirect_response=False
        )

    def test_parties_hub_renders_for_authorized_user(self):
        self.grant_permissions(self.user, "view_party")
        response = self.client.get(reverse("parties:partiesDash"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "parties_templates/parties.html")

    @patch("parties.views.connection")
    def test_autocomplete_returns_database_suggestions(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("ALPHA TRADERS",), ("BETA ALPHA",)]

        response = self.client.get(
            reverse("parties:autocomplete_party"), {"term": "alpha"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, ["ALPHA TRADERS", "BETA ALPHA"])
        parameters = cursor.execute.call_args.args[1]
        self.assertEqual(parameters, ["%ALPHA%", "ALPHA%"])

    @patch("parties.views.connection")
    def test_autocomplete_without_term_does_not_query_database(self, view_connection):
        response = self.client.get(reverse("parties:autocomplete_party"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, [])
        view_connection.cursor.assert_not_called()

    def test_parties_list_rejects_user_without_view_permission(self):
        response = self.client.get(reverse("parties:parties_list"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")

    @patch("parties.views.connection")
    def test_parties_list_serializes_authorized_database_rows(self, view_connection):
        self.grant_permissions(self.user, "view_party")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            (
                42,
                "ALPHA TRADERS",
                "Customer",
                "0300-0000000",
                "Karachi",
                1250,
                "Debit",
                "party-test-user",
                datetime(2026, 7, 20, 10, 30, tzinfo=timezone.utc),
            )
        ]

        response = self.client.get(reverse("parties:parties_list"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["parties"][0]["party_id"], 42)
        self.assertEqual(payload["parties"][0]["party_name"], "ALPHA TRADERS")
        self.assertEqual(payload["parties"][0]["opening_balance"], "1250")

    def test_create_party_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse("parties:add_new_party"),
            {"party_name": "ALPHA TRADERS"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("parties.views.connection")
    def test_create_party_rejects_missing_create_permission(self, view_connection):
        self.grant_permissions(self.user, "view_party")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        response = self.client.post(reverse("parties:add_new_party"), {
            "party_name": "ALPHA TRADERS",
            "party_type": "Customer",
            "opening_balance": "0",
            "balance_type": "Debit",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("permission", response.json()["message"].lower())

    @patch("parties.views.connection")
    def test_create_party_rejects_view_only_group(self, view_connection):
        self.grant_permissions(self.user, "view_party", "create_party")
        self.user.groups.add(Group.objects.create(name="view_only_users"))
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        response = self.client.post(reverse("parties:add_new_party"), {
            "party_name": "ALPHA TRADERS",
            "party_type": "Customer",
            "opening_balance": "0",
            "balance_type": "Debit",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("permission", response.json()["message"].lower())

    @patch("parties.views.connection")
    def test_create_party_rejects_duplicate_name(self, view_connection):
        self.grant_permissions(self.user, "view_party", "create_party")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)

        response = self.client.post(reverse("parties:add_new_party"), {
            "party_name": "ALPHA TRADERS",
            "party_type": "Customer",
            "opening_balance": "0",
            "balance_type": "Debit",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("already exists", response.json()["message"])

    @patch("parties.views.connection")
    def test_create_party_passes_normalized_payload_to_database(self, view_connection):
        self.grant_permissions(self.user, "view_party", "create_party")
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        response = self.client.post(reverse("parties:add_new_party"), {
            "party_name": "Alpha Traders",
            "party_type": "Customer",
            "contact_info": "0300-0000000",
            "address": "Karachi",
            "opening_balance": "1250",
            "balance_type": "Debit",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        sql, parameters = cursor.execute.call_args_list[-1].args
        self.assertIn("add_party_from_json", sql)
        import json
        payload = json.loads(parameters[0])
        self.assertEqual(payload["party_name"], "ALPHA TRADERS")
        self.assertEqual(payload["opening_balance"], 1250)
        self.assertEqual(payload["created_by_id"], self.user.id)

    def test_ajax_update_rejects_request_without_selected_party(self):
        self.grant_permissions(self.user, "update_party")
        response = self.client.post(
            reverse("parties:update_party"),
            {"party_name": "ALPHA TRADERS"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("No party selected", response.json()["message"])

    @patch("parties.views.connection")
    def test_ajax_update_passes_normalized_payload_to_database(self, view_connection):
        self.grant_permissions(self.user, "update_party")
        cursor = view_connection.cursor.return_value.__enter__.return_value

        response = self.client.post(
            reverse("parties:update_party"),
            {
                "party_id": "42",
                "party_name": "Alpha Traders",
                "party_type": "Customer",
                "contact_info": "0300-0000000",
                "address": "Karachi",
                "opening_balance": "1250.50",
                "balance_type": "Debit",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        sql, parameters = cursor.execute.call_args.args
        self.assertIn("update_party_from_json", sql)
        self.assertEqual(parameters[0], 42)
        import json
        payload = json.loads(parameters[1])
        self.assertEqual(payload["party_name"], "ALPHA TRADERS")
        self.assertEqual(payload["opening_balance"], 1250.5)
        self.assertEqual(payload["created_by_id"], self.user.id)
