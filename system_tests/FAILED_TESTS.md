# Failed System Tests Backlog

Source run: July 17, 2026 at 21:52 PKT  
Full run result: `52 passed, 8 failed, 60 total`  
Detailed output: `system_tests/RESULTS.md`

These failures were reproduced in a disposable local PostgreSQL database restored
from `db_backup_20260703_0000.sql`. The temporary database was removed after the
run. No production database was used or modified.

## 1. Duplicate sale return is accepted

- Group: Basic Purchase, Sale and Return Lifecycle
- Test: Attempt duplicate return
- Setup: Purchase a serial, sell it, and return it successfully.
- Action: Return the same serial again without another sale.
- Expected: The second return is rejected because there is no active sold state.
- Actual: The second return succeeds.
- Risk: Duplicate return records and incorrect stock, customer balance, revenue,
  cost-of-goods-sold, and journal reversal data.
- Likely area: `create_sale_return` and active `soldunits.status = 'Sold'` lookup.

## 2. Sale update is permitted after a partial return

- Group: Partial Sale Return Tests
- Test: Update sale after return
- Setup: Sell four serials in one invoice and return two of them.
- Action: Validate an update to the original sale invoice.
- Expected: Updating the sale invoice is blocked while a sale return references it.
- Actual: `validate_sales_update` reports that the update is allowed.
- Risk: The original sale can diverge from its return lines, stock history, and
  accounting entries.
- Likely area: `validate_sales_update`; it currently focuses on removed returned
  serials rather than blocking mutation whenever the invoice has a return.

## 3. Old sale return can be deleted after resale

- Group: Sale Return Mutation After Resale
- Test: Delete old return after resale
- Setup: Sell a serial, return it, and sell the returned serial again.
- Action: Delete the earlier sale return.
- Expected: Deletion is rejected because reversing the old return would conflict
  with the newer active sale.
- Actual: Deletion succeeds.
- Risk: Two logical sold states, incorrect stock status, and journal corruption.
- Likely area: `delete_sale_return`; it needs a guard for a later active sold record.

## 4. Old sale return can be updated after resale

- Group: Sale Return Mutation After Resale
- Test: Update old return after resale
- Setup: Sell a serial, return it, and sell the returned serial again.
- Action: Update the earlier sale return.
- Expected: Update is rejected because the returned serial has subsequently been
  resold.
- Actual: Update succeeds.
- Risk: The update reversal can alter the current sale state and corrupt stock and
  accounting history.
- Likely area: `update_sale_return`; validate later sales before reversing old lines.

## 5. Duplicate mixed-item sale return is accepted

- Group: Multi-Item Sale and Return Tests
- Test: Duplicate mixed return
- Setup: Sell serials from two items and return one serial from each item.
- Action: Submit another return containing those same two serials.
- Expected: The duplicate return is rejected because neither serial has an active
  sold state.
- Actual: The duplicate mixed-item return succeeds.
- Risk: Duplicate return lines and incorrect stock/accounting across multiple items.
- Likely area: Same `create_sale_return` active-status defect as failure 1.

## 6. Multi-item sale update is permitted after a return

- Group: Multi-Item Sale and Return Tests
- Test: Update multi-item sale after return
- Setup: Sell six serials across two items and create a mixed partial return.
- Action: Validate an update to the original multi-item sale invoice.
- Expected: The sale update is blocked while return records reference the invoice.
- Actual: `validate_sales_update` reports that the update is allowed.
- Risk: Multi-item sale, return, stock, profit, and journal records can diverge.
- Likely area: Same `validate_sales_update` rule gap as failure 2.

## 7. Sale accepts quantity greater than supplied serial count

- Group: Additional Serious Scenarios
- Test: Sale qty greater than serial count
- Input: `qty = 5` with two serial numbers.
- Expected: Sale creation is rejected because quantity and serial count differ.
- Actual: Sale creation succeeds.
- Risk: Invoice totals, item quantity, sold-unit rows, stock movement, and profit
  calculations disagree.
- Likely area: `create_sale` must require each item quantity to equal the JSON serial
  array length before inserting the invoice or journal.

## 8. Sale accepts quantity less than supplied serial count

- Group: Additional Serious Scenarios
- Test: Sale qty less than serial count
- Input: `qty = 1` with two serial numbers.
- Expected: Sale creation is rejected because quantity and serial count differ.
- Actual: Sale creation succeeds.
- Risk: More units are removed from stock than the invoice quantity and financial
  totals represent.
- Likely area: Same `create_sale` quantity/serial-count validation gap as failure 7.

## Suggested Fix Order

1. Add strict active-sold-state validation to sale return creation.
2. Protect sale return update/delete after a subsequent resale.
3. Block sale invoice mutation whenever any sale return references it.
4. Enforce `qty = serial count` inside `create_sale` for every item.
5. Rerun the full disposable suite and update this backlog only after all related
   regression tests pass.

