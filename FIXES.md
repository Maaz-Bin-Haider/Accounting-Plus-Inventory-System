# System Fixes - July 18, 2026

This document describes every defect that was found by the disposable system
test suite (`system_tests/`), the root cause of each, the fix applied, the
backend error-handling improvements, and the exact deployment steps for the
EC2 production server.

Test result before fixes: **52 passed, 8 failed** (July 17, 2026 run)
Test result after fixes: **60 passed, 0 failed** (July 18, 2026 run, twice)

All database fixes live in one file: **`production_fixes.sql`** (project root).
It is a one-time patch, safe to run once on production. It runs inside a
single transaction (all-or-nothing) and ends with read-only diagnostics.

---

## Part 1 - The 8 failed tests and their fixes

### 1. Duplicate sale return was accepted (failed tests 1 and 5)

- **Symptom:** A serial could be sale-returned again without being resold,
  in both single-item and mixed-item returns.
- **Root cause:** The database has two overloads of `create_sale_return`.
  The old 2-argument version correctly filtered `su.status = 'Sold'`, but the
  newer 3-argument version (the one the Django app actually calls, with
  `created_by`) was missing that filter. It matched the already-'Returned'
  SoldUnits record and happily returned the serial a second time.
- **Fix:** The 3-argument `create_sale_return` now selects only the active
  `'Sold'` record (`ORDER BY sold_unit_id DESC LIMIT 1` for safety with
  historical duplicates). The legacy 2-argument overload now delegates to the
  fixed version so both behave identically. Clear error messages distinguish
  "serial does not exist", "serial not currently sold", and "sold to a
  different customer".

### 2. Sale invoice update was permitted after a partial return (failed tests 2 and 6)

- **Symptom:** `validate_sales_update` reported "valid" for an invoice that a
  sale return referenced, for both single-item and multi-item invoices.
- **Root cause:** The function only blocked the update when a *removed*
  serial appeared in a sale return. An update that kept the same serial list
  always passed, even though rewriting the invoice would clash with the
  return's stock and journal records.
- **Fix:** `validate_sales_update` now blocks the update entirely while any
  serial of the invoice is in `'Returned'` state, telling the user to update
  or delete the related sale return first. The old removed-serial check is
  kept as a second safety net. In addition, `update_sale_invoice` itself now
  calls `validate_sales_update` and raises on failure, so the rule holds even
  if a caller skips the pre-check.

### 3. An old sale return could be deleted after the serial was resold (failed test 3)

