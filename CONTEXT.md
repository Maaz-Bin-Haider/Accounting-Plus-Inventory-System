# System Context

This file records the analyzed context for the Accounting Plus Inventory Management System. It is intended for future development, debugging, onboarding, and database work.

## High-Level Architecture

The system is a Django web application backed by a PostgreSQL database. The design is database-centric:

- Django renders pages, validates request permissions, handles login/session state, and exposes AJAX endpoints.
- PostgreSQL owns most accounting and inventory behavior through stored functions, views, and triggers.
- Frontend JavaScript calls Django endpoints for create/update/delete, record navigation, lookup, summaries, and reporting.

The local backup (`db_backup_20260718_0000.sql` at the time of writing; the latest `db_backup_*.sql` in the project root) is a complete PostgreSQL dump containing schema and data. It is the authoritative source for table structure, function signatures, triggers, views, and current data shape. Note: `production_fixes.sql` (July 18, 2026) supersedes several stored procedures in that dump; apply it on top when restoring.

## Django Project

Project package:

- `financee/settings.py`
- `financee/urls.py`
- `financee/admin_site.py`
- `financee/wsgi.py`
- `financee/asgi.py`

Installed local apps:

- `parties`
- `items`
- `payments`
- `receipts`
- `purchase`
- `sale`
- `purchaseReturn`
- `home`
- `saleReturn`
- `accountsReports`
- `authentication`
- `contra`

Settings notes:

- Database engine: `django.db.backends.postgresql`
- Environment variables read from `.env` using `django-environ`
- Required env vars: `SECRET_KEY`, `DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `ALLOWED_HOSTS = ['*']`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`
- `STATICFILES_DIRS = [BASE_DIR / 'static']`
- Static storage uses `ManifestStaticFilesStorage`
- `LOGIN_URL = '/authentication/login/'`
- `LOGIN_REDIRECT_URL = '/home/'`
- `LOGOUT_REDIRECT_URL = '/authentication/login/'`

## Root Routing

`financee/urls.py` maps:

- `/` to a redirect helper
- `/admin/` to `financee_admin_site`
- `/parties/` to `parties.urls`
- `/items/` to `items.urls`
- `/payments/` to `payments.urls`
- `/receipts/` to `receipts.urls`
- `/purchase/` to `purchase.urls`
- `/sale/` to `sale.urls`
- `/purchaseReturn/` to `purchaseReturn.urls`
- `/saleReturn/` to `saleReturn.urls`
- `/home/` to `home.urls`
- `/accountsReports/` to `accountsReports.urls`
- `/authentication/` to `authentication.urls`
- `/contra/` to `contra.urls`

## Shared Frontend Enhancements

### Smart Description Box

The smart description enhancement is a UI-only layer over existing description textareas. It does not change database behavior or backend payloads.

Files:

- `static/css/smart_description.css`
- `static/js/smart_description.js`

Templates loading the shared assets:

- `templates/sale_templates/sale_template.html`
- `templates/purchase_templates/purchasing_template.html`
- `templates/sale_return_templates/sale_return_template.html`
- `templates/purchase_return_templates/purchase_return_template.html`
- `templates/payments_templates/payment.html`
- `templates/receipts_templates/receipt.html`
- `templates/contra_templates/contra.html`

Behavior:

- Enhances any `textarea[name="description"]`.
- Keeps original textarea IDs and values intact.
- Saves descriptions as plain text.
- Detects pasted tab-separated spreadsheet data and comma-separated CSV data.
- Uses the first row as editable table headers.
- Displays a capped-height inline table preview with internal scrolling.
- Syncs edited table cells back into the hidden/original textarea in real time.
- Copies table descriptions as tab-separated text for Excel/Google Sheets compatibility.
- Provides `Copy`, `Edit raw`, and `Expand` controls.
- Uses SweetAlert for the expanded editor.
- Observes programmatic `.value = ...` updates, so existing previous/next/old-entry loading code continues to work.

Important implementation note: the seven existing page-specific JS files were not required to change for the smart description feature. They continue to assign loaded description text to the same textarea IDs.

## Module Map

### `authentication`

Views:

- `login_view`
- `logout_view`
- `current_user`

URLs:

- `/authentication/login/`
- `/authentication/logout/`
- `/authentication/current/user/`

The app also owns custom permission seeding migrations. Permissions are created against the `auth.user` content type and referenced as `auth.<codename>` in views.

### `home`

Primary template:

- `templates/home_templtes/home_template.html`

Core views:

- `home_view`
- dashboard JSON endpoints for sales, stock, top parties, receivables aging, recent transactions, expenses, smart alerts
- legacy APIs for cash, parties, items, balances, receivables, payables, expense party balances

Important DB functions/views called:

- `fn_dash_sales_today_kpi`
- `fn_dash_sales_range`
- `fn_dash_sales_last7days`
- `fn_dash_stock_kpi`
- `fn_dash_low_stock_items`
- `fn_dash_fast_moving_items`
- `fn_dash_stale_stock`
- `fn_dash_top_customers`
- `fn_dash_top_vendors`
- `fn_dash_receivables_aging`
- `fn_dash_recent_transactions`
- `fn_dash_expense_kpi`
- `fn_dash_top_expense_categories`
- `fn_dash_top_expense_descriptions`
- `fn_dash_smart_alerts`
- `get_parties_json`
- `get_items_json`
- `get_party_balances_json_excluding`
- `get_accounts_receivable_json_excluding`
- `get_accounts_payable_json_excluding`
- `get_expense_party_balances_json`

### `parties`

Primary templates:

- `templates/parties_templates/parties.html`
- `templates/parties_templates/add_new_party.html`
- `templates/parties_templates/update_party.html`

Views:

- `parties_hub`
- `create_new_party`
- `update_party`
- `auto_complete_party`
- `parties_list_json`

Important DB calls:

- `add_party_from_json`
- `update_party_from_json`
- `get_party_by_name`
- direct lookups against `Parties`

Party types in the DB check constraint:

- `Customer`
- `Vendor`
- `Both`
- `Expense`

### `items`

Primary templates:

- `templates/items_templates/items.html`
- `templates/items_templates/add_new_item.html`
- `templates/items_templates/update_item.html`

Views:

- `items_hub`
- `create_new_item`
- `update_item_view`
- `autocomplete_item`
- `items_list_json`
- helper `get_item_by_name`

Important DB calls:

- `add_item_from_json`
- `update_item_from_json`
- `get_item_by_name`
- `get_item_names_like`
- direct lookups against `Items`

### `purchase`

Primary template:

- `templates/purchase_templates/purchasing_template.html`

Views:

- `purchasing`
- `get_purchase`
- `get_purchase_summary`
- `purchase_serial_check`

Important DB calls:

- `create_purchase`
- `update_purchase_invoice`
- `validate_purchase_update`
- `validate_purchase_delete`
- `delete_purchase`
- `get_last_purchase_id`
- `get_previous_purchase`
- `get_next_purchase`
- `get_current_purchase`
- `get_purchase_summary`

Data model:

- `purchaseinvoices` stores invoice header.
- `purchaseitems` stores item quantity and unit price.
- `purchaseunits` stores each serial number and `in_stock` status.

### `sale`

Primary template:

- `templates/sale_templates/sale_template.html`

Views:

- `sales`
- `get_sale`
- `get_sale_summary`
- `sale_lookup_serial`
- `sale_bulk_serial_lookup`
- helper `get_item_by_serial_for_sale`

Important DB calls:

- `create_sale`
- `update_sale_invoice`
- `validate_sales_update`
- `validate_sales_delete`
- `delete_sale`
- `get_last_sale_id`
- `get_previous_sale`
- `get_next_sale`
- `get_current_sale`
- `get_sales_summary`
- `get_serial_number_details`

