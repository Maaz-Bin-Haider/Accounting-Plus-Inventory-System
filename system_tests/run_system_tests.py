#!/usr/bin/env python3
"""Disposable PostgreSQL integration suite for Financee accounting workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
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
_BACKUPS = sorted(ROOT.glob("db_backup_*.sql"))
BACKUP = _BACKUPS[-1] if _BACKUPS else ROOT / "db_backup_missing.sql"
FIXES = ROOT / "production_fixes.sql"
RESULTS = Path(__file__).resolve().parent / "RESULTS.md"
DB_PREFIX = "financee_test_"
FIXES_SHA256 = hashlib.sha256(FIXES.read_bytes()).hexdigest() if FIXES.exists() else ""
FIXTURE_DATE = date(2026, 1, 15)
REPORT_END_DATE = date(2099, 12, 31)
CORE_ACCOUNTS = (
    "Accounts Payable",
    "Owner's Capital",
    "Sales Revenue",
    "Cost of Goods Sold",
    "Cash",
    "Accounts Receivable",
    "Inventory",
)

REGRESSION_CASES = {
    1: "Attempt duplicate return",
    2: "Update sale after return",
    3: "Delete old return after resale",
    4: "Update old return after resale",
    5: "Duplicate mixed return",
    6: "Update multi-item sale after return",
    7: "Sale qty greater than serial count",
    8: "Sale qty less than serial count",
    9: "Race two sales for one serial",
}


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
            detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
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

    def opening_party(self, label: str, party_type: str, amount: float,
                      balance_type: str) -> tuple[int, str]:
        name = f"TEST_{self.run_id}_OPENING_{label}"
        payload = {"party_name": name, "party_type": party_type,
                   "opening_balance": amount, "balance_type": balance_type}
        self.query("SELECT add_party_from_json(%s::jsonb)", (json.dumps(payload),))
        row = self.query(
            "SELECT party_id FROM parties WHERE party_name=%s", (name,), one=True
        )
        self.assert_true(row is not None, f"opening party was not inserted: {name}")
        party_id = row[0]
        return party_id, name

    def opening_journal(self, party_id: int):
        rows = self.query(
            """SELECT je.journal_id,jl.party_id,jl.debit,jl.credit
               FROM journalentries je JOIN journallines jl USING (journal_id)
               WHERE je.description ILIKE 'Opening Balance for%%'
                 AND je.journal_id IN (
                     SELECT journal_id FROM journallines WHERE party_id=%s)
               ORDER BY je.journal_id,jl.line_id""",
            (party_id,),
        )
        journal_ids = {row[0] for row in rows}
        self.assert_true(len(journal_ids) == 1,
                         f"opening journals={sorted(journal_ids)}")
        return next(iter(journal_ids)), [row[1:] for row in rows]

    def assert_opening_journal(self, party_id: int, amount: float,
                               party_on_debit: bool):
        journal_id, lines = self.opening_journal(party_id)
        expected = (
            {(party_id, float(amount), 0.0), (None, 0.0, float(amount))}
            if party_on_debit
            else {(None, float(amount), 0.0), (party_id, 0.0, float(amount))}
        )
        actual = {(party, float(debit), float(credit))
                  for party, debit, credit in lines}
        return self.assert_true(
            len(lines) == 2 and actual == expected,
            f"journal={journal_id}, lines={actual}",
        )

    def item(self, key: str, price: float):
        payload = {"item_name": self.names[key], "storage": "Test Warehouse",
                   "sale_price": price, "item_code": f"{self.run_id}-{key}"}
        self.query("SELECT add_item_from_json(%s::jsonb)", (json.dumps(payload),))
        self.ids[key] = self.query("SELECT item_id FROM items WHERE item_name=%s", (self.names[key],), one=True)[0]

    def purchase(self, serials: list[str], item="item_a", price=100.0, vendor="vendor") -> int:
        payload = [{"item_name": self.names[item], "qty": len(serials), "unit_price": price,
                    "serials": [{"serial": s, "comment": "system test"} for s in serials]}]
        return self.query("SELECT create_purchase(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids[vendor], FIXTURE_DATE, json.dumps(payload), None), one=True)[0]

    def purchase_multi(self, groups: list[tuple[str, list[str], float]]) -> int:
        payload = [{"item_name": self.names[item], "qty": len(values), "unit_price": price,
                    "serials": [{"serial": s, "comment": "system test"} for s in values]}
                   for item, values, price in groups]
        return self.query("SELECT create_purchase(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids["vendor"], FIXTURE_DATE, json.dumps(payload), None), one=True)[0]

    def sale(self, groups: list[tuple[str, list[str], float]], customer="customer",
             quantities: list[int] | None = None) -> int:
        payload = []
        for index, (item, values, price) in enumerate(groups):
            qty = quantities[index] if quantities else len(values)
            payload.append({"item_name": self.names[item], "qty": qty,
                            "unit_price": price, "serials": values})
        return self.query("SELECT create_sale(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                          (self.ids[customer], FIXTURE_DATE, json.dumps(payload), None), one=True)[0]

    def sale_return(self, serials: list[str], customer="customer") -> int:
        return self.query("SELECT create_sale_return(%s::text,%s::jsonb,%s::integer)",
                          (self.names[customer], json.dumps(serials), None), one=True)[0]

    def purchase_return(self, serials: list[str], vendor="vendor") -> int:
        return self.query("SELECT create_purchase_return(%s::text,%s::jsonb,%s::integer)",
                          (self.names[vendor], json.dumps(serials), None), one=True)[0]

    def payment(self, amount=125.0) -> int:
        payload = {"party_name": self.names["vendor"], "amount": amount,
                   "payment_date": str(FIXTURE_DATE), "method": "Cash",
                   "reference_no": f"TEST-PMT-{self.run_id}",
                   "description": "System test payment"}
        return self.query("SELECT make_payment(%s::jsonb)",
                          (json.dumps(payload),), one=True)[0]["payment_id"]

    def receipt(self, amount=175.0) -> int:
        payload = {"party_name": self.names["customer"], "amount": amount,
                   "receipt_date": str(FIXTURE_DATE), "method": "Cash",
                   "reference_no": f"TEST-RCT-{self.run_id}",
                   "description": "System test receipt"}
        return self.query("SELECT make_receipt(%s::jsonb)",
                          (json.dumps(payload),), one=True)[0]["receipt_id"]

    def contra(self, amount=80.0) -> int:
        payload = {"from_party_name": self.names["customer"],
                   "to_party_name": self.names["vendor"], "amount": amount,
                   "contra_date": str(FIXTURE_DATE),
                   "reference_no": f"TEST-CON-{self.run_id}",
                   "description": "System test contra"}
        return self.query("SELECT make_contra(%s::jsonb)",
                          (json.dumps(payload),), one=True)[0]["contra_id"]

    def journal_for(self, table: str, id_column: str, record_id: int):
        allowed = {("payments", "payment_id"), ("receipts", "receipt_id"),
                   ("contra_entries", "contra_id")}
        if (table, id_column) not in allowed:
            raise AssertionError("Unsafe journal source requested")
        journal_id = self.query(
            f"SELECT journal_id FROM {table} WHERE {id_column}=%s",
            (record_id,), one=True,
        )[0]
        lines = self.query(
            "SELECT party_id,debit,credit FROM journallines WHERE journal_id=%s ORDER BY line_id",
            (journal_id,),
        )
        return journal_id, lines

    def assert_cashflow_journal(self, table, id_column, record_id, amount,
                                debit_party, credit_party):
        journal_id, lines = self.journal_for(table, id_column, record_id)
        debit = sum(line[1] for line in lines)
        credit = sum(line[2] for line in lines)
        party_sides = {(line[0], float(line[1]), float(line[2])) for line in lines}
        expected = {
            (debit_party, float(amount), 0.0),
            (credit_party, 0.0, float(amount)),
        }
        return self.assert_true(
            len(lines) == 2 and float(debit) == float(amount)
            and float(credit) == float(amount) and party_sides == expected,
            f"journal={journal_id}, lines={party_sides}",
        )

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
        start, end = date(2020, 1, 1), REPORT_END_DATE
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
            ("monthly: position", "SELECT monthly_company_position(%s)", (FIXTURE_DATE,)),
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

    def pristine_fixture(self):
        business_counts = self.query(
            """SELECT (SELECT count(*) FROM parties),
                      (SELECT count(*) FROM items),
                      (SELECT count(*) FROM journalentries),
                      (SELECT count(*) FROM purchaseinvoices),
                      (SELECT count(*) FROM salesinvoices)""",
            one=True,
        )
        accounts = tuple(
            row[0] for row in self.query(
                "SELECT account_name FROM chartofaccounts ORDER BY account_id"
            )
        )
        return self.assert_true(
            business_counts == (0, 0, 0, 0, 0)
            and accounts == CORE_ACCOUNTS,
            f"business counts={business_counts}, accounts={accounts}",
        )

    def patch_applied_once(self):
        rows = self.query(
            """SELECT patch_name, sha256, status
               FROM system_test_meta.patch_history
               ORDER BY patch_name"""
        )
        expected = [(FIXES.name, FIXES_SHA256, "applied")]
        return self.assert_true(rows == expected, f"patch history={rows}")

    def run(self):
        G = "Master Data and Reports"
        self.case(
            G,
            "Start from deterministic fixture baseline",
            "No restored business rows and exactly seven core accounts",
            self.pristine_fixture,
        )
        self.case(
            G,
            "Apply required SQL patch exactly once",
            "One applied production_fixes.sql row with the current SHA-256",
            self.patch_applied_once,
        )
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

        G = "Payment, Receipt and Contra Accounting"
        cashflow: dict[str, Any] = {}
        self.case(
            G, "Create payment", "Vendor debit and cash credit reconcile",
            lambda: (
                cashflow.setdefault("payment", self.payment()),
                self.assert_cashflow_journal(
                    "payments", "payment_id", cashflow["payment"], 125,
                    self.ids["vendor"], None,
                ),
            )[1],
        )
        self.case(
            G, "Update payment", "Old journal replaced at updated amount",
            lambda: self._update_cashflow(
                "payment", "payments", "payment_id", "update_payment",
                cashflow["payment"], 225, self.ids["vendor"], None,
            ),
        )
        self.case(
            G, "Delete payment", "Payment and linked journal are removed",
            lambda: self._delete_cashflow(
                "payments", "payment_id", "delete_payment", cashflow["payment"]
            ),
        )
        self.case(
            G, "Create receipt", "Cash debit and customer credit reconcile",
            lambda: (
                cashflow.setdefault("receipt", self.receipt()),
                self.assert_cashflow_journal(
                    "receipts", "receipt_id", cashflow["receipt"], 175,
                    None, self.ids["customer"],
                ),
            )[1],
        )
        self.case(
            G, "Update receipt", "Old journal replaced at updated amount",
            lambda: self._update_cashflow(
                "receipt", "receipts", "receipt_id", "update_receipt",
                cashflow["receipt"], 275, None, self.ids["customer"],
            ),
        )
        self.case(
            G, "Delete receipt", "Receipt and linked journal are removed",
            lambda: self._delete_cashflow(
                "receipts", "receipt_id", "delete_receipt", cashflow["receipt"]
            ),
        )
        self.case(
            G, "Create contra", "Destination debit and source credit reconcile without cash",
            lambda: (
                cashflow.setdefault("contra", self.contra()),
                self.assert_cashflow_journal(
                    "contra_entries", "contra_id", cashflow["contra"], 80,
                    self.ids["vendor"], self.ids["customer"],
                ),
            )[1],
        )
        self.case(
            G, "Update contra", "Old journal replaced at updated amount",
            lambda: self._update_cashflow(
                "contra", "contra_entries", "contra_id", "update_contra",
                cashflow["contra"], 180, self.ids["vendor"], self.ids["customer"],
            ),
        )
        self.case(
            G, "Delete contra", "Contra and linked journal are removed",
            lambda: self._delete_cashflow(
                "contra_entries", "contra_id", "delete_contra", cashflow["contra"]
            ),
        )
        self.case(
            G, "Reject non-positive cash-flow amounts", "All three functions reject zero",
            lambda: (
                self.expect_blocked(lambda: self.payment(0), "amount"),
                self.expect_blocked(lambda: self.receipt(0), "amount"),
                self.expect_blocked(lambda: self.contra(0), "amount"),
                "Payment, receipt, and contra rejected zero amounts",
            )[3],
        )
        self.case(
            G, "Reject same-party contra", "Database constraint rejects self-transfer",
            lambda: self.expect_blocked(
                lambda: self.query(
                    "SELECT make_contra(%s::jsonb)",
                    (json.dumps({
                        "from_party_name": self.names["customer"],
                        "to_party_name": self.names["customer"], "amount": 10,
                    }),),
                ),
                "cannot be the same",
            ),
        )
        self.case("Continuous Integrity and Reporting", "Cash-flow checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("cash flow"))

        G = "Party Opening Balance Accounting"
        openings: dict[str, Any] = {}
        self.case(
            G, "Customer debit opening", "Debit customer AR and credit capital",
            lambda: (
                openings.setdefault(
                    "customer", self.opening_party("CUSTOMER", "Customer", 300, "Debit")
                ),
                self.assert_opening_journal(openings["customer"][0], 300, True),
            )[1],
        )
        self.case(
            G, "Vendor credit opening", "Debit capital and credit vendor AP",
            lambda: (
                openings.setdefault(
                    "vendor", self.opening_party("VENDOR", "Vendor", 400, "Credit")
                ),
                self.assert_opening_journal(openings["vendor"][0], 400, False),
            )[1],
        )
        self.case(
            G, "Expense debit opening", "Debit expense party and credit capital",
            lambda: (
                openings.setdefault(
                    "expense", self.opening_party("EXPENSE", "Expense", 500, "Debit")
                ),
                self.assert_opening_journal(openings["expense"][0], 500, True),
            )[1],
        )
        self.case(
            G, "Update customer opening", "Original journal replaced at new amount",
            lambda: self._update_opening_balance(
                openings["customer"][0], openings["customer"][1], 450, True
            ),
        )
        self.case(
            G, "Remove customer opening", "Setting zero removes the opening journal",
            lambda: self._remove_opening_balance(
                openings["customer"][0], openings["customer"][1]
            ),
        )
        self.case("Continuous Integrity and Reporting", "Opening-balance checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("party openings"))

        G = "Duplicate Serial and Concurrency Protection"
        duplicates = self.serials("PURCHASE-DUP", 2)
        self.case(
            G, "Reject duplicate serial within purchase", "Whole invoice is rejected",
            lambda: self.expect_blocked(
                lambda: self.purchase([duplicates[0], duplicates[0]]),
                "unique",
            ),
        )
        self.case(
            G, "Reject serial reused across purchases", "Only original unit remains",
            lambda: self._duplicate_across_purchases(duplicates[1]),
        )
        race_serial = self.serials("SALE-RACE", 1)[0]
        self.case(
            G, "Prepare serial for concurrent sale", "One stocked unit exists",
            lambda: (
                self.purchase([race_serial]),
                self.assert_true(self.stock(race_serial), "Race serial is in stock"),
            )[1],
        )
        self.case(
            G, "Race two sales for one serial", "Exactly one transaction commits",
            lambda: self._concurrent_sale(race_serial),
        )
        self.case("Continuous Integrity and Reporting", "Concurrency checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("serial concurrency"))

        G = "Numeric and Date Boundary Validation"
        self.case(
            G, "Reject invalid purchase quantities", "Zero, negative, and fractional quantities fail",
            lambda: self._reject_invoice_values(
                "purchase", "qty", [0, -1, 1.5], "Quantity"
            ),
        )
        self.case(
            G, "Reject invalid sale quantities", "Zero, negative, and fractional quantities fail",
            lambda: self._reject_invoice_values(
                "sale", "qty", [0, -1, 1.5], "Quantity"
            ),
        )
        self.case(
            G, "Reject invalid purchase prices", "Negative and nonnumeric prices fail",
            lambda: self._reject_invoice_values(
                "purchase", "unit_price", [-0.01, "not-a-number"], "price"
            ),
        )
        self.case(
            G, "Reject invalid sale prices", "Negative and nonnumeric prices fail",
            lambda: self._reject_invoice_values(
                "sale", "unit_price", [-0.01, "not-a-number"], "price"
            ),
        )
        self.case(
            G, "Reject missing invoice dates", "Purchase and sale require dates",
            lambda: (
                self.expect_blocked(lambda: self._raw_invoice("purchase", None), "date"),
                self.expect_blocked(lambda: self._raw_invoice("sale", None), "date"),
                "Both invoice functions rejected null dates",
            )[2],
        )
        self.case(
            G, "Cash-flow amount and date boundaries", "One cent posts; overflow and invalid dates fail",
            self._cashflow_boundaries,
        )
        self.case(
            G, "Leap-day report boundary", "All dated reports accept a valid leap day",
            self._leap_day_reports,
        )
        self.case("Continuous Integrity and Reporting", "Boundary checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("numeric and date boundaries"))

        G = "Return Mutation and Report Reconciliation"
        return_serials = self.serials("PRETURN-MUTATE", 2)
        return_state: dict[str, Any] = {}
        self.case(
            G, "Create two-serial purchase return", "Both serials leave stock",
            lambda: (
                self.purchase(return_serials),
                return_state.setdefault("id", self.purchase_return(return_serials)),
                self.assert_true(
                    all(not self.stock(value) for value in return_serials),
                    "Both serials returned to vendor",
                ),
            )[2],
        )
        self.case(
            G, "Update purchase return to one serial", "Removed serial returns to stock",
            lambda: (
                self.query(
                    "SELECT update_purchase_return(%s::bigint,%s::jsonb,%s::integer)",
                    (return_state["id"], json.dumps([return_serials[0]]), None),
                ),
                self.assert_true(
                    not self.stock(return_serials[0]) and self.stock(return_serials[1]),
                    "Retained serial is out; removed serial is stocked",
                ),
            )[1],
        )
        self.case(
            G, "Reject invalid purchase-return updates", "Empty and duplicate lists fail atomically",
            lambda: self._reject_purchase_return_updates(
                return_state["id"], return_serials[0]
            ),
        )
        self.case(
            G, "Delete purchase return", "Header/journal removed and serial restored",
            lambda: self._delete_purchase_return_and_reconcile(
                return_state["id"], return_serials[0]
            ),
        )
        self.case(
            G, "Customer report-to-journal reconciliation", "All balance representations agree",
            lambda: self._reconcile_party_reports("customer"),
        )
        self.case(
            G, "Vendor report-to-journal reconciliation", "All balance representations agree",
            lambda: self._reconcile_party_reports("vendor"),
        )
        self.case("Continuous Integrity and Reporting", "Return/report reconciliation checkpoint", "All reports and integrity checks pass", lambda: self.checkpoint("return and report reconciliation"))

        self.case(
            "Defect Regression Manifest",
            "Every confirmed defect retains a passing regression",
            "Defects 1 through 9 are mapped to passing behavioral cases",
            self._regression_manifest,
        )

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

    def _update_cashflow(self, kind, table, id_column, function, record_id,
                         amount, debit_party, credit_party):
        old_journal, _ = self.journal_for(table, id_column, record_id)
        date_key = {"payment": "payment_date", "receipt": "receipt_date",
                    "contra": "contra_date"}[kind]
        payload = {"amount": amount, date_key: str(FIXTURE_DATE),
                   "description": f"Updated system test {kind}"}
        self.query(f"SELECT {function}(%s,%s::jsonb)",
                   (record_id, json.dumps(payload)))
        new_journal, _ = self.journal_for(table, id_column, record_id)
        old_exists = self.query(
            "SELECT count(*) FROM journalentries WHERE journal_id=%s",
            (old_journal,), one=True,
        )[0]
        self.assert_true(old_journal != new_journal and old_exists == 0,
                         f"journal replaced: {old_journal} -> {new_journal}")
        return self.assert_cashflow_journal(
            table, id_column, record_id, amount, debit_party, credit_party
        )

    def _delete_cashflow(self, table, id_column, function, record_id):
        journal_id, _ = self.journal_for(table, id_column, record_id)
        self.query(f"SELECT {function}(%s)", (record_id,))
        record_count = self.query(
            f"SELECT count(*) FROM {table} WHERE {id_column}=%s",
            (record_id,), one=True,
        )[0]
        journal_count = self.query(
            "SELECT count(*) FROM journalentries WHERE journal_id=%s",
            (journal_id,), one=True,
        )[0]
        return self.assert_true(
            record_count == 0 and journal_count == 0,
            f"record count={record_count}, journal count={journal_count}",
        )

    def _update_opening_balance(self, party_id, party_name, amount,
                                party_on_debit):
        old_journal, _ = self.opening_journal(party_id)
        payload = {"party_name": party_name, "opening_balance": amount}
        self.query("SELECT update_party_from_json(%s,%s::jsonb)",
                   (party_id, json.dumps(payload)))
        new_journal, _ = self.opening_journal(party_id)
        old_count = self.query(
            "SELECT count(*) FROM journalentries WHERE journal_id=%s",
            (old_journal,), one=True,
        )[0]
        self.assert_true(
            new_journal != old_journal and old_count == 0,
            f"opening journal replaced: {old_journal} -> {new_journal}",
        )
        return self.assert_opening_journal(party_id, amount, party_on_debit)

    def _remove_opening_balance(self, party_id, party_name):
        journal_id, _ = self.opening_journal(party_id)
        payload = {"party_name": party_name, "opening_balance": 0}
        self.query("SELECT update_party_from_json(%s,%s::jsonb)",
                   (party_id, json.dumps(payload)))
        remaining = self.query(
            """SELECT count(*) FROM journalentries je
               WHERE je.journal_id=%s OR (
                   je.description ILIKE 'Opening Balance for%%'
                   AND je.journal_id IN (
                       SELECT journal_id FROM journallines WHERE party_id=%s))""",
            (journal_id, party_id), one=True,
        )[0]
        return self.assert_true(remaining == 0,
                                f"remaining opening journals={remaining}")

    def _duplicate_across_purchases(self, serial):
        original_invoice = self.purchase([serial])
        blocked = self.expect_blocked(
            lambda: self.purchase([serial]), "unique"
        )
        units = self.query(
            "SELECT count(*) FROM purchaseunits WHERE serial_number=%s",
            (serial,), one=True,
        )[0]
        invoices = self.query(
            """SELECT count(DISTINCT pi.purchase_invoice_id)
               FROM purchaseitems pi JOIN purchaseunits pu USING (purchase_item_id)
               WHERE pu.serial_number=%s""",
            (serial,), one=True,
        )[0]
        return self.assert_true(
            units == 1 and invoices == 1 and bool(original_invoice),
            f"{blocked}; units={units}, source invoices={invoices}",
        )

    def _concurrent_sale(self, serial):
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()
        payload = json.dumps([{
            "item_name": self.names["item_a"], "qty": 1,
            "unit_price": 199, "serials": [serial],
        }])

        def worker():
            # libpq omits passwords when exposing an existing connection's DSN.
            # Pass the isolated test credential again for concurrent workers.
            conn = psycopg2.connect(
                self.conn.dsn,
                password=os.getenv("TEST_PGPASSWORD", ""),
            )
            try:
                with conn.cursor() as cur:
                    barrier.wait(timeout=10)
                    cur.execute(
                        "SELECT create_sale(%s::bigint,%s::date,%s::jsonb,%s::integer)",
                        (self.ids["customer"], FIXTURE_DATE, payload, None),
                    )
                    sale_id = cur.fetchone()[0]
                conn.commit()
                result = ("committed", sale_id)
            except Exception as exc:
                conn.rollback()
                result = ("blocked", str(exc).splitlines()[0])
            finally:
                conn.close()
            with outcome_lock:
                outcomes.append(result)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assert_true(
            all(not thread.is_alive() for thread in threads),
            "Concurrent sale workers did not finish",
        )
        committed = [value for status, value in outcomes if status == "committed"]
        blocked = [value for status, value in outcomes if status == "blocked"]
        return self.assert_true(
            len(committed) == 1 and len(blocked) == 1
            and self.active_sales(serial) == 1 and not self.stock(serial),
            f"committed={committed}, blocked={blocked}",
        )

    def _raw_invoice(self, kind, invoice_date, field=None, value=None):
        serial = f"TEST-{self.run_id}-BOUNDARY-{kind}-{field}-{value}"
        item = {"item_name": self.names["item_a"], "qty": 1,
                "unit_price": 100, "serials": [serial]}
        if kind == "purchase":
            item["serials"] = [{"serial": serial, "comment": "boundary"}]
        if field:
            item[field] = value
        function = "create_purchase" if kind == "purchase" else "create_sale"
        party_id = self.ids["vendor"] if kind == "purchase" else self.ids["customer"]
        return self.query(
            f"SELECT {function}(%s::bigint,%s::date,%s::jsonb,%s::integer)",
            (party_id, invoice_date, json.dumps([item]), None), one=True,
        )

    def _reject_invoice_values(self, kind, field, values, message):
        blocked = []
        for value in values:
            blocked.append(self.expect_blocked(
                lambda value=value: self._raw_invoice(
                    kind, FIXTURE_DATE, field, value
                ),
                message,
            ))
        return f"Rejected {field} values: {values}; cases={len(blocked)}"

    def _cashflow_boundaries(self):
        payment_id = self.payment(0.01)
        posted = self.assert_cashflow_journal(
            "payments", "payment_id", payment_id, 0.01,
            self.ids["vendor"], None,
        )
        self._delete_cashflow("payments", "payment_id", "delete_payment", payment_id)
        overflow = self.expect_blocked(lambda: self.payment(10_000_000_000), "overflow")
        bad_date_payload = {
            "party_name": self.names["customer"], "amount": 1,
            "receipt_date": "2026-02-30", "method": "Cash",
        }
        invalid_date = self.expect_blocked(
            lambda: self.query(
                "SELECT make_receipt(%s::jsonb)",
                (json.dumps(bad_date_payload),),
            ),
            "date",
        )
        return f"{posted}; {overflow}; {invalid_date}"

    def _leap_day_reports(self):
        leap_day = date(2024, 2, 29)
        calls = [
            ("SELECT * FROM detailed_ledger(%s,%s,%s)",
             (self.names["customer"], leap_day, leap_day)),
            ("SELECT * FROM get_cash_ledger_with_party(%s,%s)",
             (leap_day, leap_day)),
            ("SELECT * FROM sale_wise_profit(%s,%s)",
             (leap_day, leap_day)),
            ("SELECT monthly_income_statement(%s,%s,%s,%s)",
             (leap_day, leap_day, 0, 0)),
        ]
        for statement, params in calls:
            self.query(statement, params)
        return f"{len(calls)} report functions accepted {leap_day}"

    def _reject_purchase_return_updates(self, return_id, serial):
        empty = self.expect_blocked(
            lambda: self.query(
                "SELECT update_purchase_return(%s::bigint,%s::jsonb,%s::integer)",
                (return_id, json.dumps([]), None),
            ),
            "At least one",
        )
        duplicate = self.expect_blocked(
            lambda: self.query(
                "SELECT update_purchase_return(%s::bigint,%s::jsonb,%s::integer)",
                (return_id, json.dumps([serial, serial]), None),
            ),
            "more than once",
        )
        rows = self.query(
            "SELECT serial_number FROM purchasereturnitems WHERE purchase_return_id=%s",
            (return_id,),
        )
        return self.assert_true(
            rows == [(serial,)] and not self.stock(serial),
            f"{empty}; {duplicate}; retained rows={rows}",
        )

    def _delete_purchase_return_and_reconcile(self, return_id, serial):
        journal_id = self.query(
            "SELECT journal_id FROM purchasereturns WHERE purchase_return_id=%s",
            (return_id,), one=True,
        )[0]
        self.query("SELECT delete_purchase_return(%s)", (return_id,))
        header = self.query(
            "SELECT count(*) FROM purchasereturns WHERE purchase_return_id=%s",
            (return_id,), one=True,
        )[0]
        journal = self.query(
            "SELECT count(*) FROM journalentries WHERE journal_id=%s",
            (journal_id,), one=True,
        )[0]
        return self.assert_true(
            header == 0 and journal == 0 and self.stock(serial),
            f"header={header}, journal={journal}, serial restored",
        )

    def _reconcile_party_reports(self, key):
        party_id, party_name = self.ids[key], self.names[key]
        direct = self.query(
            """SELECT COALESCE(sum(debit),0),COALESCE(sum(credit),0),
                      COALESCE(sum(debit-credit),0)
               FROM journallines WHERE party_id=%s""",
            (party_id,), one=True,
        )
        balance_json = self.query(
            "SELECT get_party_balance_by_name(%s)", (party_name,), one=True
        )[0]
        trial = self.query(
            """SELECT total_debit,total_credit,balance FROM vw_trial_balance
               WHERE code IS NULL AND name=%s""",
            (party_name,), one=True,
        )
        ledger = self.query(
            "SELECT debit,credit,running_balance FROM detailed_ledger(%s,%s,%s)",
            (party_name, date(1900, 1, 1), REPORT_END_DATE),
        )
        self.assert_true(trial is not None and ledger,
                         f"Missing trial/ledger rows for {party_name}")
        ledger_debit = sum(row[0] for row in ledger)
        ledger_credit = sum(row[1] for row in ledger)
        values = [
            float(direct[0]), float(direct[1]), float(direct[2]),
            float(balance_json["balance"]),
            float(trial[0]), float(trial[1]), float(trial[2]),
            float(ledger_debit), float(ledger_credit), float(ledger[-1][2]),
        ]
        expected = [
            values[0], values[1], values[2], values[2],
            values[0], values[1], values[2], values[0], values[1], values[2],
        ]
        return self.assert_true(
            all(abs(actual - target) < 0.005
                for actual, target in zip(values, expected)),
            f"{party_name}: debit={direct[0]}, credit={direct[1]}, balance={direct[2]}",
        )

    def _regression_manifest(self):
        by_name = {result.name: result for result in self.results}
        missing = {
            defect: name for defect, name in REGRESSION_CASES.items()
            if name not in by_name
        }
        failing = {
            defect: name for defect, name in REGRESSION_CASES.items()
            if name in by_name and not by_name[name].passed
        }
        return self.assert_true(
            not missing and not failing,
            f"mapped={len(REGRESSION_CASES)}, missing={missing}, failing={failing}",
        )

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
    return host in ("", "localhost", "127.0.0.1", "::1", "system-test-db") or host.startswith("/")


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


def psql_command(kwargs, name: str):
    return [
        "psql", "--host", kwargs["host"], "--port", str(kwargs["port"]),
        "--username", kwargs["user"], "--dbname", name,
        "--set", "ON_ERROR_STOP=1", "--file", "-",
    ]


def psql_environment(kwargs):
    env = os.environ.copy()
    if kwargs["password"]:
        env["PGPASSWORD"] = kwargs["password"]
    return env


def restore_backup(kwargs, name: str):
    env = psql_environment(kwargs)
    # The production-origin dump assigns every object to a role named
    # ``postgres``. Local Homebrew installations commonly use the macOS account
    # name instead, so remap ownership in-memory without modifying the backup or
    # creating a cluster-wide compatibility role.
    owner = '"' + str(kwargs["user"]).replace('"', '""') + '"'
    dump_sql = BACKUP.read_text(encoding="utf-8").replace("OWNER TO postgres", f"OWNER TO {owner}")
    command = psql_command(kwargs, name)
    completed = subprocess.run(command, env=env, text=True, input=dump_sql, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f"Backup restore failed:\n{completed.stderr[-4000:]}")


def reset_fixture_data(kwargs, name: str):
    """Remove restored business data while retaining required reference accounts."""
    fixture_kwargs = dict(kwargs, dbname=name)
    conn = psycopg2.connect(**fixture_kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT tablename FROM pg_tables
                   WHERE schemaname = 'public' AND tablename <> 'chartofaccounts'
                   ORDER BY tablename"""
            )
            tables = [sql.Identifier("public", row[0]) for row in cur.fetchall()]
            if tables:
                cur.execute(
                    sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                        sql.SQL(", ").join(tables)
                    )
                )
            cur.execute(
                "DELETE FROM chartofaccounts WHERE account_name <> ALL(%s)",
                (list(CORE_ACCOUNTS),),
            )
            cur.execute(
                """SELECT setval(
                       pg_get_serial_sequence('chartofaccounts', 'account_id'),
                       (SELECT max(account_id) FROM chartofaccounts),
                       true
                   )"""
            )
        conn.commit()
    finally:
        conn.close()


