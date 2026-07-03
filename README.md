# Accounting Plus Inventory Management System

A Django and PostgreSQL based accounting plus inventory management system. The repository contains the web application and a full PostgreSQL SQL backup named `db_backup_20260703_0000.sql`.

The application is built as a thin Django layer over database-side business logic. Django handles authentication, permissions, routing, templates, static assets, and AJAX endpoints. PostgreSQL stores the core accounting and inventory data and implements most business workflows through stored functions, views, and triggers.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Django |
| Database | PostgreSQL |
| Database driver | psycopg2-binary |
| Configuration | django-environ and `.env` |
| Frontend | Django templates, CSS, JavaScript |
| Static files | Django staticfiles with manifest storage |

`financee/settings.py` was generated for Django 5.2.6. Some migration comments mention Django 6.0, so pinning exact dependency versions is recommended before production deployment.

## Project Layout

| Path | Purpose |
| --- | --- |
| `financee/` | Main Django project settings, root URLs, WSGI/ASGI, custom admin site |
| `authentication/` | Login/logout/current-user views and custom permission migrations |
| `home/` | Main dashboard and dashboard JSON APIs |
| `parties/` | Customer, vendor, both-type, and expense party management |
| `items/` | Inventory item management and item autocomplete/list APIs |
| `purchase/` | Purchase invoice workflow and serial checks |
| `sale/` | Sale invoice workflow and serial lookup APIs |
| `purchaseReturn/` | Purchase return workflow |
| `saleReturn/` | Sale return workflow |
| `payments/` | Outgoing payment workflow |
| `receipts/` | Incoming receipt workflow |
| `contra/` | Party-to-party transfer workflow |
| `accountsReports/` | Accounts, stock, profit, and monthly reports |
| `templates/` | Django HTML templates |
| `static/` | CSS and JavaScript for the UI |
| `db_backup_20260703_0000.sql` | PostgreSQL schema, functions, triggers, views, and data snapshot |

## Frontend Features

### Smart Description Box

Seven document screens use a shared smart description enhancement:

- Sale
- Purchase
- Sale return
- Purchase return
- Payment
- Receipt
- Contra entry

The feature is frontend-only. Existing `textarea name="description"` fields remain the source of truth, and descriptions continue to save as plain text through the existing backend/database flow.

Files:

- `static/css/smart_description.css`
- `static/js/smart_description.js`

The shared script enhances description textareas with:

- soft light-blue modern UI
- `Smart note` badge and `current / max` character counter
- copy button
- raw edit toggle for table descriptions
- expand popup using SweetAlert
- automatic Excel, CSV, and Google Sheets table detection
- editable inline table preview with a capped height and internal scroll
- editable expanded table popup
- table copying as tab-separated text so it can be pasted back into spreadsheets

The seven templates load the shared assets directly. Existing per-page JavaScript still sets description values on create/update/navigation; the smart-description script observes those same textarea values and re-renders the preview.

## Application Modules

### Authentication and Permissions

The app uses Django session authentication. Most business views check custom permissions stored under the Django `auth.user` content type, for example:

- `auth.view_sale`, `auth.create_sale`, `auth.update_sale`, `auth.delete_sale`
- `auth.view_purchase`, `auth.create_purchase`, `auth.update_purchase`, `auth.delete_purchase`
- `auth.view_payment`, `auth.create_payment`, `auth.update_payment`, `auth.delete_payment`
- `auth.view_receipt`, `auth.create_receipt`, `auth.update_receipt`, `auth.delete_receipt`
- `auth.view_item`, `auth.create_item`, `auth.update_item`
- `auth.view_party`, `auth.create_party`, `auth.update_party`
- report permissions such as `auth.view_detailed_ledger`, `auth.view_stock_summary`, `auth.view_sale_wise_profit_report`
- dashboard section permissions such as `auth.view_dash_sales_profit`, `auth.view_dash_stock_overview`, `auth.view_dash_smart_alerts`
- contra permissions such as `auth.view_contra_entry`, `auth.create_contra_entry`, `auth.update_contra_entry`, `auth.delete_contra_entry`

The custom admin site is defined in `financee/admin_site.py`. It restricts admin access to superusers and adds user activity reporting across business tables.

### Core Business Flows

- Parties: add, update, autocomplete, list JSON.
- Items: add, update, autocomplete, list JSON.
- Purchases: create/update/delete purchase invoices, validate serials, fetch previous/next/current invoices, show summaries.
- Sales: create/update/delete sale invoices, validate stock serials, bulk serial lookup, fetch previous/next/current invoices, show summaries.
- Purchase returns: return purchased serials to vendors, fetch previous/next/current returns, show summaries.
- Sale returns: receive sold serials back from customers, fetch previous/next/current returns, show summaries.
- Payments: create/update/delete outgoing payments and date-wise lookup.
- Receipts: create/update/delete incoming receipts and date-wise lookup.
- Contra entries: party-to-party transfers without cash movement.
- Reports: ledgers, receivables, payables, trial balance, cash ledger, stock reports, serial ledgers, item history, company valuation, sale-wise profit, and monthly reports.

## Main URLs

Root URL behavior:

- `/` redirects authenticated users to `/home/` and unauthenticated users to `/authentication/login/`.
- `/admin/` uses the custom Financee admin site.

Important app route groups:

| Prefix | App |
| --- | --- |
| `/authentication/` | login, logout, current user |
| `/home/` | dashboard and dashboard APIs |
| `/parties/` | parties dashboard, add/update, autocomplete, list |
| `/items/` | items dashboard, add/update, autocomplete, list |
| `/purchase/` | purchase invoices |
| `/sale/` | sale invoices |
| `/purchaseReturn/` | purchase returns |
| `/saleReturn/` | sale returns |
| `/payments/` | payments |
| `/receipts/` | receipts |
| `/contra/` | contra entries |
| `/accountsReports/` | reporting endpoints |

## Database Backup Summary

The included backup file is:

```text
db_backup_20260703_0000.sql
```

It contains:

- 29 `CREATE TABLE` statements
- 13 `CREATE VIEW` statements
- 134 `CREATE FUNCTION` statements
- 11 `CREATE TRIGGER` statements
- Data loaded through `COPY public... FROM stdin`

Major business tables include:

- `chartofaccounts`
- `parties`
- `items`
- `journalentries`
- `journallines`
- `purchaseinvoices`, `purchaseitems`, `purchaseunits`
- `salesinvoices`, `salesitems`, `soldunits`
- `purchasereturns`, `purchasereturnitems`
- `salesreturns`, `salesreturnitems`
- `payments`
- `receipts`
- `contra_entries`
- `stockmovements`

Major database functions include:

- party and item CRUD: `add_party_from_json`, `update_party_from_json`, `get_party_by_name`, `add_item_from_json`, `update_item_from_json`, `get_item_by_name`
- purchase flow: `create_purchase`, `update_purchase_invoice`, `validate_purchase_update`, `validate_purchase_delete`, `delete_purchase`
- sale flow: `create_sale`, `update_sale_invoice`, `validate_sales_update`, `validate_sales_delete`, `delete_sale`
- return flow: `create_purchase_return`, `update_purchase_return`, `delete_purchase_return`, `create_sale_return`, `update_sale_return`, `delete_sale_return`
- payment/receipt/contra flow: `make_payment`, `update_payment`, `delete_payment`, `make_receipt`, `update_receipt`, `delete_receipt`, `make_contra`, `update_contra`, `delete_contra`
- reporting: `detailed_ledger`, `detailed_ledger2`, `get_cash_ledger_with_party`, `get_trial_balance_json`, `stock_summary`, `get_serial_ledger`, `sale_wise_profit`, `monthly_company_position`, `monthly_income_statement`
- dashboard: `fn_dash_sales_today_kpi`, `fn_dash_sales_last7days`, `fn_dash_stock_kpi`, `fn_dash_low_stock_items`, `fn_dash_fast_moving_items`, `fn_dash_receivables_aging`, `fn_dash_recent_transactions`, `fn_dash_smart_alerts`

## Backup Data Snapshot

The backup includes application data. Row counts observed in the `COPY` sections include:

| Table | Rows |
| --- | ---: |
| `items` | 265 |
| `parties` | 224 |
| `purchaseinvoices` | 194 |
| `purchaseitems` | 1,346 |
| `purchaseunits` | 9,084 |
| `salesinvoices` | 823 |
| `salesitems` | 1,424 |
| `soldunits` | 8,100 |
| `payments` | 1,452 |
| `receipts` | 1,670 |
| `contra_entries` | 93 |
| `journalentries` | 4,316 |
| `journallines` | 10,336 |
| `stockmovements` | 19,417 |

The backup also includes Django auth users, groups, permissions, sessions, migrations, and admin logs. Treat it as sensitive production-like data.

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file with the required values.

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
```

4. Restore the PostgreSQL backup into the configured database.

```powershell
psql -U your_database_user -d your_database_name -f db_backup_20260703_0000.sql
```

5. Run Django checks and start the development server.

```powershell
python manage.py check
python manage.py runserver
```

## Development Notes

- The Django model files are mostly empty placeholders. Do not assume Django ORM models represent the database.
- Most business logic is in PostgreSQL functions and triggers. When changing invoice, stock, ledger, payment, receipt, contra, or report behavior, inspect both the Django view and the matching SQL function.
- The JavaScript files in `static/js/` drive AJAX form submission, navigation, and report rendering.
- The smart description feature is intentionally frontend-only. Do not add database columns for it; it stores synchronized plain text in the existing `description` fields.
- If purchase previous/next navigation fails with `column pi.is_opening does not exist`, the live database has a function/schema mismatch. Ensure the column exists.

Windows:

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute('ALTER TABLE public.purchaseinvoices ADD COLUMN IF NOT EXISTS is_opening boolean NOT NULL DEFAULT false;'); print('is_opening column ensured')"
.\venv\Scripts\python.exe manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute(\"SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='purchaseinvoices' AND column_name='is_opening';\"); print(cursor.fetchall())"
```

Linux/EC2:

```bash
./myvenv/bin/python manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute('ALTER TABLE public.purchaseinvoices ADD COLUMN IF NOT EXISTS is_opening boolean NOT NULL DEFAULT false;'); print('is_opening column ensured')"
./myvenv/bin/python manage.py shell -c "from django.db import connection; cursor=connection.cursor(); cursor.execute(\"SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='purchaseinvoices' AND column_name='is_opening';\"); print(cursor.fetchall())"
```

- Existing source files contain some mojibake/encoding damage in comments and old documentation. Keep new documentation and code ASCII unless there is a clear reason to use Unicode.
- `.env` is ignored by git and should not be committed.

See `CONTEXT.md` for a deeper technical map of the repository and database backup.
