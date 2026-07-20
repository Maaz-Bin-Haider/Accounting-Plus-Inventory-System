from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin
from home.views import _run_pg_function


class DashboardEndpointTests(UserPermissionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("dashboard-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)
        cache.clear()

    def test_home_requires_login_and_renders_for_authenticated_user(self):
        url = reverse("home:home")
        self.client.logout()
        self.assertRedirects(
            self.client.get(url), f'{reverse("authentication:login")}?next={url}'
        )
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home_templtes/home_template.html")

    def test_every_dashboard_section_denies_missing_permission(self):
        names = [
            "dash_sales_today", "dash_sales_chart", "dash_stock_kpi",
            "dash_low_stock", "dash_fast_moving", "dash_stale_stock",
            "dash_top_customers", "dash_top_vendors",
            "dash_receivables_aging", "dash_recent_transactions",
            "dash_expense_kpi", "dash_expense_categories",
            "dash_expense_descriptions", "dash_smart_alerts",
        ]
        for name in names:
            with self.subTest(endpoint=name):
                response = self.client.get(reverse(f"home:{name}"))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["status"], "denied")

    @patch("home.views._run_pg_function")
    def test_sales_today_permission_and_function_contract(self, run_function):
        self.grant_permissions(self.user, "view_dash_sales_profit")
        run_function.return_value = {"revenue": 1000, "invoice_count": 2}
        response = self.client.get(reverse("home:dash_sales_today"))
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["data"]["revenue"], 1000)
        run_function.assert_called_once_with("SELECT fn_dash_sales_today_kpi();")

    @patch("home.views._run_pg_function")
    def test_sales_chart_default_and_custom_range_contracts(self, run_function):
        self.grant_permissions(self.user, "view_dash_sales_profit")
        run_function.return_value = []
        self.client.get(reverse("home:dash_sales_chart"))
        run_function.assert_called_with("SELECT fn_dash_sales_last7days();")
        self.client.get(
            reverse("home:dash_sales_chart"),
            {"from": "2020-01-01", "to": "2020-01-31"},
        )
        run_function.assert_called_with(
            "SELECT fn_dash_sales_range(%s::date, %s::date);",
            ["2020-01-01", "2020-01-31"],
        )

    @patch("home.views._run_pg_function")
    def test_stock_parameter_contracts(self, run_function):
        self.grant_permissions(self.user, "view_dash_stock_overview")
        run_function.return_value = []
        self.client.get(reverse("home:dash_low_stock"), {"threshold": "7"})
        run_function.assert_called_with(
            "SELECT fn_dash_low_stock_items(%s);", [7]
        )
        self.client.get(
            reverse("home:dash_fast_moving"), {"days": "60", "limit": "4"}
        )
        run_function.assert_called_with(
            "SELECT fn_dash_fast_moving_items(%s, %s);", [60, 4]
        )
        self.client.get(reverse("home:dash_stale_stock"), {"days": "90"})
        run_function.assert_called_with("SELECT fn_dash_stale_stock(%s);", [90])

    @patch("home.views._run_pg_function")
    def test_top_party_and_recent_transaction_parameters(self, run_function):
        self.grant_permissions(
            self.user, "view_dash_top_parties", "view_dash_recent_transactions"
        )
        run_function.return_value = []
        self.client.get(
            reverse("home:dash_top_customers"),
            {"limit": "3", "from": "2020-01-01", "to": "2020-01-31"},
        )
        run_function.assert_called_with(
            "SELECT fn_dash_top_customers(%s, %s::date, %s::date);",
            [3, "2020-01-01", "2020-01-31"],
        )
        self.client.get(reverse("home:dash_recent_transactions"), {"limit": "8"})
        run_function.assert_called_with(
            "SELECT fn_dash_recent_transactions(%s);", [8]
        )

    @patch("home.views._run_pg_function")
    def test_expense_and_alert_function_contracts(self, run_function):
        self.grant_permissions(
            self.user, "view_dash_expense_tracking", "view_dash_smart_alerts"
        )
        run_function.return_value = []
        self.client.get(reverse("home:dash_expense_kpi"))
        run_function.assert_called_with("SELECT fn_dash_expense_kpi();")
        self.client.get(reverse("home:dash_expense_categories"), {"limit": "6"})
        run_function.assert_called_with(
            "SELECT fn_dash_top_expense_categories(%s, %s::date, %s::date);",
            [6, None, None],
        )
        self.client.get(reverse("home:dash_smart_alerts"))
        run_function.assert_called_with("SELECT fn_dash_smart_alerts();")

    def test_dashboard_api_rejects_post(self):
        self.grant_permissions(self.user, "view_dash_sales_profit")
        response = self.client.post(reverse("home:dash_sales_today"))
        self.assertEqual(response.status_code, 405)

    @override_settings(DASHBOARD_CACHE_SECONDS=60)
    @patch("home.views.connection")
    def test_pg_helper_caches_identical_queries(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"value": 42},)
        first = _run_pg_function("SELECT test_dashboard(%s);", [1])
        second = _run_pg_function("SELECT test_dashboard(%s);", [1])
        self.assertEqual(first, {"value": 42})
        self.assertEqual(second, first)
        cursor.execute.assert_called_once_with(
            "SELECT test_dashboard(%s);", [1]
        )

    @override_settings(DASHBOARD_CACHE_SECONDS=0)
    @patch("home.views.connection")
    def test_pg_helper_can_disable_cache(self, view_connection):
        cursor = view_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"value": 42},)
        _run_pg_function("SELECT test_dashboard();")
        _run_pg_function("SELECT test_dashboard();")
        self.assertEqual(cursor.execute.call_count, 2)

    def test_legacy_financial_endpoints_hide_data_without_permissions(self):
        cash = self.client.get(reverse("home:get_cash_balance"))
        parties = self.client.get(reverse("home:get_party_balances"))
        receivables = self.client.get(reverse("home:get_receivables"))
        payables = self.client.get(reverse("home:get_payables"))
        expenses = self.client.get(reverse("home:get_expense_party_balances"))
        self.assertEqual(cash.json()["cash_balance"], 0.0)
        for response in (parties, receivables, payables, expenses):
            self.assertEqual(response.json(), {})