def apply_required_patch(kwargs, name: str):
    """Apply the exact required patch once and record its content checksum."""
    if not FIXES.exists():
        raise RuntimeError(f"Required SQL patch not found: {FIXES}")

    fixture_kwargs = dict(kwargs, dbname=name)
    conn = psycopg2.connect(**fixture_kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS system_test_meta")
            cur.execute(
                """CREATE TABLE IF NOT EXISTS system_test_meta.patch_history (
                       patch_name text PRIMARY KEY,
                       sha256 text NOT NULL CHECK (length(sha256) = 64),
                       status text NOT NULL CHECK (status IN ('applying', 'applied')),
                       applied_at timestamptz
                   )"""
            )
            cur.execute(
                """INSERT INTO system_test_meta.patch_history
                       (patch_name, sha256, status)
                   VALUES (%s, %s, 'applying')
                   ON CONFLICT (patch_name) DO NOTHING
                   RETURNING patch_name""",
                (FIXES.name, FIXES_SHA256),
            )
            if cur.fetchone() is None:
                raise RuntimeError(f"Refusing to apply {FIXES.name} more than once")
        conn.commit()

        completed = subprocess.run(
            psql_command(kwargs, name),
            env=psql_environment(kwargs),
            text=True,
            input=FIXES.read_text(encoding="utf-8"),
            capture_output=True,
        )
        if completed.returncode:
            raise RuntimeError(f"Applying {FIXES.name} failed:\n{completed.stderr[-4000:]}")

        with conn.cursor() as cur:
            cur.execute(
                """UPDATE system_test_meta.patch_history
                   SET status = 'applied', applied_at = CURRENT_TIMESTAMP
                   WHERE patch_name = %s AND sha256 = %s AND status = 'applying'""",
                (FIXES.name, FIXES_SHA256),
            )
            if cur.rowcount != 1:
                raise RuntimeError(f"Could not finalize patch ledger for {FIXES.name}")
        conn.commit()
    finally:
        conn.close()


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
        restore_backup(kwargs, db_name)
        reset_fixture_data(kwargs, db_name)
        apply_required_patch(kwargs, db_name)
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
