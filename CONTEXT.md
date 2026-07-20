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