- **Symptom:** Sell, return, resell, then delete the old return - accepted.
- **Root cause:** `delete_sale_return` reversed the return by setting **every**
  SoldUnits record of the unit back to `'Sold'` (including the newer active
  sale's record) and forcing `in_stock = FALSE`, producing two active sold
  states and corrupted stock/journals.
- **Fix:** `delete_sale_return` now refuses to run if any serial in the
  return (a) has an active `'Sold'` record (it was resold), or (b) is no
  longer in stock (for example returned to the vendor). When the delete is
  allowed, it reverts only the exact `'Returned'` record of the return.

### 4. An old sale return could be updated after the serial was resold (failed test 4)

- **Symptom:** Same setup as above, but updating the old return - accepted.
- **Root cause:** `update_sale_return` had the same unguarded reversal logic.
- **Fix:** The same guards were added to the reversal phase of
  `update_sale_return`, and it reverts only the exact `'Returned'` record.
  Its re-insert phase keeps the active-`'Sold'` filter and gains payload
  validation (empty list, duplicate serials, blank serials).

### 5 and 6. Covered by fixes 1 and 2 (mixed-item variants of the same defects).

### 7 and 8. Sale accepted a quantity different from the serial count

- **Symptom:** `qty = 5` with 2 serials was accepted; `qty = 1` with 2
  serials was accepted. Invoice totals, item quantities, stock movements and
  profit reports all disagreed with each other.
- **Root cause:** `create_sale` never compared `qty` against the length of
  the serials array.
- **Fix:** `create_sale` (and `update_sale_invoice`) now require
  `qty = number of serials` for every item, with the message:
  *"Quantity (5) does not match the number of serial numbers (2) for item
  "X". Please provide exactly one serial number per unit."*

---

## Part 2 - Additional hardening (same defect class, found during analysis)

These were not covered by the failing tests but are the same category of
invalid entry and are now blocked at the database level:

1. **`update_sale_invoice` had no validation at all.** It did not call
   `validate_sales_update`, did not check stock, and could silently steal a
   serial that was sold on another invoice. It now validates the payload
   (quantity format, price format, qty = serial count, duplicates, blank
   serials), verifies each serial exists, belongs to the named item, and is
   either in stock or already sold on the same invoice.
2. **`delete_sale` had no guard of its own** - only the Django view checked
   `validate_sales_delete`. The function itself now refuses to delete an
   invoice while any of its serials is in `'Returned'` state.
3. **`create_purchase_return` ignored stock state.** A serial currently SOLD
   to a customer, or already returned to the vendor, could still be
   "returned to the vendor". It now requires the serial to be in stock and
   explains why when it is not.
4. **`create_purchase` and `update_purchase_invoice`** now enforce
   qty = serial count, quantity/price format checks, duplicate-serial
   detection inside the payload, blank-serial detection, and a friendly
   "Serial already exists in the system" message instead of a raw
   unique-constraint failure.
5. **`update_purchase_return`** gains empty-payload and duplicate-serial
   checks (its in-stock check already existed).
6. **All legacy function overloads** (`create_sale` 3-arg,
   `create_sale_return` 2-arg, `update_sale_return` 2-arg,
   `update_sale_invoice` 4-arg, `create_purchase` 3-arg,
   `update_purchase_invoice` 4-arg, `create_purchase_return` 2-arg) now
   delegate to the fixed versions, so no code path can bypass the new rules.
7. **`create_sale`** additionally verifies that each serial belongs to the
   item row it is sold under (the Django view checked this, but the database
   did not).

---

## Part 3 - Backend error handling improvements (Django)

Previously most views swallowed database errors and returned generic text
like *"Failed to make Sale, try again!"*, or worse, leaked the raw exception
(`f"... {e}"`) to the browser. Users could not tell what they did wrong.

**New shared helper: `financee/db_errors.py` - `user_db_error(exc, fallback)`**

- All business-rule errors from the stored procedures are raised with
  `RAISE EXCEPTION` (SQLSTATE `P0001`) and are written for end users. The
  helper detects `P0001` and shows that exact message to the user.
- Any other database error (connection failure, constraint violation,
  programming error) shows the safe generic fallback instead, so internal
  details are never leaked. The full traceback still goes to the server log.

**Views updated to use it (every create/update/delete path):**

| App | Endpoints |
| --- | --- |
| `sale` | create, update, delete (+ validation messages now come from the DB) |
| `purchase` | create, update, delete (also removed a raw `{e}` leak) |
| `saleReturn` | create, update, delete |
| `purchaseReturn` | create, update, delete (also fixed a swallowed-exception path that returned no response at all) |
| `payments` | create, update, delete (removed raw `{e}` leaks) |
| `receipts` | create, update, delete (removed raw `{e}` leaks) |
| `contra` | create, update, delete (removed raw `{e}` leaks) |
| `parties` | create, update (both AJAX and form paths; added missing generic handlers) |
| `items` | create, update (both AJAX and form paths; added missing generic handlers) |

Example of what users see now:

- Before: `Failed to make Sale, try again!`
- After: `Serial "ABC-123" is not available in stock. It may not exist, may
  already be sold, or may have been returned to the vendor.`

---

## Part 4 - Test suite changes

- `system_tests/run_system_tests.py` now automatically picks the **latest**
  `db_backup_*.sql` file in the project root (it previously hard-coded the
  deleted July 3 backup; the current backup is `db_backup_20260718_0000.sql`).
- After restoring the backup into the disposable database, the runner applies
  `production_fixes.sql` on top - so the suite tests exactly what production
  will run after deployment.
- Full suite rerun after all changes: **60 passed, 0 failed** - including all
  52 previously passing tests (no regressions) and the 8 previously failing
  ones. See `system_tests/RESULTS.md` for the detailed table.

---

## Part 5 - Deployment steps (EC2)

1. **Push/pull the code** (done by you):
   ```bash
   # on EC2, from the project root
   git pull
   ```
2. **Back up the production database first** (safety):
   ```bash
   pg_dump -h localhost -U <DB_USER> -d <DB_NAME> > pre_fix_backup_$(date +%Y%m%d_%H%M).sql
   ```
3. **Apply the one-time SQL patch:**
   ```bash
   psql -h localhost -U <DB_USER> -d <DB_NAME> -f production_fixes.sql
   ```
   The patch is transactional: if anything fails it rolls back completely.
   At the end it prints five read-only diagnostics. **Review them:**
   - Diagnostics 1-4 should return **0 rows**. Any rows listed are historical
     data corrupted while the old bugs were live (for example duplicate
     active sold states). Nothing is auto-repaired - share the output and the
     affected serials can be corrected deliberately.
   - Diagnostic 5 prints total debits and credits; the two numbers must be
     equal.
4. **Restart the application** (gunicorn serves the Python code, so it must
   be restarted for the view changes; nginx only proxies but restarting it is
   harmless):
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```
5. **Verify:** try to submit a sale with a wrong quantity or a duplicate
   sale return - the browser should now show the new descriptive error
   message and the entry must be rejected.

---

## Files changed

| File | Change |
| --- | --- |
| `production_fixes.sql` | NEW - one-time DB patch (all stored-procedure fixes + diagnostics) |
| `financee/db_errors.py` | NEW - shared DB-error-to-user-message helper |
| `sale/views.py` | Surface real DB errors; DB-driven validation messages |
| `purchase/views.py` | Surface real DB errors; remove raw exception leak |
| `saleReturn/views.py` | Surface real DB errors |
| `purchaseReturn/views.py` | Surface real DB errors; fix swallowed-exception path |
| `payments/views.py` | Surface real DB errors; remove raw exception leaks |
| `receipts/views.py` | Surface real DB errors; remove raw exception leaks |
| `contra/views.py` | Surface real DB errors; remove raw exception leaks |
| `parties/views.py` | Surface real DB errors; add missing error handlers |
| `items/views.py` | Surface real DB errors; add missing error handlers |
| `system_tests/run_system_tests.py` | Use latest backup; apply `production_fixes.sql` after restore |
| `system_tests/RESULTS.md` | Regenerated - 60 passed, 0 failed |
| `system_tests/FAILED_TESTS.md` | Updated - backlog closed |