Data model:

- `salesinvoices` stores invoice header.
- `salesitems` stores item quantity and sale price.
- `soldunits` links sold serial units to sale items and stores sold price/status.

### `purchaseReturn`

Primary template:

- `templates/purchase_return_templates/purchase_return_template.html`

Views:

- `createPurchaseReturn`
- `purchase_return_lookup`
- `get_purchase_return`
- `get_purchase_return_summary`

Important DB calls:

- `create_purchase_return`
- `update_purchase_return`
- `delete_purchase_return`
- `serial_exists_in_purchase_return`
- `get_serial_number_details`
- `get_last_purchase_return_id`
- `get_previous_purchase_return`
- `get_next_purchase_return`
- `get_current_purchase_return`
- `get_purchase_return_summary`

### `saleReturn`

Primary template:

- `templates/sale_return_templates/sale_return_template.html`

Views:

- `createSaleReturn`
- `sale_return_lookup`
- `get_sale_return`
- `get_sale_return_summary`

Important DB calls:

- `create_sale_return`
- `update_sale_return`
- `delete_sale_return`
- `serial_exists_in_sales_return`
- `get_serial_number_details`
- `get_last_sales_return_id`
- `get_previous_sales_return`
- `get_next_sales_return`
- `get_current_sales_return`
- `get_sales_return_summary`

### `payments`

Primary template:

- `templates/payments_templates/payment.html`

Views:

- `make_payment`
- `get_payment`
- `get_old_payments`
- `get_payments_date_wise`
- `get_party_balance`

Important DB calls:

- `make_payment`
- `update_payment`
- `delete_payment`
- `get_payment_details`
- `get_last_payment`
- `get_previous_payment`
- `get_next_payment`
- `get_last_20_payments_json`
- `get_payments_by_date_json`
- `get_party_balance_by_name`

Payment methods allowed by DB check constraint:

- `Cash`
- `Bank`
- `Cheque`
- `Online`

### `receipts`

Primary template:

- `templates/receipts_templates/receipt.html`

Views:

- `make_receipt`
- `get_receipt`
- `get_old_receipts`
- `get_receipts_date_wise`
- `get_party_balance`

Important DB calls:

- `make_receipt`
- `update_receipt`
- `delete_receipt`
- `get_receipt_details`
- `get_last_receipt`
- `get_previous_receipt`
- `get_next_receipt`
- `get_last_20_receipts_json`
- `get_receipts_by_date_json`
- `get_party_balance_by_name`

Receipt methods allowed by DB check constraint:

- `Cash`
- `Bank`
- `Cheque`
- `Online`

### `contra`

Primary template:

- `templates/contra_templates/contra.html`

Views:

- `make_contra`
- `get_contra`
- `get_old_contras`
- `get_contras_date_wise`
- `get_party_balance`

Important DB calls:

- `make_contra`
- `update_contra`
- `delete_contra`
- `get_contra_details`
- `get_last_contra`
- `get_previous_contra`
- `get_next_contra`
- `get_last_20_contras_json`
- `get_contras_by_date_json`
- `get_party_balance_by_name`

DB comment: `contra_entries` is for party-to-party transfers. It debits the to-party and credits the from-party, with no cash account movement.

### `accountsReports`

Primary templates:

- `templates/display_report_templates/accounts_reports_template.html`
- `templates/display_report_templates/stock_reports_template.html`
- `templates/display_report_templates/profit_reports_template.html`
- `templates/display_report_templates/monthly_reports_template.html`

Views:

- `detailed_ledger_view`
- `detailed_ledger2_view`
- `cash_ledger_view`
- `trial_balance_view`
- `receivable`
- `payable`
- `stock_report_view`
- `stock_summary`
- `stock__worth_report_view`
- `item_history_view`
- `item_detail_view`
- `serial_ledger_view`
- `serial_ledger_purchase_only_view`
- `serial_ledger_view_sale_price_hidden`
- `serial_ledger_sale_only_view`
- `items_last_purchasing`
- `items_last_sale`
- `company_valuation_report`
- `sale_wise_report`
- `monthly_position_report`
- `monthly_income_report`

Important DB calls:

- `detailed_ledger`
- `detailed_ledger2`
- `get_cash_ledger_with_party`
- `vw_trial_balance`
- `get_accounts_receivable_json_excluding`
- `get_accounts_payable_json_excluding`
- `stock_report`
- `stock_summary`
- `stock_worth_report`
- `item_transaction_history`
- `get_item_stock_by_name`
- `get_serial_ledger`
- `get_serial_ledger_purchase`
- `get_serial_ledger_sales`
- `item_last_purchase_view`
- `item_last_sale_view`
- `standing_company_worth_view`
- `sale_wise_profit`
- `monthly_company_position`
- `monthly_income_statement`

## Database Backup Details

Backup file:

- `db_backup_20260703_0000.sql`
- Size observed: about 3.7 MB
- Last modified locally: July 3, 2026

Object counts found in the dump:

- Tables: 29
- Views: 13
- Functions: 134
- Triggers: 11

### Business Tables

Core accounting:

- `chartofaccounts`
- `journalentries`
- `journallines`
- `generalledger` view
- `vw_trial_balance` view

Parties and items:

- `parties`
- `items`

Inventory and stock:

- `purchaseunits`
- `soldunits`
- `stockmovements`
- `stock_report` view
- `stock_worth_report` view
- `item_history_view`
- `item_last_purchase_view`
- `item_last_sale_view`

Transactions:

- `purchaseinvoices`
- `purchaseitems`
- `salesinvoices`
- `salesitems`
- `purchasereturns`
- `purchasereturnitems`
- `salesreturns`
- `salesreturnitems`
- `payments`
- `receipts`
- `contra_entries`

Django tables in the backup:

- `auth_group`
- `auth_group_permissions`
- `auth_permission`
- `auth_user`
- `auth_user_groups`
- `auth_user_user_permissions`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`

### Important Table Columns

`chartofaccounts`:

- `account_id`
- `account_code`
- `account_name`
- `account_type`
- `parent_account`
- `date_created`

`parties`:

- `party_id`
- `party_name`
- `party_type`
- `contact_info`
- `address`
- `ar_account_id`
- `ap_account_id`
- `opening_balance`
- `balance_type`
- `date_created`
- `created_by`

`items`:

- `item_id`
- `item_name`
- `storage`
- `sale_price`
- `item_code`
- `category`
- `brand`
- `created_at`
- `updated_at`
- `created_by`

`purchaseinvoices`:

- `purchase_invoice_id`
- `vendor_id`
- `invoice_date`
- `total_amount`
- `journal_id`
- `created_by`
- `description`
- `is_opening` may be required by `get_current_purchase`; normal invoices should use `false`

`purchaseitems`:

- `purchase_item_id`
- `purchase_invoice_id`
- `item_id`
- `quantity`
- `unit_price`

`purchaseunits`:

- `unit_id`
- `purchase_item_id`
- `serial_number`
- `in_stock`
- `serial_comment`

`salesinvoices`:

- `sales_invoice_id`
- `customer_id`
- `invoice_date`
- `total_amount`
- `journal_id`
- `created_by`
- `description`

`salesitems`:

- `sales_item_id`
- `sales_invoice_id`
- `item_id`
- `quantity`
- `unit_price`

`soldunits`:

- `sold_unit_id`
- `sales_item_id`
- `unit_id`
- `sold_price`
- `status`

`payments`:

- `payment_id`
- `party_id`
- `account_id`
- `amount`
- `payment_date`
- `method`
- `reference_no`
- `journal_id`
- `date_created`
- `notes`
- `description`
- `created_by`

`receipts`:

- `receipt_id`
- `party_id`
- `account_id`
- `amount`
- `receipt_date`
- `method`
- `reference_no`
- `journal_id`
- `date_created`
- `notes`
- `description`
- `created_by`

`contra_entries`:

- `contra_id`
- `from_party_id`
- `to_party_id`
- `amount`
- `contra_date`
- `method`
- `reference_no`
- `journal_id`
- `description`
- `notes`
- `created_by`
- `date_created`

`stockmovements`:

- `movement_id`
- `item_id`
- `serial_number`
- `movement_type`
- `reference_type`
- `reference_id`
- `movement_date`
- `quantity`

### Trigger Map

The dump defines these triggers:

- `trg_contra_insert`, `trg_contra_update`, `trg_contra_delete` on `contra_entries`
- `trg_party_insert` on `parties`
- `trg_payment_insert`, `trg_payment_update`, `trg_payment_delete` on `payments`
- `trg_receipt_insert`, `trg_receipt_update`, `trg_receipt_delete` on `receipts`
- `trg_soldunits_fix_ghost_stock` on `soldunits`

Trigger functions:

- `trg_contra_journal`
- `trg_party_opening_balance`
- `trg_payment_journal`
- `trg_receipt_journal`
- `trg_fn_soldunits_fix_ghost_stock`

### Backup Row Counts

Observed row counts from `COPY` blocks:

| Table | Rows |
| --- | ---: |
| `auth_group` | 31 |
| `auth_group_permissions` | 30 |
| `auth_permission` | 85 |
| `auth_user` | 7 |
| `auth_user_groups` | 89 |
| `auth_user_user_permissions` | 72 |
| `chartofaccounts` | 22 |
| `contra_entries` | 93 |
| `django_admin_log` | 88 |
| `django_content_type` | 6 |
| `django_migrations` | 34 |
| `django_session` | 47 |
| `items` | 265 |
| `journalentries` | 4,316 |
| `journallines` | 10,336 |
| `parties` | 224 |
| `payments` | 1,452 |
| `purchaseinvoices` | 194 |
| `purchaseitems` | 1,346 |
| `purchasereturnitems` | 34 |
| `purchasereturns` | 11 |
| `purchaseunits` | 9,084 |
| `receipts` | 1,670 |
| `salesinvoices` | 823 |
| `salesitems` | 1,424 |
| `salesreturnitems` | 55 |
| `salesreturns` | 29 |
| `soldunits` | 8,100 |
| `stockmovements` | 19,417 |

## Accounting and Inventory Concepts

The database uses double-entry accounting:

- `journalentries` is the header table.
- `journallines` stores debit/credit lines.
- `chartofaccounts` categorizes accounts as `Asset`, `Liability`, `Equity`, `Revenue`, or `Expense`.
- `generalledger` and `vw_trial_balance` provide reporting views.

Serial-number inventory is central:

- Purchase creates `purchaseitems` and one `purchaseunits` row per serial number.
- Sale links serial units through `soldunits`.
- Returns inspect serial status and update inventory/accounting through return functions.
- `stockmovements` records inventory movement history with `IN` or `OUT`.
- `serial_comment` is informational and does not affect accounting or valuation.

## Important Safety Notes

- The backup contains real application data, Django auth rows, password hashes, session rows, and admin logs. Do not publish it publicly.
- Do not rely on Django ORM migrations for the domain schema. The SQL backup is the source of truth for business tables.
- Before changing a flow, inspect both the Django view and the database function it calls.
- Changing SQL functions can affect multiple screens because create/update/delete, navigation, summaries, reports, and dashboard cards reuse the same stored procedures and views.
- Permission names are hard-coded in views. If permissions change, update both migrations/data and view checks.
- Some comments and older documentation have mojibake/encoding damage. New documentation should stay plain ASCII unless the file already requires Unicode.

## Known Operational Issue: Purchase `is_opening`

The purchase previous/next flow calls:

- Django: `purchase/views.py`
- DB functions: `get_previous_purchase`, `get_next_purchase`, `get_current_purchase`

If live logs show:

```text
column pi.is_opening does not exist
```

then the live database has a function/schema mismatch. The SQL function `get_current_purchase(bigint)` references `purchaseinvoices.is_opening`, but the table does not have that column.

Fix on Windows from the project root:

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute('ALTER TABLE public.purchaseinvoices ADD COLUMN IF NOT EXISTS is_opening boolean NOT NULL DEFAULT false;'); print('is_opening column ensured')"
.\venv\Scripts\python.exe manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute(\"SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='purchaseinvoices' AND column_name='is_opening';\"); print(cursor.fetchall())"
```

Fix on EC2/Linux from the project root:

```bash
./myvenv/bin/python manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute('ALTER TABLE public.purchaseinvoices ADD COLUMN IF NOT EXISTS is_opening boolean NOT NULL DEFAULT false;'); print('is_opening column ensured')"
./myvenv/bin/python manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute(\"SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='purchaseinvoices' AND column_name='is_opening';\"); print(cursor.fetchall())"
```

This is a schema compatibility fix. Existing normal purchase invoices default to `false`.

## Suggested Development Workflow

1. Identify the UI route in the relevant `urls.py`.
2. Read the matching Django view.
3. Find each SQL function/view/table the view calls.
4. Inspect `db_backup_20260703_0000.sql` for the function implementation and related tables/triggers.
5. Check matching JavaScript in `static/js/`.
6. Validate permission checks.
7. Test the full browser flow and database side effects.

## Disposable System Test Suite

The repository includes a production-independent PostgreSQL integration suite:

- Runner: `system_tests/run_system_tests.py`
- Usage: `system_tests/README.md`
- Latest detailed output: `system_tests/RESULTS.md`
- Confirmed failure backlog: `system_tests/FAILED_TESTS.md`

The runner creates a temporary database named with the `financee_test_` prefix,
restores the latest `db_backup_*.sql` found in the project root, applies
`production_fixes.sql` on top, creates uniquely named fixtures, runs the
database workflows and report/integrity checkpoints, writes `RESULTS.md`, and drops
the temporary database by default. It does not use Django's configured production
database.

The July 17, 2026 run found 8 defects (duplicate sale returns, sale updates
allowed while returns existed, sale-return delete/update after resale, and
qty/serial-count mismatches in create_sale). All 8 were fixed on July 18, 2026
in `production_fixes.sql`, together with additional hardening of the purchase
and return functions and user-friendly error messages surfaced through
`financee/db_errors.py`. See `FIXES.md` for root causes, fixes, and EC2
deployment steps. The July 18, 2026 run passes 60 of 60 tests.

The system runner now also exercises payment, receipt, and contra functions
through their complete create/update/delete lifecycles. Each case inspects the
linked journal: payments debit the vendor and credit cash, receipts debit cash
and credit the customer, and contra entries debit the destination party and
credit the source party without a cash line. Updates must replace the original
journal at the new amount; deletes must remove both source record and journal.
Zero amounts and same-party contra transfers are required to fail, followed by
the standard report and global accounting integrity checkpoint.

Verified on July 20, 2026 against a newly restored, production-independent
`financee_test_` PostgreSQL database with `production_fixes.sql` applied: all
72 system tests pass and the temporary database is removed. The generated
details are recorded in `system_tests/RESULTS.md`.

Party opening-balance system coverage verifies all supported posting shapes:
customer debit openings post to the party AR side, vendor credit openings post
to the party AP side, and expense openings debit the generated expense account;
each balances against Owner's Capital. Updating an opening must replace the old
journal at the new amount, while setting it to zero must remove the opening
journal completely. Every party-opening slice ends with report and integrity
checks.

