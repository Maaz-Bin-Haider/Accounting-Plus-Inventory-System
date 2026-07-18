# Failed System Tests Backlog

Status: **CLOSED - all 8 defects fixed on July 18, 2026.**

Latest run: July 18, 2026 - `60 passed, 0 failed, 60 total`
(disposable database restored from `db_backup_20260718_0000.sql` with
`production_fixes.sql` applied on top).

- Root causes, fixes, and deployment steps: see `FIXES.md` in the project root.
- Detailed run output: `system_tests/RESULTS.md`.
- The runner now applies `production_fixes.sql` automatically after restoring
  the backup, so every future run validates the patched functions.

## Resolved defects (July 17 backlog)

| # | Defect | Fixed in |
| --- | --- | --- |
| 1 | Duplicate sale return accepted | `create_sale_return` (3-arg) - restored `status = 'Sold'` filter |
| 2 | Sale update permitted after partial return | `validate_sales_update` - blocks while any invoice serial is 'Returned' |
| 3 | Old sale return deletable after resale | `delete_sale_return` - resale/stock guards |
| 4 | Old sale return updatable after resale | `update_sale_return` - resale/stock guards |
| 5 | Duplicate mixed-item sale return accepted | same as defect 1 |
| 6 | Multi-item sale update permitted after return | same as defect 2 |
| 7 | Sale accepted qty greater than serial count | `create_sale` - qty must equal serial count |
| 8 | Sale accepted qty less than serial count | same as defect 7 |

If a future run fails, reopen this file with the new backlog and rerun the
full suite after each fix, because sale returns and invoice mutations also
affect stock, journals, reports, and profit calculations.
