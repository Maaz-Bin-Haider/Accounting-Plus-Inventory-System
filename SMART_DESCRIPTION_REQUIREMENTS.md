# Smart Description Box Suggestions

## Original Requirement

The current description box has almost all of the expected modern features except:

- Copy note button when viewing an old invoice.
- Expand/collapse button.

Suggested advanced feature:

- If the user pastes copied text from Excel, CSV, or Google Sheets, the description box should automatically detect the pasted values as tabular data.
- The pasted tabular data should be displayed in a proper table form.
- The table should have proper bold headers.
- When viewing an old invoice, the user should be able to copy the exact text in table form.
- The user should still be able to add normal text like before.
- The description box UI should be high level, minimal, professional, and modern.
- The description box should have animations.
- The description box should use a different theme very light soft bluish theme.

## Implemented Suggestions

- Add a shared smart description enhancement for all seven document flows:
  - Sale
  - Sale return
  - Purchase
  - Purchase return
  - Payment
  - Receipt
  - Contra entry

- Keep the backend/database behavior unchanged:
  - Descriptions are still saved as plain text.
  - Existing textarea `id` and `name="description"` behavior remains intact.
  - Existing create, update, previous, next, and old-entry loading logic continues to work.

- Add a modern smart description shell:
  - Soft light-blue theme.
  - Minimal toolbar.
  - Character counter.
  - Copy button.
  - Edit raw button for table descriptions.
  - Expand button.
  - Smooth focus, shine, copy ripple, and modal rise animations.

- Support normal text entry:
  - Users can type ordinary notes exactly like before.
  - Normal text remains visible as a textarea.
  - Copy button copies the normal description text.

- Support pasted Excel / CSV / Google Sheets data:
  - Detect tab-separated spreadsheet rows.
  - Detect comma-separated CSV rows.
  - Convert detected tabular text into a clean table preview.
  - Use the first row as bold table headers.
  - Hide the raw textarea automatically when table data is detected.
  - Keep an `Edit raw` button so the user can reveal and edit the original raw text if needed.

- Support editable table mode:
  - Table headers are editable.
  - Table cells are editable.
  - Cell edits sync back into the hidden textarea in real time.
  - Saving the invoice still submits the synchronized plain text value.

- Support copying old invoice table descriptions:
  - When an old invoice loads with tabular description text, it is rendered as a table.
  - Copy button copies the table as tab-separated text.
  - The copied value can be pasted back into Excel or Google Sheets with columns preserved.

- Support large popup editing:
  - Expand opens a SweetAlert popup.
  - Normal text opens as a large editable textarea.
  - Table descriptions open as a large editable table.
  - The popup has `Apply` and `Close` actions.
  - `Apply` writes changes back into the original description field.
  - `Close` exits without applying changes.

## Files should be Added

- `static/css/smart_description.css`
- `static/js/smart_description.js`

## Files Updated

- `templates/sale_templates/sale_template.html`
- `templates/purchase_templates/purchasing_template.html`
- `templates/sale_return_templates/sale_return_template.html`
- `templates/purchase_return_templates/purchase_return_template.html`
- `templates/payments_templates/payment.html`
- `templates/receipts_templates/receipt.html`
- `templates/contra_templates/contra.html`

The seven page-specific JavaScript files did not need direct edits. They already load old-entry descriptions into the existing textareas. The shared `smart_description.js` observes those textarea value changes and re-renders the note/table UI automatically.

## Implementation Notes

- This is a UI-only feature.
- No database schema changes are required for smart descriptions.
- No backend view changes are required for smart descriptions.
- Descriptions are still submitted and stored as plain text.
- Tabular descriptions are stored as tab-separated text in the existing `description` fields.
- Inline table preview height is capped and scrolls internally.
- Expanded table editing remains available through the SweetAlert popup.

## Validation Suggestions

- Paste normal text and confirm it behaves like the old description box.
- Paste copied rows from Excel and confirm a table appears.
- Paste copied rows from Google Sheets and confirm a table appears.
- Paste CSV text and confirm a table appears.
- Edit table cells and save the invoice.
- Reopen the invoice and confirm the edited table is restored.
- Copy the table from an old invoice and paste it into Excel or Google Sheets.
- Use `Edit raw` and confirm the original text is visible.
- Use `Expand`, edit in the popup, click `Apply`, and confirm the inline field updates.
- Use `Expand`, edit in the popup, click `Close`, and confirm no changes are applied.