Verified after party-opening coverage on July 20, 2026: all 78 PostgreSQL
system tests pass after restoring the latest backup and applying
`production_fixes.sql`; the uniquely prefixed temporary database is removed.
Failed system cases now retain their traceback in `RESULTS.md` so CI failures
identify the exact runner location instead of reporting only an exception type.

Duplicate/concurrency system coverage rejects repeated purchase serials both
inside one invoice and across separate invoices, verifying the unique unit and
source invoice remain intact. A real two-connection race synchronizes two
transactions attempting to sell the same stocked serial; the required invariant
is exactly one committed sale, one database rejection, one active sold-unit row,
and an out-of-stock purchase unit, followed by the standard report checkpoint.

The first concurrency run exposed a real race: both simultaneous sales could
commit because `create_sale` read `in_stock` without locking the purchase unit.
`production_fixes.sql` now uses `FOR UPDATE OF pu`. A partial unique index was
evaluated but cannot yet be applied because the production-origin backup has
historical duplicate active sold rows; they require deliberate review rather
than automatic deletion. The row-lock SQL patch must be applied again to
production during a controlled deployment after taking a backup.

Verified after duplicate-serial and concurrency coverage on July 20, 2026: all
83 PostgreSQL system tests pass with the latest backup plus the updated SQL
patch, and the temporary database is removed. The race now produces exactly one
commit and one stock-availability rejection.

Numeric/date boundary system coverage exercises purchase and sale rejection of
zero, negative, and fractional quantities; negative and nonnumeric prices; and
missing invoice dates. Cash-flow coverage verifies that one cent posts to a
balanced journal while numeric overflow and invalid calendar dates are blocked.
Account, cash, profit, and monthly reports must execute for the valid leap-day
boundary `2024-02-29`.

Verified after numeric/date boundary coverage on July 20, 2026: all 91
PostgreSQL system tests pass against the restored backup plus
`production_fixes.sql`, and the temporary database is removed.

The final system-test expansion covers purchase-return mutation: updating a
two-serial vendor return to one must restore only the removed serial, invalid
empty/duplicate updates must be atomic, and deletion must restore stock while
removing the return header and journal. Report reconciliation compares customer
and vendor raw journal debit/credit/balance totals with
`get_party_balance_by_name`, the party row in `vw_trial_balance`, and every row
plus the ending running balance from `detailed_ledger`.

Verified after completing the planned PostgreSQL expansion on July 20, 2026:
all 98 system tests pass against the latest restored backup with
`production_fixes.sql` applied, and the temporary database is removed. The
payment/receipt/contra, party opening, concurrency, duplicate serial, boundary,
return mutation, and report-to-journal roadmap item is complete.

`REGRESSION_CASES` in the PostgreSQL runner maps confirmed defects 1-9 to their
named behavioral cases. A dedicated manifest case inspects the accumulated
results and fails if a mapped regression is missing or did not pass. The closed
backlog in `system_tests/FAILED_TESTS.md` now includes the concurrency defect
and the current defect-to-test mapping instead of the stale 60-test summary.

Verified after enabling the executable regression manifest on July 20, 2026:
all 99 PostgreSQL system tests pass and the disposable database is removed.

Production-stack smoke coverage uses `docker-compose.smoke.yml`, which contains
only smoke credentials, a tmpfs PostgreSQL database, disposable Redis/static
storage, and a localhost-only nginx port. `scripts/smoke_production_stack.sh`
builds and waits for the stack, checks nginx syntax, proxies `/health/` and the
login page, verifies a collected CSS asset plus immutable cache headers, and
always removes containers, networks, and volumes. `/health/` reports ready only
after both PostgreSQL `SELECT 1` and a cache write/read succeed; failures return
a generic 503 without internal details. The production web health check now
uses this readiness endpoint instead of merely rendering the login page.

Verified on July 20, 2026: all 141 Django tests pass with zero system-check
issues, and the isolated production-stack smoke script passes PostgreSQL/Redis/
Gunicorn/nginx startup, readiness, proxy, static-file, and cache-header checks.
Both test stacks removed their disposable containers, networks, databases, and
volumes after execution.

If new failures appear, treat `system_tests/FAILED_TESTS.md` as the remediation
backlog. After changing the stored procedures, rerun the complete suite rather
than testing only the affected case, because sale returns and invoice mutations
also affect stock, journals, reports, and profit calculations.

## Known Documentation Corrections

The previous `README.md` had encoding damage and some stale claims. This documentation reflects the files observed in this repository and the included SQL backup as of July 3, 2026.

## Automated Testing and Delivery Roadmap

`TODO.md` is the authoritative checklist for testing and CI/CD. The agreed
solo-developer flow is `push to main -> CI tests/build -> GitHub production
approval -> EC2 deploy`; pull requests and feature branches are not required.

The first foundation slice adds authentication endpoint/session/CSRF tests in
`authentication/tests.py` and safe PostgreSQL error translation tests in
`financee/test_db_errors.py`. Only curated PostgreSQL `P0001` messages may reach
users; other database failures must use a generic fallback.

Full integration tests must use isolated PostgreSQL because the system depends
on stored functions, triggers, views, JSONB, and PostgreSQL-specific SQL. SQLite
is not a valid substitute. CI must refuse production database names and hosts.

The isolated Django test configuration is `financee/test_settings.py`. It
requires an explicit `TEST_DB_NAME` beginning with `financee_test_`, rejects the
known production hosts and the configured production database name, disables
persistent connections and external Redis, and uses faster test-only password
hashing. `.env.test.example` documents safe non-production variables.

`financee/test_support.py` provides shared user creation and custom `auth`
permission helpers. Business endpoint test modules should reuse these helpers
instead of duplicating permission setup.

