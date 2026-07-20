import json
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from financee.test_support import UserPermissionTestMixin


class ReportEndpointTests(UserPermissionTestMixin, TestCase):
    """HTTP and PostgreSQL contracts for every family of business report."""

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_test_user("report-user")

    def setUp(self):
        self.user.refresh_from_db()
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)
        self.client.force_login(self.user)

    def post_json(self, name, payload=None):
        return self.client.post(
            reverse(f"accountsReports:{name}"),
            data=json.dumps(payload or {}),
            content_type="application/json",
        )

    @staticmethod
    def cursor_for(mock_connection, *, columns=(), rows=(), row=None):
        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = rows
        cursor.fetchone.return_value = row
        return cursor

    def test_report_requires_login(self):
        url = reverse("accountsReports:detailed_ledger")
        self.client.logout()
        response = self.client.get(url)
        self.assertRedirects(
            response, f'{reverse("authentication:login")}?next={url}'
        )

    def test_report_families_enforce_their_permissions(self):
        report_names = [
            "detailed_ledger", "detailed_ledger2", "cash_ledger",
            "trial_balance", "accounts_receivable", "accounts_payable",
            "stock_report", "stock_summary", "stock__worth_report",
            "item_history", "item_detail", "serial_ledger",
            "serial_ledger_purchase_only", "serial_ledger_with_sold_flag",
            "serial_ledger_sale_only", "items_last_purchasing",
            "items_last_sale", "company_valuation", "sale_wise_report",
            "monthly_position_report", "monthly_income_report",
        ]
        for name in report_names:
            with self.subTest(report=name):
                response = self.client.get(reverse(f"accountsReports:{name}"))
                self.assertRedirects(response, reverse("home:home"))

    def test_authorized_gets_render_each_report_template_family(self):
        cases = [
            (
                "detailed_ledger",
                ("view_accounts_reports_page", "view_detailed_ledger"),
                "display_report_templates/accounts_reports_template.html",
            ),
            (
                "stock_report",
                ("view_stock_reports_page", "view_serial_wise_stock"),
                "display_report_templates/stock_reports_template.html",
            ),
            (
                "company_valuation",
                ("view_company_valuation",),
                "display_report_templates/profit_reports_template.html",
            ),
            (
                "monthly_position_report",
                ("view_sale_wise_profit_report",),
                "display_report_templates/monthly_reports_template.html",
            ),
        ]
        for name, permissions, template in cases:
            with self.subTest(report=name):
                self.grant_permissions(self.user, *permissions)
                response = self.client.get(reverse(f"accountsReports:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    @patch("accountsReports.views.connection")
    def test_detailed_ledger_validates_and_executes_normalized_query(self, connection):
        self.grant_permissions(
            self.user, "view_accounts_reports_page", "view_detailed_ledger"
        )
        missing = self.post_json("detailed_ledger", {"party_name": "Acme"})
        invalid = self.post_json(
            "detailed_ledger",
            {"party_name": "Acme", "from_date": "20-01-01", "to_date": "2020-01-31"},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)

        cursor = self.cursor_for(
            connection,
            columns=("party_name", "balance"),
            rows=(("ACME", 125),),
        )
        response = self.post_json(
            "detailed_ledger",
            {"party_name": "  ACME  ", "from_date": "2020-01-01", "to_date": "2020-01-31"},
        )
        self.assertEqual(response.json(), [{"party_name": "ACME", "balance": 125}])
        cursor.execute.assert_called_once_with(
            "SELECT * FROM detailed_ledger(%s, %s, %s)",
            ["ACME", "2020-01-01", "2020-01-31"],
        )

    @patch("accountsReports.views.connection")
    def test_detailed_ledger2_serializes_dates_and_preserves_json(self, connection):
        self.grant_permissions(
            self.user, "view_accounts_reports_page", "view_detailed_ledger"
        )
        cursor = self.cursor_for(
            connection,
            columns=("txn_date", "invoice_details"),
            rows=((date(2020, 1, 2), {"invoice": 7}),),
        )
        response = self.post_json(
            "detailed_ledger2",
            {"party_name": "ACME", "from_date": "2020-01-01", "to_date": "2020-01-31"},
        )
        self.assertEqual(
            response.json(),
            [{"txn_date": "2020-01-02", "invoice_details": {"invoice": 7}}],
        )
        cursor.execute.assert_called_once_with(
            "SELECT * FROM detailed_ledger2(%s, %s, %s)",
            ["ACME", "2020-01-01", "2020-01-31"],
        )

    @patch("accountsReports.views.connection")
    def test_cash_and_trial_balance_query_contracts(self, connection):
        self.grant_permissions(
            self.user,
            "view_accounts_reports_page", "view_cash_ledger", "view_trial_balance",
        )
        cursor = self.cursor_for(connection, columns=("balance",), rows=((90,),))
        response = self.post_json(
            "cash_ledger", {"from_date": "2020-01-01", "to_date": "2020-01-31"}
        )
        self.assertEqual(response.json(), [{"balance": 90}])
        cursor.execute.assert_called_with(
            "SELECT * FROM get_cash_ledger_with_party(%s, %s)",
            ["2020-01-01", "2020-01-31"],
        )
        cursor.reset_mock()
        self.post_json("trial_balance")
        cursor.execute.assert_called_once_with("SELECT * FROM vw_trial_balance")

    @patch("accountsReports.views.connection")
    def test_receivable_and_payable_return_database_json(self, connection):
        self.grant_permissions(
            self.user, "view_accounts_reports_page", "view_receivable", "view_payable"
        )
        cursor = self.cursor_for(connection, row=([{"party": "ACME", "due": 10}],))
        receivable = self.post_json("accounts_receivable")
        self.assertEqual(receivable.json(), [{"party": "ACME", "due": 10}])
        cursor.execute.assert_called_with(
            "SELECT get_accounts_receivable_json_excluding()"
        )
        cursor.fetchone.return_value = ({"SUPPLIER": 20},)
        payable = self.post_json("accounts_payable")
        self.assertEqual(payable.json(), {"SUPPLIER": 20})
        cursor.execute.assert_called_with("SELECT get_accounts_payable_json_excluding()")

    @patch("accountsReports.views.connection")
    def test_stock_listing_report_query_contracts(self, connection):
        self.grant_permissions(
            self.user,
            "view_stock_reports_page", "view_serial_wise_stock",
            "view_stock_summary", "view_stock_worth_report",
            "view_last_purchasing", "view_last_sale",
        )
        cursor = self.cursor_for(connection, columns=("item",), rows=(("PHONE",),))
        cases = [
            ("stock_report", "SELECT * FROM stock_report"),
            ("stock_summary", "SELECT * FROM stock_summary();"),
            ("stock__worth_report", "SELECT * FROM stock_worth_report"),
            ("items_last_purchasing", "SELECT * FROM item_last_purchase_view"),
            ("items_last_sale", "SELECT * FROM item_last_sale_view"),
        ]
        for name, sql in cases:
            with self.subTest(report=name):
                cursor.reset_mock()
                response = self.post_json(name)
                self.assertEqual(response.json(), [{"item": "PHONE"}])
                cursor.execute.assert_called_once_with(sql)

    @patch("accountsReports.views.connection")
    def test_item_reports_validate_normalize_and_query(self, connection):
        self.grant_permissions(
            self.user, "view_stock_reports_page", "view_item_history", "view_item_detail"
        )
        self.assertEqual(self.post_json("item_detail").status_code, 400)
        self.assertEqual(
            self.post_json(
                "item_history",
                {"item_name": "phone", "from_date": "bad", "to_date": "2020-01-31"},
            ).status_code,
            400,
        )
        cursor = self.cursor_for(connection, columns=("item",), rows=(("PHONE",),))
        history = self.post_json(
            "item_history",
            {"item_name": " phone ", "from_date": "2020-01-01", "to_date": "2020-01-31"},
        )
        self.assertEqual(history.json(), [{"item": "PHONE"}])
        cursor.execute.assert_called_with(
            "SELECT * FROM item_transaction_history(%s,%s, %s)",
            ["PHONE", "2020-01-01", "2020-01-31"],
        )
        self.post_json("item_detail", {"item_name": " phone "})
        cursor.execute.assert_called_with(
            "SELECT * FROM get_item_stock_by_name(%s)", ["PHONE"]
        )

    @patch("accountsReports.views.connection")
    def test_all_serial_ledger_variants_validate_and_query(self, connection):
        self.grant_permissions(
            self.user,
            "view_stock_reports_page", "view_serial_ledger",
            "view_serial_ledger_purchase_only", "view_last_purchasing",
            "view_serial_ledger_sale_only",
        )
        cursor = self.cursor_for(connection, columns=("serial_number",), rows=(("S-1",),))
        cases = [
            ("serial_ledger", "SELECT * FROM get_serial_ledger(%s)"),
            ("serial_ledger_purchase_only", "SELECT * FROM get_serial_ledger_purchase(%s)"),
            (
                "serial_ledger_with_sold_flag",
                "SELECT serial_number, serial_comment, item_name, txn_date, particulars, reference, qty_in, qty_out, balance, party_name, purchase_price FROM get_serial_ledger(%s);",
            ),
            ("serial_ledger_sale_only", "SELECT * FROM get_serial_ledger_sales(%s)"),
        ]
        for name, sql in cases:
            with self.subTest(report=name):
                self.assertEqual(self.post_json(name).status_code, 400)
                cursor.reset_mock()
                response = self.post_json(name, {"serial": " S-1 "})
                self.assertEqual(response.json(), [{"serial_number": "S-1"}])
                cursor.execute.assert_called_once_with(sql, ["S-1"])

    @patch("accountsReports.views.connection")
    def test_company_valuation_returns_json_and_handles_empty_result(self, connection):
        self.grant_permissions(self.user, "view_company_valuation")
        cursor = self.cursor_for(connection, row=({"net_worth": 500},))
        response = self.post_json("company_valuation")
        self.assertEqual(response.json(), {"net_worth": 500})
        cursor.execute.assert_called_once_with("SELECT * FROM standing_company_worth_view")
        cursor.fetchone.return_value = None
        self.assertEqual(self.post_json("company_valuation").status_code, 404)

    @patch("accountsReports.views.connection")
    def test_sale_wise_profit_validates_dates_and_executes_query(self, connection):
        self.grant_permissions(self.user, "view_accounts_reports_page")
        self.assertEqual(
            self.post_json(
                "sale_wise_report", {"from_date": "bad", "to_date": "2020-01-31"}
            ).status_code,
            400,
        )
        cursor = self.cursor_for(connection, columns=("profit",), rows=((35,),))
        response = self.post_json(
            "sale_wise_report", {"from_date": "2020-01-01", "to_date": "2020-01-31"}
        )
        self.assertEqual(response.json(), [{"profit": 35}])
        cursor.execute.assert_called_once_with(
            "SELECT * FROM sale_wise_profit(%s,%s)",
            ["2020-01-01", "2020-01-31"],
        )

    @patch("accountsReports.views.connection")
    def test_monthly_position_validates_queries_and_handles_empty_result(self, connection):
        self.grant_permissions(self.user, "view_sale_wise_profit_report")
        self.assertEqual(
            self.post_json("monthly_position_report", {"as_of_date": "bad"}).status_code,
            400,
        )
        cursor = self.cursor_for(connection, row=({"assets": 100},))
        response = self.post_json(
            "monthly_position_report", {"as_of_date": "2020-01-31"}
        )
        self.assertEqual(response.json(), {"assets": 100})
        cursor.execute.assert_called_once_with(
            "SELECT monthly_company_position(%s)", ["2020-01-31"]
        )
        cursor.fetchone.return_value = (None,)
        self.assertEqual(
            self.post_json(
                "monthly_position_report", {"as_of_date": "2020-01-31"}
            ).status_code,
            404,
        )

    @patch("accountsReports.views.connection")
    def test_monthly_income_validates_numbers_and_executes_float_contract(self, connection):
        self.grant_permissions(self.user, "view_sale_wise_profit_report")
        invalid = self.post_json(
            "monthly_income_report",
            {
                "from_date": "2020-01-01", "to_date": "2020-01-31",
                "sales_revenue": "not-a-number", "cogs": "5",
            },
        )
        self.assertEqual(invalid.status_code, 400)
        cursor = self.cursor_for(connection, row=({"net_income": 75},))
        response = self.post_json(
            "monthly_income_report",
            {
                "from_date": "2020-01-01", "to_date": "2020-01-31",
                "sales_revenue": "100.50", "cogs": 25,
            },
        )
        self.assertEqual(response.json(), {"net_income": 75})
        cursor.execute.assert_called_once_with(
            "SELECT monthly_income_statement(%s, %s, %s, %s)",
            ["2020-01-01", "2020-01-31", 100.5, 25.0],
        )

    def test_report_rejects_unsupported_method(self):
        self.grant_permissions(
            self.user, "view_accounts_reports_page", "view_trial_balance"
        )
        response = self.client.put(reverse("accountsReports:trial_balance"))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"error": "Method not allowed"})
