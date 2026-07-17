#!/usr/bin/env python3
"""Disposable PostgreSQL integration suite for Financee accounting workflows."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("psycopg2 is required; run: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "db_backup_20260703_0000.sql"
RESULTS = Path(__file__).resolve().parent / "RESULTS.md"
DB_PREFIX = "financee_test_"


@dataclass
class Result:
    group: str
    name: str
    expected: str
    passed: bool
    detail: str
    seconds: float


class Suite:
    def __init__(self, conn, run_id: str):
        self.conn = conn
        self.run_id = run_id
        self.results: list[Result] = []
        self.ids: dict[str, int] = {}
        self.names = {
            "vendor": f"TEST_{run_id}_VENDOR_A",
            "wrong_vendor": f"TEST_{run_id}_VENDOR_B",
            "customer": f"TEST_{run_id}_CUSTOMER_A",
            "wrong_customer": f"TEST_{run_id}_CUSTOMER_B",
            "expense": f"TEST_{run_id}_EXPENSE",
            "cash": f"TEST_{run_id}_CASH_SALE",
            "item_a": f"TEST_{run_id}_ITEM_A",
            "item_b": f"TEST_{run_id}_ITEM_B",
        }
        self.serial_no = 0

    def serials(self, label: str, count: int) -> list[str]:
        values = []
        for _ in range(count):
            self.serial_no += 1
            values.append(f"TEST-{self.run_id}-{label}-{self.serial_no:03d}")
        return values

    def query(self, statement: str, params=(), one=False):
        with self.conn.cursor() as cur:
            cur.execute(statement, params)
            if cur.description is None:
                return None
            return cur.fetchone() if one else cur.fetchall()

    @contextmanager
    def savepoint(self):
        marker = f"sp_{time.time_ns()}"
        self.query(f"SAVEPOINT {marker}")
        try:
            yield
        except Exception:
            self.query(f"ROLLBACK TO SAVEPOINT {marker}")
            self.query(f"RELEASE SAVEPOINT {marker}")
            raise
        else:
            self.query(f"RELEASE SAVEPOINT {marker}")

    def case(self, group: str, name: str, expected: str, fn: Callable[[], Any]):
        started = time.monotonic()
        try:
            detail = fn()
            passed = True
            detail = "Passed" if detail is None else str(detail)
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            passed = False
            detail = f"{type(exc).__name__}: {exc}"
        self.results.append(Result(group, name, expected, passed, detail, time.monotonic() - started))
        return passed

    def assert_true(self, condition: bool, detail: str):
        if not condition:
            raise AssertionError(detail)
        return detail

    def expect_blocked(self, action: Callable[[], Any], contains: str | None = None):
        try:
            with self.savepoint():
                action()
        except Exception as exc:
            message = str(exc)
            if contains and contains.lower() not in message.lower():
                raise AssertionError(f"Blocked for an unexpected reason: {message}") from exc
            return f"Blocked as expected: {message.splitlines()[0]}"
        raise AssertionError("Operation unexpectedly succeeded")

    def party(self, key: str, party_type: str):
        payload = {"party_name": self.names[key], "party_type": party_type,
                   "opening_balance": 0, "balance_type": "Debit"}
        self.query("SELECT add_party_from_json(%s::jsonb)", (json.dumps(payload),))
        row = self.query("SELECT party_id FROM parties WHERE party_name=%s", (self.names[key],), one=True)
        self.ids[key] = row[0]

    def item(self, key: str, price: float):
        payload = {"item_name": self.names[key], "storage": "Test Warehouse",
                   "sale_price": price, "item_code": f"{self.run_id}-{key}"}
        self.query("SELECT add_item_from_json(%s::jsonb)", (json.dumps(payload),))
        self.ids[key] = self.query("SELECT item_id FROM items WHERE item_name=%s", (self.names[key],), one=True)[0]

    def purchase(self, serials: list[str], item="item_a", price=100.0, vendor="vendor") -> int:
        payload = [{"item_name": self.names[item], "qty": len(serials), "unit_price": price,
                    "serials": [{"serial": s, "comment": "system test"} for s in serials]}]
        return self.query("SELECT create_purchase(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids[vendor], date.today(), json.dumps(payload), None), one=True)[0]

    def purchase_multi(self, groups: list[tuple[str, list[str], float]]) -> int:
        payload = [{"item_name": self.names[item], "qty": len(values), "unit_price": price,
                    "serials": [{"serial": s, "comment": "system test"} for s in values]}
                   for item, values, price in groups]
        return self.query("SELECT create_purchase(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids["vendor"], date.today(), json.dumps(payload), None), one=True)[0]

    def sale(self, groups: list[tuple[str, list[str], float]], customer="customer",
             quantities: list[int] | None = None) -> int:
        payload = []
        for index, (item, values, price) in enumerate(groups):
            qty = quantities[index] if quantities else len(values)
            payload.append({"item_name": self.names[item], "qty": qty,
                            "unit_price": price, "serials": values})
        return self.query("SELECT create_sale(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids[customer], date.today(), json.dumps(payload), None), one=True)[0]

    def sale_return(self, serials: list[str], customer="customer") -> int:
        return self.query("SELECT create_sale_return(%s::text,%s::jsonb,%s::integer)",
                          (self.names[customer], json.dumps(serials), None), one=True)[0]

    def purchase_return(self, serials: list[str], vendor="vendor") -> int:
        return self.query("SELECT create_purchase_return(%s::text,%s::jsonb,%s::integer)",
                          (self.names[vendor], json.dumps(serials), None), one=True)[0]

    def stock(self, serial: str) -> bool:
        row = self.query("SELECT in_stock FROM purchaseunits WHERE serial_number=%s", (serial,), one=True)
        if not row:
            raise AssertionError(f"Serial {serial} is missing")
        return row[0]

    def active_sales(self, serial: str) -> int:
        return self.query("""SELECT count(*) FROM soldunits su JOIN purchaseunits pu ON pu.unit_id=su.unit_id
                             WHERE pu.serial_number=%s AND su.status='Sold'""", (serial,), one=True)[0]

    def checkpoint(self, label: str):
        empty = self.query("""SELECT count(*) FROM journalentries je
                              LEFT JOIN journallines jl ON jl.journal_id=je.journal_id
                              WHERE jl.line_id IS NULL""", one=True)[0]
        duplicate = self.query("""SELECT count(*) FROM (SELECT pu.serial_number
                                  FROM soldunits su JOIN purchaseunits pu ON pu.unit_id=su.unit_id
                                  WHERE pu.serial_number LIKE %s AND su.status='Sold'
                                  GROUP BY pu.serial_number HAVING count(*) > 1) q""",
                               (f"TEST-{self.run_id}-%",), one=True)[0]
        if empty or duplicate:
            raise AssertionError(f"empty journals={empty}, serials with multiple active sales={duplicate}")
        self.run_reports()
        return "Reports executed; no empty journals or duplicate active sold states"

    def run_reports(self):
        start, end = date(2020, 1, 1), date.today()
        calls = [
            ("accounts: trial balance", "SELECT * FROM vw_trial_balance", ()),
            ("accounts: detailed ledger", "SELECT * FROM detailed_ledger(%s,%s,%s)", (self.names["customer"], start, end)),
            ("accounts: detailed ledger 2", "SELECT * FROM detailed_ledger2(%s,%s,%s)", (self.names["customer"], start, end)),
            ("accounts: cash ledger", "SELECT * FROM get_cash_ledger_with_party(%s,%s)", (start, end)),
            ("accounts: receivables", "SELECT get_accounts_receivable_json_excluding()", ()),
            ("accounts: payables", "SELECT get_accounts_payable_json_excluding()", ()),
            ("stock: summary", "SELECT * FROM stock_summary()", ()),
            ("stock: serial ledger", "SELECT * FROM get_serial_ledger(%s)", (f"TEST-{self.run_id}-NO-SERIAL",)),
            ("stock: purchase serial ledger", "SELECT * FROM get_serial_ledger_purchase(%s)", (f"TEST-{self.run_id}-NO-SERIAL",)),
            ("stock: sales serial ledger", "SELECT * FROM get_serial_ledger_sales(%s)", (f"TEST-{self.run_id}-NO-SERIAL",)),
            ("stock: item history", "SELECT * FROM item_history_view LIMIT 1", ()),
            ("sales: summary", "SELECT get_sales_summary(%s,%s)", (start, end)),
            ("sales: profit", "SELECT * FROM sale_wise_profit(%s,%s)", (start, end)),
            ("sales: company valuation", "SELECT * FROM standing_company_worth_view", ()),
            ("sales: returns", "SELECT get_sales_return_summary(%s,%s)", (start, end)),
            ("purchase: summary", "SELECT get_purchase_summary(%s,%s)", (start, end)),
            ("purchase: returns", "SELECT get_purchase_return_summary(%s,%s)", (start, end)),
            ("monthly: position", "SELECT monthly_company_position(%s)", (date.today(),)),
            ("monthly: income", "SELECT monthly_income_statement(%s,%s,%s,%s)", (start, end, 0, 0)),
            ("dashboard: sales today", "SELECT fn_dash_sales_today_kpi()", ()),
            ("dashboard: sales range", "SELECT fn_dash_sales_range(%s,%s)", (start, end)),
            ("dashboard: sales 7 days", "SELECT fn_dash_sales_last7days()", ()),
            ("dashboard: stock KPI", "SELECT fn_dash_stock_kpi()", ()),
            ("dashboard: low stock", "SELECT fn_dash_low_stock_items()", ()),
            ("dashboard: fast stock", "SELECT fn_dash_fast_moving_items()", ()),
            ("dashboard: stale stock", "SELECT fn_dash_stale_stock()", ()),
            ("dashboard: customers", "SELECT fn_dash_top_customers()", ()),
            ("dashboard: vendors", "SELECT fn_dash_top_vendors()", ()),
            ("dashboard: aging", "SELECT fn_dash_receivables_aging()", ()),
            ("dashboard: recent", "SELECT fn_dash_recent_transactions()", ()),
            ("dashboard: expenses", "SELECT fn_dash_expense_kpi()", ()),
            ("dashboard: alerts", "SELECT fn_dash_smart_alerts()", ()),
            ("legacy: parties", "SELECT get_parties_json()", ()),
            ("legacy: items", "SELECT get_items_json()", ()),
            ("legacy: balances", "SELECT get_party_balances_json()", ()),
            ("legacy: expenses", "SELECT get_expense_party_balances_json()", ()),
        ]
        failures = []
        for label, statement, params in calls:
            try:
                with self.savepoint():
                    self.query(statement, params)
            except Exception as exc:
                failures.append(f"{label}: {str(exc).splitlines()[0]}")
        if failures:
            raise AssertionError("; ".join(failures))

    def setup(self):
        for key, kind in (("vendor", "Vendor"), ("wrong_vendor", "Vendor"),
                          ("customer", "Customer"), ("wrong_customer", "Customer"),
                          ("expense", "Expense"), ("cash", "Customer")):
            self.party(key, kind)
        self.item("item_a", 150)
        self.item("item_b", 250)
        return self.assert_true(len(self.ids) == 8, "Six parties and two items created")

    def run(self):
        G = "Master Data and Reports"
        self.case(G, "Create required master data", "All required parties and items are available", self.setup)
        self.case(G, "Run all report groups after setup", "Every report executes", lambda: (self.run_reports(), "All report calls executed")[1])

        G = "Basic Purchase, Sale and Return Lifecycle"
        s = self.serials("LIFE", 4)
        self.case(G, "Purchase four serials", "All are in stock", lambda: self.assert_true(bool(self.purchase(s)) and all(self.stock(x) for x in s), "Four serials are in stock"))
        self.case(G, "Sell serial 1", "Serial becomes sold", lambda: self.assert_true(bool(self.sale([("item_a", [s[0]], 180)])) and not self.stock(s[0]), "Serial is sold"))
        self.case(G, "Attempt duplicate sale", "Blocked", lambda: self.expect_blocked(lambda: self.sale([("item_a", [s[0]], 180)])))
        self.case(G, "Return with wrong customer", "Blocked", lambda: self.expect_blocked(lambda: self.sale_return([s[0]], "wrong_customer")))
        self.case(G, "Return with correct customer", "Serial returns to stock", lambda: self.assert_true(bool(self.sale_return([s[0]])) and self.stock(s[0]), "Valid return succeeded"))
        self.case(G, "Attempt duplicate return", "Blocked", lambda: self.expect_blocked(lambda: self.sale_return([s[0]])))
        self.case(G, "Resell returned serial", "Serial becomes sold", lambda: self.assert_true(bool(self.sale([("item_a", [s[0]], 185)])) and not self.stock(s[0]), "Resale succeeded"))
        self.case(G, "Return after resale", "Second return succeeds", lambda: self.assert_true(bool(self.sale_return([s[0]])) and self.stock(s[0]), "Second return succeeded"))
        self.case(G, "Purchase return with wrong vendor", "Blocked", lambda: self.expect_blocked(lambda: self.purchase_return([s[0]], "wrong_vendor")))
        self.case(G, "Purchase-return after lifecycle", "Serial unavailable", lambda: self.assert_true(bool(self.purchase_return([s[0]])) and not self.stock(s[0]), "Purchase return succeeded"))
        self.case(G, "Sell purchase-returned serial", "Blocked", lambda: self.expect_blocked(lambda: self.sale([("item_a", [s[0]], 190)])))
        self.case("Continuous Integrity and Reporting", "Lifecycle checkpoint", "Reports and integrity pass", lambda: self.checkpoint("lifecycle"))

        G = "Purchase Invoice Update Tests"
        u = self.serials("PUPDATE", 5); original, replacement = u[:4], u[4]
        state: dict[str, Any] = {}
        self.case(G, "Create mixed-state purchase", "Invoice created", lambda: state.setdefault("purchase", self.purchase(original)))
        self.case(G, "Sell one mixed-state serial", "Serial sold", lambda: self.assert_true(bool(self.sale([("item_a", [original[0]], 190)])) and not self.stock(original[0]), "Sold state created"))

        def purchase_payload(values, price):
            return [{"item_name": self.names["item_a"], "qty": len(values), "unit_price": price,
                     "serials": [{"serial": x, "comment": "updated"} for x in values]}]
        price_json = json.dumps(purchase_payload(original, 120))
        repl_values = [original[0], replacement, original[2], original[3]]
        repl_json = json.dumps(purchase_payload(repl_values, 120))
        remove_sold_json = json.dumps(purchase_payload(original[1:], 120))
        self.case(G, "Validate price-only update", "Permitted", lambda: self.assert_true(self.query("SELECT validate_purchase_update2(%s,%s::jsonb)", (state["purchase"], price_json), one=True)[0]["is_valid"], "Validation permitted"))
        self.case(G, "Apply price-only update", "Sold state preserved", lambda: (self.query("SELECT update_purchase_invoice(%s::bigint,%s::jsonb,%s::text,%s::date,%s::integer)", (state["purchase"], price_json, None, None, None)), self.assert_true(not self.stock(original[0]), "Price updated and sold state preserved"))[1])
        self.case(G, "Validate unsold replacement", "Permitted", lambda: self.assert_true(self.query("SELECT validate_purchase_update2(%s,%s::jsonb)", (state["purchase"], repl_json), one=True)[0]["is_valid"], "Replacement permitted"))
        self.case(G, "Replace unsold serial", "Old removed and new stocked", lambda: (self.query("SELECT update_purchase_invoice(%s::bigint,%s::jsonb,%s::text,%s::date,%s::integer)", (state["purchase"], repl_json, None, None, None)), self.assert_true(self.query("SELECT count(*) FROM purchaseunits WHERE serial_number=%s", (original[1],), one=True)[0] == 0 and self.stock(replacement), "Replacement applied"))[1])
        self.case(G, "Validate removal of sold serial", "Blocked and identifies serial", lambda: self.assert_true(not self.query("SELECT validate_purchase_update2(%s,%s::jsonb)", (state["purchase"], remove_sold_json), one=True)[0]["is_valid"], "Sold serial identified"))
        self.case(G, "Apply update removing sold serial", "Blocked", lambda: self.expect_blocked(lambda: self.query("SELECT update_purchase_invoice(%s::bigint,%s::jsonb,%s::text,%s::date,%s::integer)", (state["purchase"], remove_sold_json, None, None, None))))
        self.case(G, "Purchase-return replacement", "Replacement unavailable", lambda: self.assert_true(bool(self.purchase_return([replacement])) and not self.stock(replacement), "Replacement returned"))
        self.case("Continuous Integrity and Reporting", "Purchase-update checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("purchase update"))

        G = "Partial Sale Return Tests"
        p = self.serials("PARTIAL", 4); st = {}
        self.case(G, "Purchase four serials", "Stock created", lambda: self.assert_true(bool(self.purchase(p)) and all(self.stock(x) for x in p), "Stock created"))
        self.case(G, "Sell four serials", "All sold", lambda: (st.setdefault("sale", self.sale([("item_a", p, 200)])), self.assert_true(all(not self.stock(x) for x in p), "All sold"))[1])
        self.case(G, "Return two serials", "Two in stock and two sold", lambda: (st.setdefault("return", self.sale_return(p[:2])), self.assert_true(all(self.stock(x) for x in p[:2]) and all(not self.stock(x) for x in p[2:]), "Partial return correct"))[1])
        sale_json = json.dumps([{"item_name": self.names["item_a"], "qty": 4, "unit_price": 205, "serials": p}])
        self.case(G, "Update sale after return", "Blocked", lambda: self.assert_true(not self.query("SELECT validate_sales_update(%s,%s::jsonb)", (st["sale"], sale_json), one=True)[0]["is_valid"], "Update validation blocked"))
        self.case(G, "Delete sale after return", "Blocked", lambda: self.assert_true(not self.query("SELECT validate_sales_delete(%s)", (st["sale"],), one=True)[0]["is_valid"], "Delete validation blocked"))
        self.case(G, "Update return from two to one", "Removed sold; retained stocked", lambda: (self.query("SELECT update_sale_return(%s::bigint,%s::jsonb,%s::integer)", (st["return"], json.dumps([p[0]]), None)), self.assert_true(self.stock(p[0]) and not self.stock(p[1]), "Return updated correctly"))[1])
        self.case(G, "Delete return before resale", "Affected serial sold", lambda: (self.query("SELECT delete_sale_return(%s)", (st["return"],)), self.assert_true(not self.stock(p[0]), "Return deleted and serial sold"))[1])
        self.case("Continuous Integrity and Reporting", "Partial-return checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("partial return"))

        G = "Sale Return Mutation After Resale"
        r = self.serials("RESALE", 1); rs = {}
        self.case(G, "Purchase resale serial", "Stock created", lambda: self.purchase(r))
        self.case(G, "Credit-sell and return", "Return succeeds", lambda: (self.sale([("item_a", r, 210)]), rs.setdefault("return", self.sale_return(r)), self.assert_true(self.stock(r[0]), "Returned"))[2])
        self.case(G, "Resell returned serial", "Resale succeeds", lambda: self.assert_true(bool(self.sale([("item_a", r, 215)])) and not self.stock(r[0]), "Resold"))
        self.case(G, "Delete old return after resale", "Blocked", lambda: self.expect_blocked(lambda: self.query("SELECT delete_sale_return(%s)", (rs["return"],))))
        self.case(G, "Update old return after resale", "Blocked", lambda: self.expect_blocked(lambda: self.query("SELECT update_sale_return(%s::bigint,%s::jsonb,%s::integer)", (rs["return"], json.dumps(r), None))))
        self.case("Continuous Integrity and Reporting", "Resale-mutation checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("resale mutation"))

        G = "Multi-Item Sale and Return Tests"
        a, b = self.serials("MULTIA", 3), self.serials("MULTIB", 3); ms = {}
        self.case(G, "Purchase two-item stock", "Stock created", lambda: self.purchase_multi([("item_a", a, 100), ("item_b", b, 200)]))
        self.case(G, "Sell six across two items", "All sold", lambda: (ms.setdefault("sale", self.sale([("item_a", a, 170), ("item_b", b, 280)])), self.assert_true(all(not self.stock(x) for x in a+b), "All six sold"))[1])
        self.case(G, "Return one from each item", "Mixed return succeeds", lambda: (ms.setdefault("return", self.sale_return([a[0], b[0]])), self.assert_true(self.stock(a[0]) and self.stock(b[0]), "Mixed return succeeded"))[1])
        self.case(G, "Duplicate mixed return", "Blocked", lambda: self.expect_blocked(lambda: self.sale_return([a[0], b[0]])))
        self.case(G, "Update mixed return", "Old sold and new stocked", lambda: (self.query("SELECT update_sale_return(%s::bigint,%s::jsonb,%s::integer)", (ms["return"], json.dumps([a[1], b[1]]), None)), self.assert_true(not self.stock(a[0]) and not self.stock(b[0]) and self.stock(a[1]) and self.stock(b[1]), "Mixed return changed"))[1])
        multi_json = json.dumps([{"item_name": self.names["item_a"], "qty": 3, "unit_price": 170, "serials": a}, {"item_name": self.names["item_b"], "qty": 3, "unit_price": 280, "serials": b}])
        self.case(G, "Update multi-item sale after return", "Blocked", lambda: self.assert_true(not self.query("SELECT validate_sales_update(%s,%s::jsonb)", (ms["sale"], multi_json), one=True)[0]["is_valid"], "Update blocked"))
        self.case(G, "Delete multi-item sale after return", "Blocked", lambda: self.assert_true(not self.query("SELECT validate_sales_delete(%s)", (ms["sale"],), one=True)[0]["is_valid"], "Delete blocked"))
        self.case("Continuous Integrity and Reporting", "Multi-item checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("multi item"))

        G = "Additional Serious Scenarios"
        untouched = self.serials("DELETEOK", 2); sold = self.serials("DELETEBLOCK", 1)
        holder = {}
        self.case(G, "Delete untouched purchase", "Deletion succeeds", lambda: (holder.setdefault("p", self.purchase(untouched)), self.query("SELECT delete_purchase(%s)", (holder["p"],)), self.assert_true(self.query("SELECT count(*) FROM purchaseinvoices WHERE purchase_invoice_id=%s", (holder["p"],), one=True)[0] == 0, "Untouched purchase deleted"))[2])
        self.case(G, "Delete purchase containing sold serial", "Blocked", lambda: (holder.setdefault("soldp", self.purchase(sold)), self.sale([("item_a", sold, 180)]), self.assert_true(not self.query("SELECT validate_purchase_delete(%s)", (holder["soldp"],), one=True)[0]["is_valid"], "Deletion validation blocked"))[2])
        qty_more = self.serials("QTYMORE", 2)
        qty_less = self.serials("QTYLESS", 2)
        duplicate = self.serials("DUPLICATE", 1)
        negative = self.serials("NEGATIVE", 1)
        self.purchase(qty_more); self.purchase(qty_less); self.purchase(duplicate); self.purchase(negative)
        self.conn.commit()
        self.case(G, "Sale qty greater than serial count", "Rejected", lambda: self.expect_blocked(lambda: self.sale([("item_a", qty_more, 180)], quantities=[5])))
        self.case(G, "Sale qty less than serial count", "Rejected", lambda: self.expect_blocked(lambda: self.sale([("item_a", qty_less, 180)], quantities=[1])))
        self.case(G, "Duplicate serial in one sale", "Rejected", lambda: self.expect_blocked(lambda: self.sale([("item_a", [duplicate[0], duplicate[0]], 180)])))
        self.case(G, "Negative sale price", "Rejected", lambda: self.expect_blocked(lambda: self.sale([("item_a", negative, -1)])))

        cost = self.serials("COST", 1); cost_state = {}
        self.case(G, "Correct purchase cost then sale-return", "Return cost uses corrected cost", lambda: self._cost_basis_test(cost, cost_state))
        cross1, cross2 = self.serials("CROSS", 1), self.serials("CROSS", 1)
        self.case(G, "One return across two sale invoices", "Both return to stock", lambda: (self.purchase(cross1+cross2), self.sale([("item_a", cross1, 180)]), self.sale([("item_a", cross2, 185)]), self.sale_return(cross1+cross2), self.assert_true(self.stock(cross1[0]) and self.stock(cross2[0]), "Cross-invoice return succeeded"))[4])
        self.case("Continuous Integrity and Reporting", "Serious-scenarios checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("serious scenarios"))

        G = "Financial Invariant Tests"
        self.case(G, "Double-entry identity", "Debits equal credits", lambda: self._double_entry())
        self.case(G, "No orphaned journal lines", "No orphan exists", lambda: self.assert_true(self.query("SELECT count(*) FROM journallines jl LEFT JOIN journalentries je ON je.journal_id=jl.journal_id WHERE je.journal_id IS NULL", one=True)[0] == 0, "No orphaned lines"))
        self.case(G, "Debit and credit signs", "No negative values", lambda: self.assert_true(self.query("SELECT count(*) FROM journallines WHERE debit<0 OR credit<0", one=True)[0] == 0, "No negative debit/credit"))
        self.case(G, "Stock and sold coherence", "Stock matches active sold state", self._stock_coherence)
        self.case("Continuous Integrity and Reporting", "Final checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("final"))

    def _cost_basis_test(self, values, state):
        state["purchase"] = self.purchase(values, price=100)
        self.sale([("item_a", values, 175)])
        payload = [{"item_name": self.names["item_a"], "qty": 1, "unit_price": 130,
                    "serials": [{"serial": values[0], "comment": "corrected"}]}]
        self.query("SELECT update_purchase_invoice(%s::bigint,%s::jsonb,%s::text,%s::date,%s::integer)", (state["purchase"], json.dumps(payload), None, None, None))
        return_id = self.sale_return(values)
        cost = self.query("SELECT cost_price FROM salesreturnitems WHERE sales_return_id=%s", (return_id,), one=True)[0]
        return self.assert_true(float(cost) == 130.0, f"Return cost basis is {cost}")

    def _double_entry(self):
        debit, credit = self.query("SELECT COALESCE(sum(debit),0),COALESCE(sum(credit),0) FROM journallines", one=True)
        return self.assert_true(debit == credit, f"debit={debit}, credit={credit}")

    def _stock_coherence(self):
        bad = self.query("""SELECT count(*) FROM purchaseunits pu
                            WHERE pu.serial_number LIKE %s AND
                            ((pu.in_stock AND EXISTS (SELECT 1 FROM soldunits su WHERE su.unit_id=pu.unit_id AND su.status='Sold'))
                             OR (NOT pu.in_stock AND EXISTS (SELECT 1 FROM soldunits su WHERE su.unit_id=pu.unit_id AND su.status='Sold') = FALSE
                                 AND NOT EXISTS (SELECT 1 FROM purchasereturnitems pri WHERE pri.serial_number=pu.serial_number)))""",
                         (f"TEST-{self.run_id}-%",), one=True)[0]
        return self.assert_true(bad == 0, f"Incoherent tested serials={bad}")


def local_host(host: str) -> bool:
    return host in ("", "localhost", "127.0.0.1", "::1") or host.startswith("/")


def admin_kwargs():
    return {"host": os.getenv("TEST_PGHOST", "localhost"),
            "port": int(os.getenv("TEST_PGPORT", "5432")),
            "user": os.getenv("TEST_PGUSER", "postgres"),
            "password": os.getenv("TEST_PGPASSWORD", ""),
            "dbname": os.getenv("TEST_PGADMIN_DB", "postgres")}


def create_database(kwargs, name: str):
    if not local_host(kwargs["host"]):
        raise RuntimeError("Refusing a non-local TEST_PGHOST")
    admin = psycopg2.connect(**kwargs); admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(name)))
    finally:
        admin.close()


def drop_database(kwargs, name: str):
    if not name.startswith(DB_PREFIX):
        raise RuntimeError("Refusing to drop a database without the test prefix")
    admin = psycopg2.connect(**kwargs); admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()", (name,))
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))
    finally:
        admin.close()


def restore(kwargs, name: str):
    env = os.environ.copy()
    if kwargs["password"]:
        env["PGPASSWORD"] = kwargs["password"]
    # The production-origin dump assigns every object to a role named
    # ``postgres``. Local Homebrew installations commonly use the macOS account
    # name instead, so remap ownership in-memory without modifying the backup or
    # creating a cluster-wide compatibility role.
    owner = '"' + str(kwargs["user"]).replace('"', '""') + '"'
    dump_sql = BACKUP.read_text(encoding="utf-8").replace("OWNER TO postgres", f"OWNER TO {owner}")
    command = ["psql", "--host", kwargs["host"], "--port", str(kwargs["port"]),
               "--username", kwargs["user"], "--dbname", name, "--set", "ON_ERROR_STOP=1",
               "--file", "-"]
    completed = subprocess.run(command, env=env, text=True, input=dump_sql, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f"Backup restore failed:\n{completed.stderr[-4000:]}")


def write_report(db_name: str, suite: Suite | None, fatal: str | None, kept: bool):
    now = time.strftime("%Y-%m-%d %H:%M:%S %z")
    results = suite.results if suite else []
    passed = sum(r.passed for r in results); failed = len(results) - passed
    lines = ["# Financee System Test Results", "", f"Generated: `{now}`", "",
             f"Temporary database: `{db_name}` ({'kept' if kept else 'removed'})", "",
             f"Summary: **{passed} passed, {failed} failed, {len(results)} total**", ""]
    if fatal:
        lines += ["## Environment failure", "", "```text", fatal, "```", ""]
    current = None
    for result in results:
        if result.group != current:
            current = result.group; lines += [f"## {current}", "", "| Status | Test | Expected | Detail | Time |", "|---|---|---|---|---:|"]
        clean = result.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {'PASS' if result.passed else 'FAIL'} | {result.name} | {result.expected} | {clean} | {result.seconds:.3f}s |")
    lines += ["", "## Notes", "", "- Expected-error cases pass only when PostgreSQL rejects the operation.",
              "- Report checkpoints invoke accounts, stock, monthly, sales, purchase, dashboard, and legacy report functions.",
              "- Tests use uniquely prefixed fixtures and run only in the disposable database.", ""]
    RESULTS.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-db", action="store_true", help="keep the disposable database for inspection")
    args = parser.parse_args()
    run_id = time.strftime("%Y%m%d%H%M%S") + str(os.getpid())
    db_name = DB_PREFIX + run_id.lower()
    kwargs = admin_kwargs(); suite = None; fatal = None; created = False
    try:
        if not BACKUP.exists():
            raise RuntimeError(f"Backup not found: {BACKUP}")
        create_database(kwargs, db_name); created = True
        restore(kwargs, db_name)
        test_kwargs = dict(kwargs, dbname=db_name)
        conn = psycopg2.connect(**test_kwargs); conn.autocommit = False
        try:
            suite = Suite(conn, run_id); suite.run(); conn.commit()
        finally:
            conn.close()
    except Exception:
        fatal = traceback.format_exc()
    finally:
        if created and not args.keep_db:
            try:
                drop_database(kwargs, db_name)
            except Exception:
                fatal = (fatal or "") + "\nDatabase cleanup failed:\n" + traceback.format_exc()
        write_report(db_name, suite, fatal, bool(created and args.keep_db))
    failed = fatal is not None or suite is None or any(not r.passed for r in suite.results)
    print(f"Results written to {RESULTS}")
    if suite:
        print(f"{sum(r.passed for r in suite.results)} passed, {sum(not r.passed for r in suite.results)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