`docker-compose.test.yml` runs Django tests against PostgreSQL 16 in a `tmpfs`
data directory. It has a separate Compose project name, no host ports, no named
production volume, test-only credentials, and no dependency on production
`.env` values. The container connects through PostgreSQL's `postgres`
maintenance database and Django creates/destroys the guarded
`financee_test_ci` database. Run it with:

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
docker compose -f docker-compose.test.yml down --remove-orphans
```

Test settings use plain static-file storage so template tests do not require a
production `collectstatic` manifest. Endpoint tests replace only the connection
reference inside the view module; patching `django.db.connection.cursor`
directly is forbidden because it also intercepts authentication, sessions, and
test transaction management.

The PostgreSQL error-helper tests use exception-derived cause objects with
`pgcode` and `diag.message_primary` attributes, matching Python's exception
chaining rules and the relevant psycopg2 interface.

Verified baseline on July 20, 2026: the Docker test stack created
`financee_test_ci`, applied Django migrations, reported zero system-check
issues, passed all 26 authentication/party/error-helper tests, and destroyed the
test database successfully.

`items/tests.py` now applies the same endpoint-contract strategy to item
management: login and permission enforcement, view-only restrictions, template
rendering, autocomplete parameters, list serialization, duplicate handling,
normalized create/update procedure payloads, creator attribution, CSRF, and
generic handling of non-curated database failures. The view module's connection
reference is mocked while Django's real authentication/session connection stays
untouched.

Verified after adding item coverage on July 20, 2026: all 41 Django tests pass
against the ephemeral PostgreSQL 16 stack with zero system-check issues, and the
guarded test database is destroyed successfully.

`sale/tests.py` starts transaction endpoint coverage with sale-page access,
malformed submit/delete requests, CSRF, individual serial lookup state, pasted
bulk-serial parsing/deduplication/grouping, invalid serial reporting, invoice
navigation validation/payloads, and summary date/default-result contracts.
Database-facing endpoint tests replace only the sale view module's connection.

Verified after the first sales slice on July 20, 2026: all 57 Django tests pass
against ephemeral PostgreSQL 16 with zero system-check issues, followed by
successful destruction of the guarded test database.

Payment, receipt, and contra endpoint tests now cover page access, CSRF,
normalized create/update stored-function payloads, creator attribution,
navigation/date/balance input validation, balance response contracts, contra
same-party rejection, and contra deletion.

Verified after the first cash-flow endpoint slice on July 20, 2026: all 105
Django tests pass against ephemeral PostgreSQL 16 with zero system-check issues
and successful destruction of the guarded test database.

`home/tests.py` covers dashboard authentication, every widget permission,
PostgreSQL function and parameter contracts for sales/stock/parties/transactions/
expenses/alerts, GET-only enforcement, cache hits and disabled-cache behavior,
and permission-based hiding on legacy financial endpoints.

Verified after dashboard coverage on July 20, 2026: all 116 Django tests pass
against ephemeral PostgreSQL 16 with zero system-check issues and successful
test-database destruction.

`accountsReports/tests.py` covers every account, cash, stock, item, serial,
profit, valuation, and monthly report route. It verifies authentication and
the custom permission combinations, each template family, date/number/required
field validation, item/serial normalization, exact PostgreSQL function/view
contracts, row and JSON response shaping, no-data responses, and HTTP method
handling. Database calls are mocked at the report view module boundary; report
calculation correctness remains part of the PostgreSQL system-test layer.

Verified after report coverage on July 20, 2026: all 131 Django tests pass
against ephemeral PostgreSQL 16 with zero system-check issues and successful
destruction of the guarded test database. The receivables report's leftover
response-type debug print was removed after it appeared in the test output.

`financee/test_smoke.py` provides a centralized presentation-layer guard. It
discovers and compiles every HTML file under `templates/`, extracts every
literal Django `{% static %}` dependency and resolves it through Django's
configured static-file finders, and rejects empty custom CSS/JavaScript files.
Together with the authenticated page-render assertions in each endpoint suite,
this covers the roadmap's HTML/template/static smoke-test checkpoint without
depending on production data.

Verified after presentation smoke coverage on July 20, 2026: all 134 Django
tests pass against ephemeral PostgreSQL 16 with zero system-check issues and
successful destruction of the guarded test database.

`financee/test_security.py` centrally enforces CSRF rejection for login and all
11 business mutation routes (party/item creation and update, payment, receipt,
contra, purchase, sale, and both return directions). `financee/http_errors.py`
provides the shared JSON 500 boundary: unexpected details are logged server-side
while clients receive only a fixed generic message. Report and cash-flow JSON
exception paths use this boundary so SQL text, schema details, credentials, and
internal hostnames cannot be reflected in HTTP responses.

Verified after centralized CSRF and error-disclosure coverage on July 20, 2026:
all 138 Django tests pass against ephemeral PostgreSQL 16 with zero system-check
issues and successful destruction of the guarded test database. The deliberate
report exception is logged with its traceback while the HTTP response remains
generic.

Sales coverage now includes the fully validated mutation branches. Tests verify
create/update/delete permissions, the view-only group, stored-function argument
contracts, JSON item/serial payloads, creator IDs, trimmed description writes,
database validation rejection for returned serials, and sanitization of delete
validation failures.

Verified after completing sales mutation coverage on July 20, 2026: all 65
Django tests pass against ephemeral PostgreSQL 16 with zero system-check issues.
The deliberate internal-error case is logged server-side while its SQL details
remain absent from the HTTP response.

`purchase/tests.py` covers purchase-page access, malformed requests, CSRF,
create/update/delete permissions and procedure contracts, the view-only group,
creator attribution, description persistence, database validation blocking,
navigation, summaries, and classification of new, stocked, and historic serials.

Verified after purchase coverage on July 20, 2026: all 81 Django tests pass
against ephemeral PostgreSQL 16 with zero system-check issues and successful
test-database destruction.

`saleReturn/tests.py` and `purchaseReturn/tests.py` cover return-page access,
CSRF, serial availability lookup, create/update/delete permissions and stored
function arguments, creator IDs, description persistence, and invalid
navigation/summary inputs for both customer and vendor return directions.

Verified after the paired return slice on July 20, 2026: all 92 Django tests
pass against ephemeral PostgreSQL 16 with zero system-check issues and
successful destruction of the guarded test database.

The first business endpoint slice is in `parties/tests.py`. It covers login and
`view_party` enforcement, authorized template rendering, autocomplete query
parameters and JSON results, list endpoint authorization and serialization, and
CSRF rejection for party creation. Database reads are mocked in these endpoint
contract tests; stored-procedure behavior remains the responsibility of the
isolated PostgreSQL integration suite.

Party endpoint coverage now also verifies create permission and view-only-group
restrictions, duplicate-name behavior, normalization of create/update payloads,
`created_by_id` propagation, and AJAX update selection validation. Test setup
clears Django's permission caches between cases so authorization tests remain
independent and order-agnostic.

`TODO.md` begins with a prominent production action warning: take and verify a
PostgreSQL backup, then reapply the updated `production_fixes.sql` before the
next production deployment. The concurrency patch has only been exercised in
disposable databases and has not changed production.

## Coverage Gate

Coverage is measured with branch tracking across the 13 Django application and
project packages. Migrations, tests, test settings/support, system tests, and
the management launcher are excluded; production modules, including admin and
WSGI/ASGI entry points, remain in scope. The July 20, 2026 baseline is 57.4% over
3,379 production Python statements. The enforced initial floor is 55%, which
prevents meaningful erosion while allowing a small margin for coverage-version
rounding. Current priority gaps are `financee/admin_site.py` (13%), payments and
receipts views (39%), and both return view modules (49%).

`.coveragerc` owns the scope and threshold. `requirements-test.txt` and
`Dockerfile.test` keep coverage tooling out of the production image, and
`scripts/run_django_tests.sh` is the single container entry point for the
branch-aware Django test run. `docker-compose.test.yml` builds that dedicated
test image and runs the script against ephemeral PostgreSQL 16.

## Canonical Test Commands

Use `scripts/run_fast_tests.sh` during normal development. It builds the
test-only image, runs all Django endpoint/security/presentation tests against
ephemeral PostgreSQL, enforces the branch-coverage floor, propagates the test
exit status, and removes its containers, network, and temporary storage.

Use `scripts/run_full_tests.sh` before delivery and in the required CI check. It
runs the fast suite first, then all restored-backup PostgreSQL procedure,
accounting, concurrency, regression, and integrity scenarios, and finally the
production-shaped PostgreSQL/Redis/Gunicorn/nginx smoke suite. Execution stops
at the first failing stage. Every stage has its own cleanup trap.

The database procedure stage is isolated by `docker-compose.system-test.yml`.
It exposes no host port, stores PostgreSQL data in `tmpfs`, uses test-only
credentials, and builds `Dockerfile.system-test` with the required `psql`
client. Its Dockerfile-specific ignore rules include the repository's latest
`db_backup_*.sql` in this test image while the production `.dockerignore`
continues excluding database backups from the production image. The system
runner accepts the fixed Compose hostname `system-test-db`
in addition to loopback/Unix-socket connections; all arbitrary remote hosts and
database names without the generated `financee_test_` prefix remain rejected.
Concurrent-sale worker connections explicitly reuse `TEST_PGPASSWORD`, because
libpq deliberately omits passwords from an established connection's exposed
DSN; this keeps the race test portable between peer-authenticated local servers
and the password-authenticated Compose database.

Verified end to end on July 20, 2026 through
`scripts/run_full_tests.sh`: 141 Django tests passed with 57.4% branch-aware
coverage, all 99 restored-backup PostgreSQL system scenarios passed, and the
production-shaped smoke checks passed. The command returned zero only after all
three stages succeeded, and all disposable containers, networks, databases,
volumes, and `tmpfs` storage were removed.

## Deterministic Fixture Contract

Django endpoint tests create their own users and permissions inside Django's
fresh test database, use literal request dates, mock only module-local database
boundaries, and do not load fixture files or production data.

The PostgreSQL runner uses the latest backup only to obtain the production
schema, views, triggers, and stored functions. After applying
`production_fixes.sql`, `reset_fixture_data()` truncates every public table
except `chartofaccounts`, resets table sequences, deletes all non-core chart
rows, and resets the chart sequence. Exactly these seven named reference
accounts remain: Accounts Payable, Owner's Capital, Sales Revenue, Cost of Goods
Sold, Cash, Accounts Receivable, and Inventory. A first-class system test fails
unless all business tables are empty and this exact account set exists before
scenario setup.

All runner-authored accounting transactions use the fixed date `2026-01-15`.
Report reconciliation uses a deterministic `2099-12-31` upper bound so it also
includes return functions that assign their dates within PostgreSQL. Fixture
names remain run-prefixed for diagnostic clarity, but every assertion is scoped
to records created by the suite. Verified July 20, 2026: the sanitized baseline
passes all 100 PostgreSQL scenarios with zero restored business rows.

## Dependency Lock Policy

`requirements.txt` pins every installed production Python package, including
the transitive asgiref, packaging, and sqlparse dependencies. The tested
production resolution is Django 5.2.16, django-environ 0.14.0, Gunicorn 26.0.0,
psycopg2-binary 2.9.12, Redis client 8.0.1, asgiref 3.12.1, packaging 26.2,
and sqlparse 0.5.5. `requirements-test.txt` extends that exact production set
with coverage 7.15.2.

All three Dockerfiles pin the Python 3.12 slim multi-architecture manifest by
SHA-256 digest. Production, test, system-test, and smoke Compose definitions
also pin PostgreSQL 16; applicable stacks pin Redis 7 Alpine and nginx Alpine
by immutable multi-architecture digest. Readable tags remain alongside digests,
but the digest controls the pulled content. This keeps ARM64 EC2 and a potential
x86_64 CI runner on the same published image release for their architecture.

Dependency upgrades must update explicit versions/digests in one reviewed
change and pass `scripts/run_full_tests.sh`; floating ranges or unreviewed tag
refreshes must not be reintroduced. Verified July 20, 2026: all images rebuilt
from the pinned declarations, 141 Django tests passed at 57.4% coverage, all
100 PostgreSQL system scenarios passed, and production-stack smoke passed.

## Redis Integration Test Contract

`docker-compose.test.yml` now starts an unexposed, persistence-disabled Redis 7
service and points Django test settings at logical database 15 through
`TEST_REDIS_URL`. The setting accepts only `redis`/`rediss` URLs on loopback or
the fixed `test-redis` Compose hostname; arbitrary remote Redis hosts are
rejected. When the variable is absent, local test runs retain the isolated
in-process cache and Redis-specific cases skip cleanly.

`financee/test_redis.py` verifies Django Redis serialization and round trips
through two independent cache clients, confirms that timeouts reach Redis, and
forces server-side expiry before proving Django returns a miss. Because the
whole Docker Django suite now uses Redis, the pre-existing dashboard hit/miss,
cache-disabled, and readiness endpoint tests also exercise the real backend.
Each test clears logical database 15, while Compose disables snapshots and AOF
and removes the container/network after the run.

Verified July 20, 2026: all 143 Redis-enabled Django tests passed against
ephemeral PostgreSQL and Redis with zero Django system-check issues; branch
coverage remained 57.4%, and both disposable services were removed.

## Disposable Schema and Patch Pipeline

`system_tests/run_system_tests.py` exposes the database preparation stages
explicitly and executes them in this order: create a guarded disposable
database, restore the latest repository backup once, remove restored data and
reset reference fixtures, reserve the required patch by filename and SHA-256,
execute `production_fixes.sql` through `psql`, then mark the ledger row applied.

The patch ledger exists only in the disposable `system_test_meta` schema. Its
primary key prevents a patch filename from being reserved twice. A reservation
is committed before patch execution, while `production_fixes.sql` supplies its
own all-or-nothing transaction; only a successful `psql` exit can transition
the ledger from `applying` to `applied`. Missing patches, checksum mismatch,
duplicate reservation, patch failure, and ledger-finalization failure all stop
the suite before business tests.

The system preflight independently queries the ledger and requires exactly one
row for `production_fixes.sql`, with the SHA-256 calculated from the file being
tested and status `applied`. Verified July 20, 2026: the ordered pipeline and
all 101 PostgreSQL system scenarios pass, and the disposable database is
removed afterward.

## CI-Ready Quality Gate

`scripts/run_quality_checks.sh` validates every maintained shell script with
`sh -n`, parses the test/system/smoke Compose definitions, builds the pinned
test image, byte-compiles all Python project/test packages, and runs Django's
normal system checks with warnings treated as failures. It then runs
`manage.py check --deploy` under an explicit hardened production profile and
also fails on any deployment warning. Every temporary Compose resource is
removed by a cleanup trap.

The production settings now expose environment-controlled SSL redirect,
secure-cookie, HSTS, and trusted-forwarded-protocol controls. Their defaults
remain off because the current production origin-TLS state has not yet been
verified; this deliberately preserves current production behavior. The quality
gate supplies secure values to prove the deployment configuration is valid.
Those production variables must be enabled only after Cloudflare Full (strict)
and the nginx origin certificate are confirmed, as tracked separately in
`TODO.md`.

`scripts/run_full_tests.sh` now runs the quality gate before any test suite, then
executes the Redis-enabled Django/endpoint suite, restored-schema PostgreSQL
system suite, and production-shaped smoke suite. Verified July 20, 2026: both
Django check modes reported zero issues, all 143 Django tests passed at 57.4%
branch-aware coverage over 3,387 statements, all 101 PostgreSQL scenarios
passed, and the final nginx/Redis/PostgreSQL/Gunicorn smoke checks passed.

## GitHub CI and Test Artifacts

`.github/workflows/ci.yml` is the first active GitHub Actions workflow. It runs
on every push to `main` and by manual dispatch, grants the job read-only
repository contents permission, cancels superseded runs on the same ref, limits
the job to 30 minutes, and invokes only the canonical
`scripts/run_full_tests.sh` command. Artifact publication uses `if: always()`
so diagnostics survive a failed test step, and retains results for 14 days.

The Django test container bind-mounts the ignored local `artifacts/` directory.
`scripts/run_django_tests.sh` preserves the original test exit status while
writing `django-tests.log`; when coverage data exists it also writes the human
report `coverage.txt`, Cobertura-compatible `coverage.xml`, and detailed
`coverage.json`. A coverage-floor failure still produces all reports and fails
the command. `scripts/run_system_tests.sh` removes stale output before each run
and copies the newly generated system report to
`artifacts/postgresql-system-tests.md` during cleanup, including failure runs.
Neither database dumps nor environment files are included in the upload path.

Verified locally July 20, 2026: the workflow YAML parses, the full suite passes,
and all five expected artifacts are generated outside the containers. The
workflow itself becomes active only after this change is committed and pushed
to GitHub.

Repository security note: `db_backup_20260718_0000.sql` is currently tracked
despite `.gitignore` documenting that production backups must never enter Git.
The system suite presently needs it as its schema/function source, so removing
it without a sanitized replacement would break CI. `TODO.md` now records the
required remediation: create a sanitized schema fixture, switch tests to it,
purge the production-origin dump from Git history, and audit/rotate any secrets
that may have been committed. CI artifact paths explicitly exclude the dump.

## GitHub Build Cache

The CI workflow sets up Docker Buildx and prebuilds the Django test,
PostgreSQL-system-test, and production-smoke application images before running
the canonical suite. Each build imports and exports a separate GitHub Actions
BuildKit cache scope (`django-test`, `postgres-system-test`, and `production`)
with maximum layer retention, preventing the images from overwriting one
another's cache. Python dependency installation layers are therefore reused
when their pinned requirements and Dockerfile inputs have not changed.

The three prebuilt images are loaded under the exact Compose-generated local
tags. CI sets `SKIP_DOCKER_BUILD=1`, causing quality, fast, system, and smoke
scripts to reuse those images; ordinary local execution still builds by
default. This avoids the former duplicate builds while preserving one set of
canonical scripts for both environments.

Only immutable build inputs and image layers enter the cache. PostgreSQL test
data remains in `tmpfs`, Redis snapshots/AOF remain disabled, Django's test
database is destroyed, and every Compose cleanup still removes containers,
networks, and volumes. Verified locally July 20, 2026: the full suite passes in
prebuilt-image reuse mode without any Docker build step—143 Django tests at
57.4% coverage, 101 PostgreSQL scenarios, and the production-stack smoke suite.
GitHub cache import/export will be confirmed by the next pushed workflow run.

## Commit-Tagged ARM64 Production Artifact

The CI workflow now has a `build-production-image` job with an explicit
dependency on the complete `test` job. GitHub therefore cannot build or publish
a deployable artifact when any quality, Django, PostgreSQL, Redis, or stack
smoke check fails. The job uses QEMU and Buildx to build the production
`Dockerfile` specifically for `linux/arm64`, matching the AWS Graviton
architecture of the EC2 `t4g.large` host.

The image has exactly one workflow tag, `financee:<full Git commit SHA>`; no
deployable `latest` tag is produced. The same SHA is embedded in the image's
`org.opencontainers.image.revision` label through the `VCS_REF` build argument.
Buildx exports a Docker-loadable `production-image.tar`, and the workflow saves
the BuildKit image digest, archive SHA-256, platform, tag, and source commit in
`image-metadata.txt`. Both files are published together as the short-lived
`production-image-<commit SHA>` GitHub artifact with seven-day retention and no
additional compression. This creates the immutable handoff for the later
approval-gated deployment job without granting CI production access or changing
the EC2 instance.

Local verification covers workflow syntax, image architecture, revision label,
archive loading, and metadata consistency. The GitHub-hosted ARM64 export and
artifact publication must be confirmed by the next pushed workflow run.

GitHub run `1ed4cb097d458357436ae0e2e2fef953a0ced4f3` subsequently passed both
the complete test job and ARM64 image-build job and published the expected
`production-image-1ed4cb097d458357436ae0e2e2fef953a0ced4f3` artifact. This
confirms the hosted runner can create the intended deployment handoff.

## Production Approval Boundary

The workflow now contains an `authorize-production` job chained through
`needs: build-production-image`; that build is itself chained through
`needs: test`. The job targets the GitHub Environment named `production` and
uses a non-cancelling `production-deployment` concurrency group. Once the
environment has a required-reviewer protection rule, a push cannot enter this
job until every test and image-build requirement passes and the solo developer
approves it in GitHub.

After approval, the job downloads only the artifact whose name contains the
current workflow commit. Before any future deployment step can use it, the job
requires matching commit, image tag, and ARM64 platform metadata; recomputes
and verifies the archive SHA-256; loads the Docker archive; and inspects its
architecture and embedded OCI revision label. A mismatch stops the job. No EC2
credentials, secrets, network connection, or production mutation are part of
this milestone.

GitHub Environment protection is repository configuration and cannot be
enforced by workflow YAML alone. `DEPLOYMENT_GUIDE.md` records the one-time UI
steps. The next pushed run must demonstrate that `authorize-production` pauses
for review and passes artifact validation only after approval.

The workflow at commit `f8b9555` subsequently paused at the protected
`production` Environment as intended. After manual approval, all three jobs—
tests, ARM64 artifact creation, and release authorization/validation—passed.
This proves both the dependency chain and GitHub approval rule.

## Read-Only EC2 Deployment Preflight

The approved production job now establishes SSH using only environment-scoped
values: `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_SSH_KEY`, and a
pre-verified `PRODUCTION_KNOWN_HOSTS` entry. The non-sensitive absolute project
directory is supplied as the `PRODUCTION_PATH` Environment variable. Strict
host-key checking, batch mode, and an explicitly selected key are mandatory;
the workflow does not learn or trust a host key on first use.

After the local release artifact passes checksum, architecture, tag, and
revision validation, the workflow opens a read-only SSH session. It requires
an ARM64 kernel, Docker Engine, the Compose plugin, the existing production
directory, a readable `.env`, and a Compose configuration that renders
successfully. This preflight does not copy artifacts, pull source, build an
image, execute SQL, or change containers. Its purpose is to prove the secret
contract and server prerequisites before deployment automation is introduced.

`DEPLOYMENT_GUIDE.md` documents the four environment secrets and one variable.
The next pushed run will fail safely unless those values have first been added
to the protected `production` Environment; after approval it must report
`Production preflight passed without changing the host.`

GitHub commit `0ea3dcf` subsequently passed all three jobs. The approved job's
remote log ended with `Production preflight passed without changing the host.`,
proving the environment-scoped credentials, strict host-key entry, ARM64 host,
Docker/Compose installation, production path, `.env`, and existing Compose
configuration are valid.

## Immutable Deployment Compose Configuration

`docker-compose.deploy.yml` is a narrow production-only override. Its web
service requires `RELEASE_IMAGE` and explicitly clears the base file's
`build: .` field through Compose's `!reset` directive. When merged with
`docker-compose.yml`, the rendered web
service therefore references only `financee:<full commit SHA>` and has no build
configuration. Future deployment commands must use both files plus
`--no-build`, providing a second guard against rebuilding source on EC2.

This milestone changes no workflow deployment behavior and no EC2 state. Local
validation renders the merged Compose model using a representative 40-character
commit tag and checks that the web image is exact and the build field is absent.

GitHub commit `64e8c06` subsequently passed all three jobs, confirming the
immutable Compose override did not regress the established CI and approval
path.

## Commit-Specific EC2 Release Staging

The approved job now checks out only the deployment configuration in addition
to downloading the already-built artifact. After the proven read-only
preflight, it requires free EC2 disk space equal to at least twice the archive
size and creates a mode-0700 directory at
`<PRODUCTION_PATH>/releases/<full commit SHA>`. The SHA is checked as exactly 40
lowercase hexadecimal characters before it becomes part of a server path.

SCP uses the same pinned host key and explicit deployment identity to transfer
the image archive, its metadata, and `docker-compose.deploy.yml`. EC2 repeats
the commit/tag/platform assertions and archive SHA-256 verification before
loading the image. It then independently inspects ARM64 architecture and the
embedded revision label and renders the merged deployment Compose model with
the exact `financee:<commit SHA>` image.

This stage deliberately stops before `docker compose up`: it writes the
commit-specific release directory and loads an unused image into Docker, but
does not change any running container or database. The next pushed approved run
must end with `Release <commit SHA> staged and verified; running containers were
not changed.` before backup, SQL-patch, health-check, and rollback automation is
allowed to proceed.

GitHub commit `3b47ea8` subsequently passed all three jobs. EC2 reported that
the exact image was loaded as
`financee:3b47ea8700ebcda50eae4aa00014345d8f4d90f0` and that the release was
staged and verified without changing running containers.

## Verified Pre-Deployment PostgreSQL Backup

The staged release now also contains the repository's exact
`production_fixes.sql`; GitHub calculates its SHA-256 before transfer and EC2
must reproduce that checksum. The patch is not executed at this stage.

After image staging, the approved workflow streams `pg_dump --format=custom`
from the running database container into a temporary file under the existing
host-only `backups/` directory. It requires non-empty output and has the
container's matching `pg_restore` parse its manifest before atomically renaming
the file to `predeploy-<full commit SHA>.dump`. The resulting backup and checksum
are mode 0600. A final checksum check and a restore manifest of more than ten
lines are mandatory. Re-running a commit validates and reuses its backup rather
than overwriting it. Restore-manifest checks stream the mode-0600 host file to
the container over stdin, so validation does not weaken backup permissions or
depend on matching host/container numeric user IDs.

The backup remains only on EC2 and is never returned as a GitHub artifact. This
step takes a consistent database snapshot but does not execute SQL or change
running containers. The next approved run must confirm the checksum and
manifest before live deployment and patch application can be implemented.

GitHub commit `82869fa` subsequently created and verified
`predeploy-82869fa5f103d5792a75ccb54ae7f1070ba829cc.dump` on EC2. Its SHA-256
check passed and the matching PostgreSQL `pg_restore` reported 440 manifest
lines. No production data or running container was changed.

## Running-Image Rollback Anchor

The approved workflow now resolves the running Compose web container before
any live release change, requires it to be in the running state, and obtains
its immutable Docker image ID. That exact image ID is tagged as
`financee:rollback-before-<new commit SHA>`. This works for the existing
manually built production image even when it has no commit tag or OCI revision
label.

The workflow atomically writes mode-0600 `rollback-metadata.txt` into the new
release directory with the previous container ID, image ID, optional revision,
rollback tag, and UTC capture timestamp. It then proves the rollback tag still
resolves to the captured image ID. Tagging an existing image changes only
Docker image metadata; the running application and database are untouched. The
next approved run must confirm this rollback anchor before SQL or container
changes are introduced.

GitHub commit `7b638cb` subsequently preserved the live web image as
`financee:rollback-before-7b638cb05d6f8643664f0c1098d379b89ec212fb` and
verified that the running containers were unchanged. The rollback anchor is
therefore proven on the production Docker host.

## Automatic Production SQL Patch Ledger

The approved workflow now crosses the first live-change boundary only after
the tested artifact, remote checksum, verified custom-format backup, and exact
running-image rollback tag all succeed. It rechecks the backup checksum and
creates `deployment_meta.sql_patches` in PostgreSQL, recording patch SHA-256,
filename, triggering source commit, backup filename, and server timestamp.

If the staged `production_fixes.sql` checksum is absent from that ledger, the
workflow runs it using the database container's matching `psql`, with
`ON_ERROR_STOP` in addition to the patch's own `BEGIN`/`COMMIT`. Any SQL error
therefore stops and rolls back the function replacement before deployment. The
complete diagnostic output is retained only on EC2 as mode-0600
`production-fixes.log`, and the success marker is required before inserting the
ledger row. An already-recorded checksum is skipped, making repeated workflow
runs idempotent. A final query requires exactly one matching ledger row.

This milestone updates stored function definitions but still does not restart
or replace application containers. The next approved run is intentionally the
required production reapplication identified at the top of `TODO.md`; its log
and ledger must be confirmed before that warning can be marked resolved.

The first production attempt at commit `38db277` stopped before patch execution.
The backup checksum passed and PostgreSQL created the empty
`deployment_meta.sql_patches` table, but the remote POSIX shell treated an
indented `RECORD_SQL` terminator as heredoc content and ended with
`expecting ";;"`. No function was replaced, no patch row was inserted, and no
container was changed. The terminator is now aligned at column zero in the
rendered remote script, and that remote body is validated directly with
Ubuntu-compatible `dash -n` in addition to whole-workflow YAML/shell checks.

The corrected run at commit `42db5e2` verified its backup, applied the patch
successfully, inserted one ledger row, and reported checksum
`dd9d152e6d808bd658be51fbe3db042a0519449084ba60e617c1494cc288e189`.
The required production SQL action is therefore complete and recorded.

## Live Image Switch and Automatic Rollback

The approved job now reaches `docker compose up` only after every preceding
test, artifact, approval, remote checksum, backup, rollback-image, and SQL-ledger
gate succeeds. It combines the base and deployment override, supplies only
`financee:<current commit SHA>`, passes `--no-build`, and recreates the web and
nginx services while leaving PostgreSQL and Redis running.

The remote verifier allows three minutes for the web container to become
running and healthy. It also requires the container image ID to equal the
approved image and requires the nginx-served loopback health endpoint to return
exactly `{"status": "ok"}`. A successful release atomically records
`deployment-result.txt` and `.deployed-commit` with image and UTC timing data.

Any startup, image-identity, container-health, or HTTP-health failure triggers
an immediate Compose recreation with the previously captured rollback tag. The
same health checks must pass for rollback; even a successful rollback leaves
the GitHub job failed so the release cannot be mistaken for success. Failure of
both release and rollback is reported as critical with Compose status. This is
the first milestone that intentionally changes running production containers.

GitHub commit `7694a64` completed the first immutable deployment. Compose
recreated the web container from
`financee:7694a646bacb1d67fa8457f206764c1211f04901`, kept PostgreSQL and Redis
healthy, and reported that both container and loopback HTTP health checks
passed. The deployment, health, rollback preparation, and release-recording
roadmap items are therefore proven.

## Public Post-Deployment Smoke Gate

The production Environment now also supplies non-sensitive `PRODUCTION_URL`,
which must be an HTTPS origin without a trailing slash. After internal image,
container, and nginx health succeeds, the GitHub runner tests the public route
through Cloudflare: exact `/health/` JSON, HTTP 200 from the login page, and the
expected immutable cache header from the login stylesheet. Each public group is
retried three times with bounded requests.

Public smoke failure is inside the same rollback decision as internal health
failure. The workflow restores the preserved image and requires both internal
and public checks to pass; the GitHub run remains failed after a healthy
rollback. The next approved run requires `PRODUCTION_URL` to be configured as
`https://swisstechfinance.com` and must prove all three public routes before the
post-deployment smoke roadmap item is complete.

