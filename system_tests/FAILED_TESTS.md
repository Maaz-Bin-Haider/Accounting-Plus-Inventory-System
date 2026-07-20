# Failed System Tests Backlog

Status: **CLOSED - all 9 confirmed defects have passing regressions.**

Latest run: July 20, 2026 - `99 passed, 0 failed, 99 total`
(disposable database restored from `db_backup_20260718_0000.sql` with
`production_fixes.sql` applied on top).

- Root causes, fixes, and deployment steps: see `FIXES.md` in the project root.
- Detailed run output: `system_tests/RESULTS.md`.
- The runner now applies `production_fixes.sql` automatically after restoring
  the backup, so every future run validates the patched functions.

## Resolved defects (July 17 backlog)

| # | Defect | Regression case |
| --- | --- | --- |
| 1 | Duplicate sale return accepted | `Attempt duplicate return` |
| 2 | Sale update permitted after partial return | `Update sale after return` |
| 3 | Old sale return deletable after resale | `Delete old return after resale` |
| 4 | Old sale return updatable after resale | `Update old return after resale` |
| 5 | Duplicate mixed-item sale return accepted | `Duplicate mixed return` |
| 6 | Multi-item sale update permitted after return | `Update multi-item sale after return` |
| 7 | Sale accepted qty greater than serial count | `Sale qty greater than serial count` |
| 8 | Sale accepted qty less than serial count | `Sale qty less than serial count` |
| 9 | Two concurrent sales committed for one serial | `Race two sales for one serial` |

`REGRESSION_CASES` in the runner is executable: the suite fails if any mapped
case is absent or does not pass.

If a future run fails, reopen this file with the new backlog and rerun the
full suite after each fix, because sale returns and invoice mutations also
affect stock, journals, reports, and profit calculations.
