import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class ContraEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("contra-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)

    def test_page_access_rendering_and_csrf(self):
        url = reverse("contra:contra")
        self.client.logout()
        self.assertRedirects(
            self.client.get(url), f'{reverse("authentication:login")}?next={url}'
        )
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(url), reverse("home:home"), fetch_redirect_response=False
        )
        self.grant_permissions(self.user, "view_contra_entry")
        self.assertTemplateUsed(self.client.get(url), "contra_templates/contra.html")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(url, {"action": "delete"}).status_code, 403)

    def test_submit_rejects_same_party(self):
        self.grant_permissions(self.user, "view_contra_entry")
        response = self.client.post(reverse("contra:contra"), {
            "action": "submit", "from_search_name": "CASH",
            "to_search_name": "cash", "amount": "100",
            "contra_date": "2020-01-01",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "From and To party cannot be the same")

    @patch("contra.views.connection")
    def test_create_and_update_payloads(self, view_connection):
        self.grant_permissions(
            self.user, "view_contra_entry", "create_contra_entry",
            "update_contra_entry",
        )
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("FROM PARTY",), ("TO PARTY",)]
        url = reverse("contra:contra")
        form = {
            "action": "submit", "from_search_name": "from party",
            "to_search_name": "to party", "amount": "1000.50",
            "contra_date": "2020-01-01", "description": "Transfer",
        }
        self.assertRedirects(
            self.client.post(url, form), url, fetch_redirect_response=False
        )
        make = next(
            call for call in cursor.execute.call_args_list
            if "make_contra" in call.args[0]
        )
        payload = json.loads(make.args[1][0])
        self.assertEqual(payload["from_party_name"], "FROM PARTY")
        self.assertEqual(payload["to_party_name"], "TO PARTY")
        self.assertEqual(payload["created_by_id"], self.user.id)
        self.assertRedirects(
            self.client.post(url, {**form, "current_id": "42"}),
            url,
            fetch_redirect_response=False,
        )
        update = next(
            call for call in cursor.execute.call_args_list
            if "update_contra" in call.args[0]
        )
        self.assertEqual(update.args[1][0], "42")

    def test_navigation_dates_and_balance_validate_inputs(self):
        nav = self.client.get(reverse("contra:get_contra"), {"current_id": "bad"})
        self.assertEqual(nav.status_code, 400)
        dates = self.client.get(reverse("contra:get_contras_date_wise"))
        self.assertEqual(dates.status_code, 400)
        balance = self.client.get(reverse("contra:get_party_balance"))
        self.assertEqual(balance.status_code, 400)

    @patch("contra.views.connection")
    def test_delete_and_balance_database_contracts(self, view_connection):
        self.grant_permissions(
            self.user, "view_contra_entry", "delete_contra_entry"
        )
        cursor = view_connection.cursor.return_value.__enter__.return_value
        url = reverse("contra:contra")
        deleted = self.client.post(url, {"action": "delete", "current_id": "42"})
        self.assertRedirects(deleted, url, fetch_redirect_response=False)
        delete = next(
            call for call in cursor.execute.call_args_list
            if "delete_contra" in call.args[0]
        )
        self.assertEqual(delete.args[1], [42])
        cursor.fetchone.return_value = ({"found": True, "balance": 9000},)
        balance = self.client.get(
            reverse("contra:get_party_balance"), {"name": "FROM PARTY"}
        )
        self.assertEqual(balance.json()["balance"], 9000)