The first public-gate attempt at commit `c2db0a4` proved the new container was
internally healthy, but Cloudflare returned HTTP 403 to all three requests sent
from the origin EC2 host. The identical 403 after restoring the prior image
proved this was origin-IP bot/security treatment, not an application regression.
The previous image was recreated and passed internal health. A diagnostic
`docker compose ps` then also failed because it omitted required
`RELEASE_IMAGE`; that reporting-only defect did not affect rollback.

Public requests now run from the GitHub-hosted runner, representing a genuinely
external client path. The runner checks the same health JSON, login status, and
static cache header. If those fail, a dedicated conditional SSH step restores
the captured rollback image and requires internal container/HTTP health. EC2
continues to own the release and rollback health checks, while Cloudflare is no
longer asked to proxy an origin-to-itself request. The diagnostic Compose call
now also receives the required image variable.

GitHub-hosted public checks at commit `1bb1f25` also received Cloudflare 403 on
all retries. At the user's direction, Cloudflare automation is deferred so the
site can remain accessible under its existing free security policy. The public
smoke and conditional public-only rollback steps have been removed from the
active workflow. Container image identity, Docker health, and nginx loopback
health remain mandatory and retain automatic rollback.

The core solo-developer CI/CD flow is complete: push to `main`, full isolated
tests, immutable ARM64 artifact, protected approval, EC2 staging, verified
backup, rollback anchor, idempotent SQL ledger, no-build deployment, internal
health checks, automatic rollback, and deployment recording. `TODO.md` retains
the deferred Cloudflare exception/monitoring work, repository dump remediation,
credential rotation, TLS hardening, observability, restore/rollback drills, and
remaining endpoint-test gaps for a future work session.
