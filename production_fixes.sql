-- ============================================================================
-- PRODUCTION FIXES - One-time SQL patch
-- Accounting Plus Inventory System
-- Date: 2026-07-18
--
-- Fixes the 8 confirmed defects from system_tests/FAILED_TESTS.md and hardens
-- related stored procedures against invalid entries, with clear user-facing
-- error messages.
--
-- HOW TO RUN ON EC2 (from the project root, after git pull):
--   sudo -u postgres psql -d <DB_NAME> -f production_fixes.sql
-- or with the application role:
--   psql -h localhost -U <DB_USER> -d <DB_NAME> -f production_fixes.sql
--
-- The whole patch runs in a single transaction: it either fully applies or
-- fully rolls back. Read-only data diagnostics are printed at the end.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ============================================================================
-- FIX 1 + FIX 5 (Failed tests 1 and 5): create_sale_return accepted duplicate
-- returns because the 3-argument overload (the one the application calls) was
-- missing the "su.status = 'Sold'" filter. It matched already-returned rows.
--
-- Also adds: empty-payload check, duplicate-serials-in-payload check, and
-- clear error messages that tell the user exactly what is wrong.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_sale_return(p_party_name text, p_serials jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_return_id   BIGINT;
    v_customer_id BIGINT;
    v_serial      TEXT;
    v_unit        RECORD;
    v_total       NUMERIC(14,2) := 0;
    v_dup         TEXT;
    v_exists      BOOLEAN;
BEGIN
    -- Basic payload validation -----------------------------------------------
    IF p_serials IS NULL OR jsonb_typeof(p_serials) <> 'array' OR jsonb_array_length(p_serials) = 0 THEN
        RAISE EXCEPTION 'At least one serial number is required to create a sale return.';
    END IF;

    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(p_serials) AS s) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this return. Each serial can only be returned once.', v_dup;
    END IF;

    SELECT party_id INTO v_customer_id FROM Parties WHERE party_name = p_party_name LIMIT 1;
    IF v_customer_id IS NULL THEN
        RAISE EXCEPTION 'Customer "%" does not exist. Please check the party name.', p_party_name;
    END IF;

    INSERT INTO SalesReturns(customer_id, return_date, total_amount, created_by)
    VALUES (v_customer_id, CURRENT_DATE, 0, p_created_by)
    RETURNING sales_return_id INTO v_return_id;

    FOR v_serial IN SELECT jsonb_array_elements_text(p_serials)
    LOOP
        IF v_serial IS NULL OR btrim(v_serial) = '' THEN
            RAISE EXCEPTION 'A blank serial number was submitted. Please remove empty serial entries.';
        END IF;

        -- Only the ACTIVE sold record qualifies for a return.
        SELECT su.sold_unit_id, su.unit_id, su.sold_price, si.item_id,
               si.sales_invoice_id, pu.serial_number, pi2.unit_price, s.customer_id
        INTO v_unit
        FROM SoldUnits su
        JOIN SalesItems si ON su.sales_item_id = si.sales_item_id
        JOIN SalesInvoices s ON si.sales_invoice_id = s.sales_invoice_id
        JOIN PurchaseUnits pu ON su.unit_id = pu.unit_id
        JOIN PurchaseItems pi2 ON pu.purchase_item_id = pi2.purchase_item_id
        WHERE pu.serial_number = v_serial
          AND su.status = 'Sold'
        ORDER BY su.sold_unit_id DESC
        LIMIT 1;

        IF NOT FOUND THEN
            SELECT EXISTS (SELECT 1 FROM PurchaseUnits pu WHERE pu.serial_number = v_serial)
            INTO v_exists;
            IF NOT v_exists THEN
                RAISE EXCEPTION 'Serial "%" does not exist in the system. Please check the serial number.', v_serial;
            ELSE
                RAISE EXCEPTION 'Serial "%" is not currently sold, so it cannot be returned. It may already have been returned or is still in stock.', v_serial;
            END IF;
        END IF;

        IF v_unit.customer_id <> v_customer_id THEN
            RAISE EXCEPTION 'Serial "%" was not sold to customer "%". Please select the customer who actually bought it.', v_serial, p_party_name;
        END IF;

        UPDATE SoldUnits SET status = 'Returned' WHERE sold_unit_id = v_unit.sold_unit_id;
        UPDATE PurchaseUnits SET in_stock = TRUE WHERE unit_id = v_unit.unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (v_unit.item_id, v_serial, 'IN', 'SalesReturn', v_return_id, 1);

        INSERT INTO SalesReturnItems(sales_return_id, item_id, sold_price, cost_price, serial_number)
        VALUES (v_return_id, v_unit.item_id, v_unit.sold_price, v_unit.unit_price, v_serial);

        v_total := v_total + v_unit.sold_price;
    END LOOP;

    UPDATE SalesReturns SET total_amount = v_total WHERE sales_return_id = v_return_id;
    PERFORM rebuild_sales_return_journal(v_return_id);
    RETURN v_return_id;
END;
$$;

-- Legacy 2-argument overload now delegates to the fixed version so both
-- signatures behave identically.
CREATE OR REPLACE FUNCTION public.create_sale_return(p_party_name text, p_serials jsonb) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN public.create_sale_return(p_party_name, p_serials, NULL::integer);
END;
$$;


-- ============================================================================
-- FIX 7 + FIX 8 (Failed tests 7 and 8): create_sale accepted a quantity that
-- did not match the number of serial numbers supplied, corrupting invoice
-- totals, stock counts and profit reports.
--
-- Also adds: customer existence check, item existence with a clear message,
-- qty/price format validation, duplicate-serial detection, blank-serial
-- detection, and a check that each serial actually belongs to the item row
-- it is being sold under.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_sale(p_party_id bigint, p_invoice_date date, p_items jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_invoice_id     BIGINT;
    v_sales_item_id  BIGINT;
    v_total          NUMERIC(14,2) := 0;
    v_unit_id        BIGINT;
    v_serial         TEXT;
    v_item_id        BIGINT;
    v_serial_item_id BIGINT;
    v_item           JSONB;
    v_item_name      TEXT;
    v_qty_text       TEXT;
    v_price_text     TEXT;
    v_qty            INT;
    v_serial_count   INT;
    v_dup            TEXT;
BEGIN
    -- Header validation -------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM Parties WHERE party_id = p_party_id) THEN
        RAISE EXCEPTION 'The selected customer does not exist. Please choose a valid customer.';
    END IF;
    IF p_invoice_date IS NULL THEN
        RAISE EXCEPTION 'Sale date is required.';
    END IF;
    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'At least one item is required to create a sale.';
    END IF;

    -- Duplicate serials anywhere in the payload ------------------------------
    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(it->'serials') AS s
          FROM jsonb_array_elements(p_items) it) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this sale. Each serial number can only be sold once.', v_dup;
    END IF;

    -- Per-item validation (before anything is written) -----------------------
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        v_item_name  := NULLIF(btrim(COALESCE(v_item->>'item_name','')), '');
        v_qty_text   := v_item->>'qty';
        v_price_text := v_item->>'unit_price';

        IF v_item_name IS NULL THEN
            RAISE EXCEPTION 'Item name is missing for one of the sale rows.';
        END IF;
        IF v_qty_text IS NULL OR v_qty_text !~ '^[0-9]+$' OR v_qty_text::INT <= 0 THEN
            RAISE EXCEPTION 'Quantity for item "%" must be a whole number greater than zero.', v_item_name;
        END IF;
        IF v_price_text IS NULL OR v_price_text !~ '^[0-9]+(\.[0-9]+)?$' THEN
            RAISE EXCEPTION 'Sale price for item "%" must be a valid non-negative number.', v_item_name;
        END IF;
        IF v_item->'serials' IS NULL OR jsonb_typeof(v_item->'serials') <> 'array' THEN
            RAISE EXCEPTION 'Serial numbers are missing for item "%".', v_item_name;
        END IF;

        v_qty          := v_qty_text::INT;
        v_serial_count := jsonb_array_length(v_item->'serials');

        IF v_qty <> v_serial_count THEN
            RAISE EXCEPTION 'Quantity (%) does not match the number of serial numbers (%) for item "%". Please provide exactly one serial number per unit.', v_qty, v_serial_count, v_item_name;
        END IF;
    END LOOP;

    -- Create the invoice ------------------------------------------------------
    INSERT INTO SalesInvoices(customer_id, invoice_date, total_amount, created_by)
    VALUES (p_party_id, p_invoice_date, 0, p_created_by)
    RETURNING sales_invoice_id INTO v_invoice_id;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        SELECT item_id INTO v_item_id FROM Items
        WHERE item_name = (v_item->>'item_name') LIMIT 1;
        IF v_item_id IS NULL THEN
            RAISE EXCEPTION 'Item "%" does not exist. Please create the item first.', (v_item->>'item_name');
        END IF;

        INSERT INTO SalesItems(sales_invoice_id, item_id, quantity, unit_price)
        VALUES (v_invoice_id, v_item_id, (v_item->>'qty')::INT, (v_item->>'unit_price')::NUMERIC)
        RETURNING sales_item_id INTO v_sales_item_id;

        v_total := v_total + ((v_item->>'qty')::INT * (v_item->>'unit_price')::NUMERIC);

        FOR v_serial IN SELECT jsonb_array_elements_text(v_item->'serials')
        LOOP
            IF v_serial IS NULL OR btrim(v_serial) = '' THEN
                RAISE EXCEPTION 'A blank serial number was submitted for item "%". Please remove empty serial entries.', (v_item->>'item_name');
            END IF;

            SELECT pu.unit_id, pi.item_id INTO v_unit_id, v_serial_item_id
            FROM PurchaseUnits pu
            JOIN PurchaseItems pi ON pi.purchase_item_id = pu.purchase_item_id
            WHERE pu.serial_number = v_serial AND pu.in_stock = TRUE
            LIMIT 1;

            IF v_unit_id IS NULL THEN
                RAISE EXCEPTION 'Serial "%" is not available in stock. It may not exist, may already be sold, or may have been returned to the vendor.', v_serial;
            END IF;

            IF v_serial_item_id <> v_item_id THEN
                RAISE EXCEPTION 'Serial "%" does not belong to item "%". Please check the serial number.', v_serial, (v_item->>'item_name');
            END IF;

            INSERT INTO SoldUnits(sales_item_id, unit_id, sold_price, status)
            VALUES (v_sales_item_id, v_unit_id, (v_item->>'unit_price')::NUMERIC, 'Sold');
            UPDATE PurchaseUnits SET in_stock = FALSE WHERE unit_id = v_unit_id;
            INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
            VALUES (v_item_id, v_serial, 'OUT', 'SalesInvoice', v_invoice_id, 1);
        END LOOP;
    END LOOP;

    UPDATE SalesInvoices SET total_amount = v_total WHERE sales_invoice_id = v_invoice_id;
    PERFORM rebuild_sales_journal(v_invoice_id);
    RETURN v_invoice_id;
END;
$$;

-- Legacy 3-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.create_sale(p_party_id bigint, p_invoice_date date, p_items jsonb) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN public.create_sale(p_party_id, p_invoice_date, p_items, NULL::integer);
END;
$$;


-- ============================================================================
-- FIX 2 + FIX 6 (Failed tests 2 and 6): validate_sales_update only blocked an
-- update when a REMOVED serial was in a sale return. An update that kept the
-- same serial list was always allowed even though a sale return referenced
-- the invoice, letting the invoice diverge from its return records.
--
-- New rule: while any serial of the invoice is in 'Returned' state, the
-- invoice cannot be updated at all. The historical removed-serial check is
-- kept as a second safety net for older data.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.validate_sales_update(p_invoice_id bigint, p_items jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_existing_serials TEXT[];
    v_new_serials TEXT[];
    v_removed_serials TEXT[];
    v_returned_serials TEXT[];
    v_message TEXT;
BEGIN
    -- 1. Block the update entirely while a sale return references this invoice.
    SELECT ARRAY_AGG(pu.serial_number)
    INTO v_returned_serials
    FROM SoldUnits su
    JOIN SalesItems si ON su.sales_item_id = si.sales_item_id
    JOIN PurchaseUnits pu ON su.unit_id = pu.unit_id
    WHERE si.sales_invoice_id = p_invoice_id
      AND su.status = 'Returned';

    IF v_returned_serials IS NOT NULL THEN
        v_message := 'This sale invoice cannot be updated because ' ||
                     array_length(v_returned_serials, 1) ||
                     ' serial(s) from it have been returned by the customer. ' ||
                     'Update or delete the related sale return first.';
        RETURN jsonb_build_object(
            'is_valid', FALSE,
            'message', v_message,
            'returned_serials', v_returned_serials
        );
    END IF;

    -- 2. Historical safety net: block removal of serials that appear in any
    --    sale return record.
    SELECT ARRAY_AGG(pu.serial_number)
    INTO v_existing_serials
    FROM SoldUnits su
    JOIN PurchaseUnits pu ON su.unit_id = pu.unit_id
    JOIN SalesItems si ON su.sales_item_id = si.sales_item_id
    WHERE si.sales_invoice_id = p_invoice_id;

    IF v_existing_serials IS NULL THEN
        v_existing_serials := ARRAY[]::TEXT[];
    END IF;

    SELECT ARRAY_AGG(serial::TEXT)
    INTO v_new_serials
    FROM jsonb_array_elements(p_items) AS item,
         jsonb_array_elements_text(item->'serials') AS serial;

    IF v_new_serials IS NULL THEN
        v_new_serials := ARRAY[]::TEXT[];
    END IF;

    SELECT ARRAY_AGG(s)
    INTO v_removed_serials
    FROM unnest(v_existing_serials) AS s
    WHERE s <> ALL(v_new_serials);

    IF v_removed_serials IS NULL THEN
        v_removed_serials := ARRAY[]::TEXT[];
    END IF;

    SELECT ARRAY_AGG(sri.serial_number)
    INTO v_returned_serials
    FROM SalesReturnItems sri
    WHERE sri.serial_number = ANY(v_removed_serials);

    IF v_returned_serials IS NULL THEN
        v_returned_serials := ARRAY[]::TEXT[];
    END IF;

    IF array_length(v_returned_serials, 1) IS NOT NULL THEN
        v_message := 'This update would remove ' ||
                     array_length(v_returned_serials, 1) ||
                     ' serial(s) that already appear in a sale return. ' ||
                     'Update or delete the related sale return first.';
        RETURN jsonb_build_object(
            'is_valid', FALSE,
            'message', v_message,
            'returned_serials', v_returned_serials
        );
    END IF;

    RETURN jsonb_build_object(
        'is_valid', TRUE,
        'message', 'Safe to update - no sale return references this invoice.',
        'returned_serials', v_returned_serials
    );
END;
$$;


-- ============================================================================
-- HARDENING for FIX 2 + FIX 6: update_sale_invoice previously performed no
-- validation at all: it did not call validate_sales_update, did not check
-- quantity against serial count, and re-attached serials without checking
-- stock, so it could silently steal a serial that was sold on another
-- invoice. All of that is now enforced inside the function itself.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_sale_invoice(p_invoice_id bigint, p_items jsonb, p_party_name text DEFAULT NULL::text, p_invoice_date date DEFAULT NULL::date, p_created_by integer DEFAULT NULL::integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_item           JSONB;
    v_item_id        BIGINT;
    v_total          NUMERIC(14,2) := 0;
    v_sales_item_id  BIGINT;
    v_serial         TEXT;
    v_unit_id        BIGINT;
    v_serial_item_id BIGINT;
    v_new_party_id   BIGINT;
    v_validation     JSONB;
    v_item_name      TEXT;
    v_qty_text       TEXT;
    v_price_text     TEXT;
    v_qty            INT;
    v_serial_count   INT;
    v_dup            TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM SalesInvoices WHERE sales_invoice_id = p_invoice_id) THEN
        RAISE EXCEPTION 'Sale invoice % was not found.', p_invoice_id;
    END IF;

    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'At least one item is required on the sale invoice.';
    END IF;

    -- Enforce the update rules (blocked while a sale return references it).
    v_validation := validate_sales_update(p_invoice_id, p_items);
    IF (v_validation->>'is_valid')::BOOLEAN = FALSE THEN
        RAISE EXCEPTION '%', v_validation->>'message';
    END IF;

    -- Duplicate serials anywhere in the payload.
    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(it->'serials') AS s
          FROM jsonb_array_elements(p_items) it) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this sale. Each serial number can only be sold once.', v_dup;
    END IF;

    -- Per-item payload validation and serial availability checks, performed
    -- BEFORE any row is deleted or modified.
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        v_item_name  := NULLIF(btrim(COALESCE(v_item->>'item_name','')), '');
        v_qty_text   := v_item->>'qty';
        v_price_text := v_item->>'unit_price';

        IF v_item_name IS NULL THEN
            RAISE EXCEPTION 'Item name is missing for one of the sale rows.';
        END IF;
        IF v_qty_text IS NULL OR v_qty_text !~ '^[0-9]+$' OR v_qty_text::INT <= 0 THEN
            RAISE EXCEPTION 'Quantity for item "%" must be a whole number greater than zero.', v_item_name;
        END IF;
        IF v_price_text IS NULL OR v_price_text !~ '^[0-9]+(\.[0-9]+)?$' THEN
            RAISE EXCEPTION 'Sale price for item "%" must be a valid non-negative number.', v_item_name;
        END IF;
        IF v_item->'serials' IS NULL OR jsonb_typeof(v_item->'serials') <> 'array' THEN
            RAISE EXCEPTION 'Serial numbers are missing for item "%".', v_item_name;
        END IF;

        v_qty          := v_qty_text::INT;
        v_serial_count := jsonb_array_length(v_item->'serials');
        IF v_qty <> v_serial_count THEN
            RAISE EXCEPTION 'Quantity (%) does not match the number of serial numbers (%) for item "%". Please provide exactly one serial number per unit.', v_qty, v_serial_count, v_item_name;
        END IF;

        SELECT item_id INTO v_item_id
        FROM Items WHERE item_name = (v_item->>'item_name') LIMIT 1;
        IF v_item_id IS NULL THEN
            RAISE EXCEPTION 'Item "%" does not exist. Please create the item first.', v_item_name;
        END IF;

        FOR v_serial IN SELECT jsonb_array_elements_text(v_item->'serials')
        LOOP
            IF v_serial IS NULL OR btrim(v_serial) = '' THEN
                RAISE EXCEPTION 'A blank serial number was submitted for item "%". Please remove empty serial entries.', v_item_name;
            END IF;

            SELECT pu.unit_id, pi.item_id INTO v_unit_id, v_serial_item_id
            FROM PurchaseUnits pu
            JOIN PurchaseItems pi ON pi.purchase_item_id = pu.purchase_item_id
            WHERE pu.serial_number = v_serial
            LIMIT 1;

            IF v_unit_id IS NULL THEN
                RAISE EXCEPTION 'Serial "%" does not exist in the system. Please check the serial number.', v_serial;
            END IF;

            IF v_serial_item_id <> v_item_id THEN
                RAISE EXCEPTION 'Serial "%" does not belong to item "%". Please check the serial number.', v_serial, v_item_name;
            END IF;

            -- The serial must be in stock, or already sold on THIS invoice.
            IF NOT EXISTS (
                SELECT 1 FROM PurchaseUnits pu
                WHERE pu.unit_id = v_unit_id
                  AND (pu.in_stock = TRUE
                       OR EXISTS (SELECT 1
                                  FROM SoldUnits su
                                  JOIN SalesItems si ON si.sales_item_id = su.sales_item_id
                                  WHERE su.unit_id = pu.unit_id
                                    AND su.status = 'Sold'
                                    AND si.sales_invoice_id = p_invoice_id))
            ) THEN
                RAISE EXCEPTION 'Serial "%" is not available. It is already sold on another invoice or has been returned to the vendor.', v_serial;
            END IF;
        END LOOP;
    END LOOP;

    -- 1. Update Party (Customer) if given
    IF p_party_name IS NOT NULL THEN
        SELECT party_id INTO v_new_party_id
        FROM Parties WHERE party_name = p_party_name LIMIT 1;

        IF v_new_party_id IS NULL THEN
            RAISE EXCEPTION 'Customer "%" does not exist. Please check the party name.', p_party_name;
        END IF;

        UPDATE SalesInvoices
        SET customer_id = v_new_party_id
        WHERE sales_invoice_id = p_invoice_id;
    END IF;

    -- 2. Update Invoice Date (if provided)
    IF p_invoice_date IS NOT NULL THEN
        UPDATE SalesInvoices
        SET invoice_date = p_invoice_date
        WHERE sales_invoice_id = p_invoice_id;
    END IF;

    -- 3. Update last modifier (always, if provided)
    IF p_created_by IS NOT NULL THEN
        UPDATE SalesInvoices
        SET created_by = p_created_by
        WHERE sales_invoice_id = p_invoice_id;
    END IF;

    -- 4. Delete old items + sold units + stock movements
    DELETE FROM StockMovements
    WHERE reference_type = 'SalesInvoice' AND reference_id = p_invoice_id;

    DELETE FROM SoldUnits
    WHERE sales_item_id IN (
        SELECT sales_item_id FROM SalesItems WHERE sales_invoice_id = p_invoice_id
    );

    -- Note: the statement-level trigger trg_soldunits_fix_ghost_stock
    -- restores in_stock = TRUE for units left without any soldunits record,
    -- and the loop below takes the new serial list out of stock again.

    DELETE FROM SalesItems WHERE sales_invoice_id = p_invoice_id;

    -- 5. Insert new/updated items and serials
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        SELECT item_id INTO v_item_id
        FROM Items WHERE item_name = (v_item->>'item_name') LIMIT 1;

        INSERT INTO SalesItems(sales_invoice_id, item_id, quantity, unit_price)
        VALUES (p_invoice_id, v_item_id,
                (v_item->>'qty')::INT, (v_item->>'unit_price')::NUMERIC)
        RETURNING sales_item_id INTO v_sales_item_id;

        v_total := v_total + ((v_item->>'qty')::INT * (v_item->>'unit_price')::NUMERIC);

        FOR v_serial IN SELECT jsonb_array_elements_text(v_item->'serials')
        LOOP
            SELECT unit_id INTO v_unit_id
            FROM PurchaseUnits WHERE serial_number = v_serial LIMIT 1;

            UPDATE PurchaseUnits SET in_stock = FALSE WHERE unit_id = v_unit_id;

            INSERT INTO SoldUnits(sales_item_id, unit_id, sold_price, status)
            VALUES (v_sales_item_id, v_unit_id, (v_item->>'unit_price')::NUMERIC, 'Sold');

            INSERT INTO StockMovements(item_id, serial_number, movement_type,
                                       reference_type, reference_id, quantity)
            VALUES (v_item_id, v_serial, 'OUT', 'SalesInvoice', p_invoice_id, 1);
        END LOOP;
    END LOOP;

    -- 6. Update total amount
    UPDATE SalesInvoices SET total_amount = v_total
    WHERE sales_invoice_id = p_invoice_id;

    -- 7. Rebuild journal
    PERFORM rebuild_sales_journal(p_invoice_id);
END;
$$;

-- Legacy 4-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.update_sale_invoice(p_invoice_id bigint, p_items jsonb, p_party_name text DEFAULT NULL::text, p_invoice_date date DEFAULT NULL::date) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM public.update_sale_invoice(p_invoice_id, p_items, p_party_name, p_invoice_date, NULL::integer);
END;
$$;


-- ============================================================================
-- FIX 3 (Failed test 3): delete_sale_return reversed a return with no checks.
-- If the serial had been sold again after the return, deleting the old return
-- flipped EVERY sold record of the unit back to 'Sold', producing two active
-- sold states, wrong stock, and corrupted journals.
--
-- New rules per returned serial:
--   - blocked if the serial has an active sale (it was sold again);
--   - blocked if the serial is no longer in stock (e.g. returned to vendor);
--   - only the exact 'Returned' record of this return is reverted.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.delete_sale_return(p_return_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    rec          RECORD;
    v_journal_id BIGINT;
    v_unit_id    BIGINT;
    v_in_stock   BOOLEAN;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM SalesReturns WHERE sales_return_id = p_return_id) THEN
        RAISE EXCEPTION 'Sale return % was not found.', p_return_id;
    END IF;

    -- 1. Revert each returned unit (with guards)
    FOR rec IN
        SELECT sri.serial_number, sri.item_id
        FROM SalesReturnItems sri
        WHERE sri.sales_return_id = p_return_id
    LOOP
        SELECT pu.unit_id, pu.in_stock INTO v_unit_id, v_in_stock
        FROM PurchaseUnits pu
        WHERE pu.serial_number = rec.serial_number
        LIMIT 1;

        IF v_unit_id IS NULL THEN
            RAISE EXCEPTION 'Serial "%" from this return no longer exists in stock records, so the return cannot be deleted.', rec.serial_number;
        END IF;

        IF EXISTS (SELECT 1 FROM SoldUnits su WHERE su.unit_id = v_unit_id AND su.status = 'Sold') THEN
            RAISE EXCEPTION 'This sale return cannot be deleted because serial "%" was sold again after the return. Delete or update the newer sale first.', rec.serial_number;
        END IF;

        IF v_in_stock = FALSE THEN
            RAISE EXCEPTION 'This sale return cannot be deleted because serial "%" is no longer in stock (it may have been returned to the vendor).', rec.serial_number;
        END IF;

        -- Revert only the most recent 'Returned' record of this unit.
        UPDATE SoldUnits
        SET status = 'Sold'
        WHERE sold_unit_id = (
            SELECT su.sold_unit_id
            FROM SoldUnits su
            WHERE su.unit_id = v_unit_id AND su.status = 'Returned'
            ORDER BY su.sold_unit_id DESC
            LIMIT 1
        );

        UPDATE PurchaseUnits
        SET in_stock = FALSE
        WHERE unit_id = v_unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (rec.item_id, rec.serial_number, 'OUT', 'SalesReturn-Delete', p_return_id, 1);
    END LOOP;

    -- 2. Remove journal (if exists)
    SELECT journal_id INTO v_journal_id
    FROM SalesReturns
    WHERE sales_return_id = p_return_id;

    IF v_journal_id IS NOT NULL THEN
        DELETE FROM JournalLines WHERE journal_id = v_journal_id;
        DELETE FROM JournalEntries WHERE journal_id = v_journal_id;
    END IF;

    -- 3. Delete return items
    DELETE FROM SalesReturnItems WHERE sales_return_id = p_return_id;

    -- 4. Delete return header
    DELETE FROM SalesReturns WHERE sales_return_id = p_return_id;
END;
$$;


-- ============================================================================
-- FIX 4 (Failed test 4): update_sale_return had the same missing guard as
-- delete_sale_return when reversing its old lines. Updating an old return
-- after the serial had been resold corrupted the current sale state.
--
-- The reversal loop now has the same guards, and reverts only the exact
-- 'Returned' record. The re-insert loop keeps the active-'Sold' filter and
-- gains clearer error messages plus payload validation.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_sale_return(p_return_id bigint, p_serials jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    rec           RECORD;
    v_serial      TEXT;
    v_unit        RECORD;
    v_total       NUMERIC(14,2) := 0;
    v_customer_id BIGINT;
    v_unit_id     BIGINT;
    v_in_stock    BOOLEAN;
    v_dup         TEXT;
    v_exists      BOOLEAN;
BEGIN
    SELECT customer_id INTO v_customer_id
    FROM SalesReturns WHERE sales_return_id = p_return_id;

    IF v_customer_id IS NULL THEN
        RAISE EXCEPTION 'Sale return % was not found.', p_return_id;
    END IF;

    IF p_serials IS NULL OR jsonb_typeof(p_serials) <> 'array' OR jsonb_array_length(p_serials) = 0 THEN
        RAISE EXCEPTION 'At least one serial number is required. To remove the whole return, delete it instead.';
    END IF;

    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(p_serials) AS s) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this return. Each serial can only be returned once.', v_dup;
    END IF;

    -- Guard pass: every serial currently on the return must still be safely
    -- reversible (not resold, still in stock).
    FOR rec IN
        SELECT serial_number
        FROM SalesReturnItems
        WHERE sales_return_id = p_return_id
    LOOP
        SELECT pu.unit_id, pu.in_stock INTO v_unit_id, v_in_stock
        FROM PurchaseUnits pu
        WHERE pu.serial_number = rec.serial_number
        LIMIT 1;

        IF v_unit_id IS NULL THEN
            RAISE EXCEPTION 'Serial "%" from this return no longer exists in stock records, so the return cannot be updated.', rec.serial_number;
        END IF;

        IF EXISTS (SELECT 1 FROM SoldUnits su WHERE su.unit_id = v_unit_id AND su.status = 'Sold') THEN
            RAISE EXCEPTION 'This sale return cannot be updated because serial "%" was sold again after the return. Delete or update the newer sale first.', rec.serial_number;
        END IF;

        IF v_in_stock = FALSE THEN
            RAISE EXCEPTION 'This sale return cannot be updated because serial "%" is no longer in stock (it may have been returned to the vendor).', rec.serial_number;
        END IF;
    END LOOP;

    -- Reverse old items
    FOR rec IN
        SELECT serial_number, item_id
        FROM SalesReturnItems
        WHERE sales_return_id = p_return_id
    LOOP
        SELECT pu.unit_id INTO v_unit_id
        FROM PurchaseUnits pu
        WHERE pu.serial_number = rec.serial_number
        LIMIT 1;

        -- Revert only the most recent 'Returned' record of this unit.
        UPDATE SoldUnits
        SET status = 'Sold'
        WHERE sold_unit_id = (
            SELECT su.sold_unit_id
            FROM SoldUnits su
            WHERE su.unit_id = v_unit_id AND su.status = 'Returned'
            ORDER BY su.sold_unit_id DESC
            LIMIT 1
        );

        UPDATE PurchaseUnits
        SET in_stock = FALSE
        WHERE unit_id = v_unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (rec.item_id, rec.serial_number, 'OUT', 'SalesReturn-Update-Reverse', p_return_id, 1);
    END LOOP;

    DELETE FROM SalesReturnItems WHERE sales_return_id = p_return_id;

    -- Insert new items
    FOR v_serial IN SELECT jsonb_array_elements_text(p_serials)
    LOOP
        IF v_serial IS NULL OR btrim(v_serial) = '' THEN
            RAISE EXCEPTION 'A blank serial number was submitted. Please remove empty serial entries.';
        END IF;

        SELECT su.sold_unit_id, su.unit_id, su.sold_price, si.item_id,
               si.sales_invoice_id, pu.serial_number, pi.unit_price, s.customer_id
        INTO v_unit
        FROM SoldUnits su
        JOIN SalesItems si    ON su.sales_item_id = si.sales_item_id
        JOIN SalesInvoices s  ON si.sales_invoice_id = s.sales_invoice_id
        JOIN PurchaseUnits pu ON su.unit_id = pu.unit_id
        JOIN PurchaseItems pi ON pu.purchase_item_id = pi.purchase_item_id
        WHERE pu.serial_number = v_serial
          AND su.status = 'Sold'
        ORDER BY su.sold_unit_id DESC
        LIMIT 1;

        IF NOT FOUND THEN
            SELECT EXISTS (SELECT 1 FROM PurchaseUnits pu WHERE pu.serial_number = v_serial)
            INTO v_exists;
            IF NOT v_exists THEN
                RAISE EXCEPTION 'Serial "%" does not exist in the system. Please check the serial number.', v_serial;
            ELSE
                RAISE EXCEPTION 'Serial "%" is not currently sold, so it cannot be returned. It may already have been returned or is still in stock.', v_serial;
            END IF;
        END IF;

        IF v_unit.customer_id <> v_customer_id THEN
            RAISE EXCEPTION 'Serial "%" was not sold to this customer. Please check the serial number.', v_serial;
        END IF;

        UPDATE SoldUnits SET status = 'Returned' WHERE sold_unit_id = v_unit.sold_unit_id;
        UPDATE PurchaseUnits SET in_stock = TRUE WHERE unit_id = v_unit.unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (v_unit.item_id, v_serial, 'IN', 'SalesReturn-Update', p_return_id, 1);

        INSERT INTO SalesReturnItems(sales_return_id, item_id, sold_price, cost_price, serial_number)
        VALUES (p_return_id, v_unit.item_id, v_unit.sold_price, v_unit.unit_price, v_serial);

        v_total := v_total + v_unit.sold_price;
    END LOOP;

    -- Update totals and last modifier
    UPDATE SalesReturns
    SET total_amount = v_total,
        created_by   = COALESCE(p_created_by, created_by)
    WHERE sales_return_id = p_return_id;

    PERFORM rebuild_sales_return_journal(p_return_id);
END;
$$;

-- Legacy 2-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.update_sale_return(p_return_id bigint, p_serials jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM public.update_sale_return(p_return_id, p_serials, NULL::integer);
END;
$$;


-- ============================================================================
-- HARDENING: delete_sale previously had no guard of its own; only the Django
-- view called validate_sales_delete. Now the function itself refuses to
-- delete an invoice that a sale return still references.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.delete_sale(p_invoice_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    rec RECORD;
    v_journal_id BIGINT;
    v_returned_count INT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM SalesInvoices WHERE sales_invoice_id = p_invoice_id) THEN
        RAISE EXCEPTION 'Sale invoice % was not found.', p_invoice_id;
    END IF;

    SELECT count(*) INTO v_returned_count
    FROM SoldUnits su
    JOIN SalesItems si ON su.sales_item_id = si.sales_item_id
    WHERE si.sales_invoice_id = p_invoice_id
      AND su.status = 'Returned';

    IF v_returned_count > 0 THEN
        RAISE EXCEPTION 'This sale invoice cannot be deleted because % serial(s) from it have been returned by the customer. Delete the related sale return first.', v_returned_count;
    END IF;

    -- 1. Restore stock for all sold units of this sale
    FOR rec IN
        SELECT su.unit_id, pu.serial_number, si.item_id
        FROM SoldUnits su
        JOIN SalesItems si ON su.sales_item_id = si.sales_item_id
        JOIN PurchaseUnits pu ON su.unit_id = pu.unit_id
        WHERE si.sales_invoice_id = p_invoice_id
    LOOP
        UPDATE PurchaseUnits
        SET in_stock = TRUE
        WHERE unit_id = rec.unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (rec.item_id, rec.serial_number, 'IN', 'SalesInvoice-Delete', p_invoice_id, 1);
    END LOOP;

    -- 2. Delete associated journal entries (accounting)
    SELECT journal_id INTO v_journal_id
    FROM SalesInvoices
    WHERE sales_invoice_id = p_invoice_id;

    IF v_journal_id IS NOT NULL THEN
        DELETE FROM JournalLines WHERE journal_id = v_journal_id;
        DELETE FROM JournalEntries WHERE journal_id = v_journal_id;
    END IF;

    -- 3. Delete the invoice (cascade removes SalesItems + SoldUnits)
    DELETE FROM SalesInvoices
    WHERE sales_invoice_id = p_invoice_id;
END;
$$;


-- ============================================================================
-- HARDENING: create_purchase gets the same strict payload validation as
-- create_sale: quantity must equal serial count, quantity and price must be
-- valid, serials must be unique in the payload and must not already exist in
-- the system (previously this surfaced as a raw unique-constraint error).
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_purchase(p_party_id bigint, p_invoice_date date, p_items jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_invoice_id       BIGINT;
    v_purchase_item_id BIGINT;
    v_total            NUMERIC(14,2) := 0;
    v_item_id          BIGINT;
    v_item             JSONB;
    v_serial           JSONB;
    v_item_name        TEXT;
    v_qty_text         TEXT;
    v_price_text       TEXT;
    v_qty              INT;
    v_serial_count     INT;
    v_dup              TEXT;
    v_existing         TEXT;
BEGIN
    -- Header validation -------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM Parties WHERE party_id = p_party_id) THEN
        RAISE EXCEPTION 'The selected vendor does not exist. Please choose a valid vendor.';
    END IF;
    IF p_invoice_date IS NULL THEN
        RAISE EXCEPTION 'Purchase date is required.';
    END IF;
    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'At least one item is required to create a purchase.';
    END IF;

    -- Duplicate serials inside the payload ------------------------------------
    SELECT s INTO v_dup
    FROM (SELECT (so->>'serial') AS s
          FROM jsonb_array_elements(p_items) it,
               jsonb_array_elements(it->'serials') so) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this purchase. Serial numbers must be unique.', v_dup;
    END IF;

    -- Serials that already exist in the system --------------------------------
    SELECT pu.serial_number INTO v_existing
    FROM PurchaseUnits pu
    WHERE pu.serial_number IN (
        SELECT (so->>'serial')
        FROM jsonb_array_elements(p_items) it,
             jsonb_array_elements(it->'serials') so
    )
    LIMIT 1;
    IF v_existing IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" already exists in the system from an earlier purchase. Serial numbers must be unique.', v_existing;
    END IF;

    -- Per-item validation ------------------------------------------------------
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        v_item_name  := NULLIF(btrim(COALESCE(v_item->>'item_name','')), '');
        v_qty_text   := v_item->>'qty';
        v_price_text := v_item->>'unit_price';

        IF v_item_name IS NULL THEN
            RAISE EXCEPTION 'Item name is missing for one of the purchase rows.';
        END IF;
        IF v_qty_text IS NULL OR v_qty_text !~ '^[0-9]+$' OR v_qty_text::INT <= 0 THEN
            RAISE EXCEPTION 'Quantity for item "%" must be a whole number greater than zero.', v_item_name;
        END IF;
        IF v_price_text IS NULL OR v_price_text !~ '^[0-9]+(\.[0-9]+)?$' THEN
            RAISE EXCEPTION 'Purchase price for item "%" must be a valid non-negative number.', v_item_name;
        END IF;
        IF v_item->'serials' IS NULL OR jsonb_typeof(v_item->'serials') <> 'array' THEN
            RAISE EXCEPTION 'Serial numbers are missing for item "%".', v_item_name;
        END IF;

        v_qty          := v_qty_text::INT;
        v_serial_count := jsonb_array_length(v_item->'serials');
        IF v_qty <> v_serial_count THEN
            RAISE EXCEPTION 'Quantity (%) does not match the number of serial numbers (%) for item "%". Please provide exactly one serial number per unit.', v_qty, v_serial_count, v_item_name;
        END IF;

        FOR v_serial IN SELECT * FROM jsonb_array_elements(v_item->'serials')
        LOOP
            IF NULLIF(btrim(COALESCE(v_serial->>'serial','')), '') IS NULL THEN
                RAISE EXCEPTION 'A blank serial number was submitted for item "%". Please remove empty serial entries.', v_item_name;
            END IF;
        END LOOP;
    END LOOP;

    -- Create the invoice -------------------------------------------------------
    INSERT INTO PurchaseInvoices(vendor_id, invoice_date, total_amount, created_by)
    VALUES (p_party_id, p_invoice_date, 0, p_created_by)
    RETURNING purchase_invoice_id INTO v_invoice_id;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        SELECT item_id INTO v_item_id FROM Items
        WHERE item_name = (v_item->>'item_name') LIMIT 1;
        IF v_item_id IS NULL THEN
            INSERT INTO Items(item_name, sale_price)
            VALUES ((v_item->>'item_name'), (v_item->>'unit_price')::NUMERIC)
            RETURNING item_id INTO v_item_id;
        END IF;

        INSERT INTO PurchaseItems(purchase_invoice_id, item_id, quantity, unit_price)
        VALUES (v_invoice_id, v_item_id, (v_item->>'qty')::INT, (v_item->>'unit_price')::NUMERIC)
        RETURNING purchase_item_id INTO v_purchase_item_id;

        v_total := v_total + ((v_item->>'qty')::INT * (v_item->>'unit_price')::NUMERIC);

        FOR v_serial IN SELECT * FROM jsonb_array_elements(v_item->'serials')
        LOOP
            INSERT INTO PurchaseUnits(purchase_item_id, serial_number, serial_comment, in_stock)
            VALUES (v_purchase_item_id, v_serial->>'serial',
                    NULLIF(TRIM(COALESCE(v_serial->>'comment', '')), ''), TRUE);
            INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
            VALUES (v_item_id, v_serial->>'serial', 'IN', 'PurchaseInvoice', v_invoice_id, 1);
        END LOOP;
    END LOOP;

    UPDATE PurchaseInvoices SET total_amount = v_total WHERE purchase_invoice_id = v_invoice_id;
    PERFORM rebuild_purchase_journal(v_invoice_id);
    RETURN v_invoice_id;
END;
$$;

-- Legacy 3-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.create_purchase(p_party_id bigint, p_invoice_date date, p_items jsonb) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN public.create_purchase(p_party_id, p_invoice_date, p_items, NULL::integer);
END;
$$;


-- ============================================================================
-- HARDENING: update_purchase_invoice gets the same strict payload validation.
-- Its existing serial/sold-state validation (validate_purchase_update2) is
-- unchanged and still enforced.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_purchase_invoice(p_invoice_id bigint, p_items jsonb, p_party_name text DEFAULT NULL::text, p_invoice_date date DEFAULT NULL::date, p_created_by integer DEFAULT NULL::integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_item              JSONB;
    v_item_id           BIGINT;
    v_total             NUMERIC(14,2) := 0;
    v_purchase_item_id  BIGINT;
    v_serial            JSONB;
    v_new_party_id      BIGINT;
    v_existing_serials  TEXT[];
    v_new_serials       TEXT[];
    v_serials_to_remove TEXT[];
    v_serials_to_keep   TEXT[];
    v_validation        JSONB;
    v_temp_item_id      BIGINT := -999999;
    v_item_name         TEXT;
    v_qty_text          TEXT;
    v_price_text        TEXT;
    v_qty               INT;
    v_serial_count      INT;
    v_dup               TEXT;
    v_conflict          TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM PurchaseInvoices WHERE purchase_invoice_id = p_invoice_id) THEN
        RAISE EXCEPTION 'Purchase invoice % was not found.', p_invoice_id;
    END IF;

    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'At least one item is required on the purchase invoice.';
    END IF;

    -- Duplicate serials inside the payload
    SELECT s INTO v_dup
    FROM (SELECT (so->>'serial') AS s
          FROM jsonb_array_elements(p_items) it,
               jsonb_array_elements(it->'serials') so) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this purchase. Serial numbers must be unique.', v_dup;
    END IF;

    -- Per-item payload validation
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        v_item_name  := NULLIF(btrim(COALESCE(v_item->>'item_name','')), '');
        v_qty_text   := v_item->>'qty';
        v_price_text := v_item->>'unit_price';

        IF v_item_name IS NULL THEN
            RAISE EXCEPTION 'Item name is missing for one of the purchase rows.';
        END IF;
        IF v_qty_text IS NULL OR v_qty_text !~ '^[0-9]+$' OR v_qty_text::INT <= 0 THEN
            RAISE EXCEPTION 'Quantity for item "%" must be a whole number greater than zero.', v_item_name;
        END IF;
        IF v_price_text IS NULL OR v_price_text !~ '^[0-9]+(\.[0-9]+)?$' THEN
            RAISE EXCEPTION 'Purchase price for item "%" must be a valid non-negative number.', v_item_name;
        END IF;
        IF v_item->'serials' IS NULL OR jsonb_typeof(v_item->'serials') <> 'array' THEN
            RAISE EXCEPTION 'Serial numbers are missing for item "%".', v_item_name;
        END IF;

        v_qty          := v_qty_text::INT;
        v_serial_count := jsonb_array_length(v_item->'serials');
        IF v_qty <> v_serial_count THEN
            RAISE EXCEPTION 'Quantity (%) does not match the number of serial numbers (%) for item "%". Please provide exactly one serial number per unit.', v_qty, v_serial_count, v_item_name;
        END IF;

        FOR v_serial IN SELECT * FROM jsonb_array_elements(v_item->'serials')
        LOOP
            IF NULLIF(btrim(COALESCE(v_serial->>'serial','')), '') IS NULL THEN
                RAISE EXCEPTION 'A blank serial number was submitted for item "%". Please remove empty serial entries.', v_item_name;
            END IF;
        END LOOP;
    END LOOP;

    -- Validate (sold serials cannot be removed, etc.)
    v_validation := validate_purchase_update2(p_invoice_id, p_items);
    IF (v_validation->>'is_valid')::BOOLEAN = FALSE THEN
        RAISE EXCEPTION '%', v_validation->>'message';
    END IF;

    -- Update Party
    IF p_party_name IS NOT NULL THEN
        SELECT party_id INTO v_new_party_id
        FROM Parties WHERE party_name = p_party_name LIMIT 1;

        IF v_new_party_id IS NULL THEN
            RAISE EXCEPTION 'Vendor "%" does not exist. Please check the party name.', p_party_name;
        END IF;

        UPDATE PurchaseInvoices
        SET vendor_id = v_new_party_id
        WHERE purchase_invoice_id = p_invoice_id;
    END IF;

    -- Update Date
    IF p_invoice_date IS NOT NULL THEN
        UPDATE PurchaseInvoices
        SET invoice_date = p_invoice_date
        WHERE purchase_invoice_id = p_invoice_id;
    END IF;

    -- Update last modifier
    IF p_created_by IS NOT NULL THEN
        UPDATE PurchaseInvoices
        SET created_by = p_created_by
        WHERE purchase_invoice_id = p_invoice_id;
    END IF;

    -- Existing serials
    SELECT ARRAY_AGG(pu.serial_number)
    INTO v_existing_serials
    FROM PurchaseUnits pu
    JOIN PurchaseItems pi ON pu.purchase_item_id = pi.purchase_item_id
    WHERE pi.purchase_invoice_id = p_invoice_id;

    IF v_existing_serials IS NULL THEN v_existing_serials := ARRAY[]::TEXT[]; END IF;

    -- New serials from JSON
    SELECT ARRAY_AGG(serial_obj->>'serial')
    INTO v_new_serials
    FROM jsonb_array_elements(p_items) AS item,
         jsonb_array_elements(item->'serials') AS serial_obj;

    IF v_new_serials IS NULL THEN v_new_serials := ARRAY[]::TEXT[]; END IF;

    -- Newly added serials must not already exist somewhere else
    SELECT pu.serial_number INTO v_conflict
    FROM PurchaseUnits pu
    WHERE pu.serial_number = ANY(v_new_serials)
      AND pu.serial_number <> ALL(v_existing_serials)
    LIMIT 1;
    IF v_conflict IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" already exists in the system from another purchase. Serial numbers must be unique.', v_conflict;
    END IF;

    -- Serials to remove
    SELECT ARRAY_AGG(s) INTO v_serials_to_remove
    FROM unnest(v_existing_serials) AS s WHERE s <> ALL(v_new_serials);
    IF v_serials_to_remove IS NULL THEN v_serials_to_remove := ARRAY[]::TEXT[]; END IF;

    -- Serials to keep
    SELECT ARRAY_AGG(s) INTO v_serials_to_keep
    FROM unnest(v_existing_serials) AS s WHERE s = ANY(v_new_serials);
    IF v_serials_to_keep IS NULL THEN v_serials_to_keep := ARRAY[]::TEXT[]; END IF;

    -- Temp item placeholder
    INSERT INTO PurchaseItems(purchase_invoice_id, item_id, quantity, unit_price)
    VALUES (p_invoice_id, 1, 1, 0)
    RETURNING purchase_item_id INTO v_temp_item_id;

    UPDATE PurchaseUnits SET purchase_item_id = v_temp_item_id
    WHERE serial_number = ANY(v_serials_to_keep);

    -- Remove old stock movements for removed serials
    DELETE FROM StockMovements
    WHERE reference_type = 'PurchaseInvoice'
      AND reference_id = p_invoice_id
      AND serial_number = ANY(v_serials_to_remove);

    -- Delete old items
    DELETE FROM PurchaseItems
    WHERE purchase_invoice_id = p_invoice_id
      AND purchase_item_id != v_temp_item_id;

    -- Recreate items
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        SELECT item_id INTO v_item_id
        FROM Items WHERE item_name = (v_item->>'item_name') LIMIT 1;

        IF v_item_id IS NULL THEN
            INSERT INTO Items(item_name, sale_price)
            VALUES ((v_item->>'item_name'), (v_item->>'unit_price')::NUMERIC)
            RETURNING item_id INTO v_item_id;
        END IF;

        INSERT INTO PurchaseItems(purchase_invoice_id, item_id, quantity, unit_price)
        VALUES (p_invoice_id, v_item_id,
                (v_item->>'qty')::INT, (v_item->>'unit_price')::NUMERIC)
        RETURNING purchase_item_id INTO v_purchase_item_id;

        v_total := v_total + ((v_item->>'qty')::INT * (v_item->>'unit_price')::NUMERIC);

        FOR v_serial IN SELECT * FROM jsonb_array_elements(v_item->'serials')
        LOOP
            IF (v_serial->>'serial') = ANY(v_serials_to_keep) THEN
                UPDATE PurchaseUnits
                SET purchase_item_id = v_purchase_item_id,
                    serial_comment = NULLIF(TRIM(COALESCE(v_serial->>'comment','')), '')
                WHERE serial_number = v_serial->>'serial'
                  AND purchase_item_id = v_temp_item_id;
            ELSE
                INSERT INTO PurchaseUnits(purchase_item_id, serial_number, serial_comment, in_stock)
                VALUES (v_purchase_item_id, v_serial->>'serial',
                        NULLIF(TRIM(COALESCE(v_serial->>'comment','')), ''), TRUE);

                INSERT INTO StockMovements(item_id, serial_number, movement_type,
                                           reference_type, reference_id, quantity)
                VALUES (v_item_id, v_serial->>'serial', 'IN', 'PurchaseInvoice', p_invoice_id, 1);
            END IF;
        END LOOP;
    END LOOP;

    DELETE FROM PurchaseItems WHERE purchase_item_id = v_temp_item_id;

    UPDATE PurchaseInvoices SET total_amount = v_total
    WHERE purchase_invoice_id = p_invoice_id;

    PERFORM rebuild_purchase_journal(p_invoice_id);
END;
$$;

-- Legacy 4-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.update_purchase_invoice(p_invoice_id bigint, p_items jsonb, p_party_name text DEFAULT NULL::text, p_invoice_date date DEFAULT NULL::date) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM public.update_purchase_invoice(p_invoice_id, p_items, p_party_name, p_invoice_date, NULL::integer);
END;
$$;


-- ============================================================================
-- HARDENING: create_purchase_return previously did NOT check stock state, so
-- a serial that was currently SOLD to a customer (or already returned to the
-- vendor) could still be "returned to vendor", corrupting stock and journals.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_purchase_return(p_party_name text, p_serials jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_return_id BIGINT;
    v_vendor_id BIGINT;
    v_serial    TEXT;
    v_rec       RECORD;
    v_total     NUMERIC(14,2) := 0;
    v_dup       TEXT;
    v_exists    BOOLEAN;
BEGIN
    IF p_serials IS NULL OR jsonb_typeof(p_serials) <> 'array' OR jsonb_array_length(p_serials) = 0 THEN
        RAISE EXCEPTION 'At least one serial number is required to create a purchase return.';
    END IF;

    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(p_serials) AS s) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this return. Each serial can only be returned once.', v_dup;
    END IF;

    SELECT party_id INTO v_vendor_id FROM Parties WHERE party_name = p_party_name LIMIT 1;
    IF v_vendor_id IS NULL THEN
        RAISE EXCEPTION 'Vendor "%" does not exist. Please check the party name.', p_party_name;
    END IF;

    INSERT INTO PurchaseReturns(vendor_id, return_date, total_amount, created_by)
    VALUES (v_vendor_id, CURRENT_DATE, 0, p_created_by)
    RETURNING purchase_return_id INTO v_return_id;

    FOR v_serial IN SELECT jsonb_array_elements_text(p_serials)
    LOOP
        IF v_serial IS NULL OR btrim(v_serial) = '' THEN
            RAISE EXCEPTION 'A blank serial number was submitted. Please remove empty serial entries.';
        END IF;

        SELECT pu.unit_id, pu.in_stock, pu.purchase_item_id, pi2.unit_price, pi2.item_id,
               pi2.purchase_invoice_id, pu.serial_number
        INTO v_rec
        FROM PurchaseUnits pu
        JOIN PurchaseItems pi2 ON pu.purchase_item_id = pi2.purchase_item_id
        JOIN PurchaseInvoices pinv ON pi2.purchase_invoice_id = pinv.purchase_invoice_id
        WHERE pu.serial_number = v_serial AND pinv.vendor_id = v_vendor_id;

        IF NOT FOUND THEN
            SELECT EXISTS (SELECT 1 FROM PurchaseUnits pu WHERE pu.serial_number = v_serial)
            INTO v_exists;
            IF NOT v_exists THEN
                RAISE EXCEPTION 'Serial "%" does not exist in the system. Please check the serial number.', v_serial;
            ELSE
                RAISE EXCEPTION 'Serial "%" was not purchased from vendor "%". Please select the vendor it was actually purchased from.', v_serial, p_party_name;
            END IF;
        END IF;

        IF v_rec.in_stock = FALSE THEN
            RAISE EXCEPTION 'Serial "%" is not in stock, so it cannot be returned to the vendor. It may be sold to a customer or already returned.', v_serial;
        END IF;

        UPDATE PurchaseUnits SET in_stock = FALSE WHERE unit_id = v_rec.unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (v_rec.item_id, v_serial, 'OUT', 'PurchaseReturn', v_return_id, 1);

        INSERT INTO PurchaseReturnItems(purchase_return_id, item_id, unit_price, serial_number)
        VALUES (v_return_id, v_rec.item_id, v_rec.unit_price, v_serial);

        v_total := v_total + v_rec.unit_price;
    END LOOP;

    UPDATE PurchaseReturns SET total_amount = v_total WHERE purchase_return_id = v_return_id;
    PERFORM rebuild_purchase_return_journal(v_return_id);
    RETURN v_return_id;
END;
$$;

-- Legacy 2-argument overload delegates to the fixed version.
CREATE OR REPLACE FUNCTION public.create_purchase_return(p_party_name text, p_serials jsonb) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN public.create_purchase_return(p_party_name, p_serials, NULL::integer);
END;
$$;


-- ============================================================================
-- HARDENING: update_purchase_return gains empty-payload and duplicate-serial
-- checks (its in-stock check already existed).
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_purchase_return(p_return_id bigint, p_serials jsonb, p_created_by integer DEFAULT NULL::integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    rec         RECORD;
    v_serial    TEXT;
    v_unit      RECORD;
    v_total     NUMERIC(14,2) := 0;
    v_vendor_id BIGINT;
    v_dup       TEXT;
BEGIN
    -- Get vendor id
    SELECT vendor_id INTO v_vendor_id
    FROM PurchaseReturns WHERE purchase_return_id = p_return_id;

    IF v_vendor_id IS NULL THEN
        RAISE EXCEPTION 'Purchase return % was not found.', p_return_id;
    END IF;

    IF p_serials IS NULL OR jsonb_typeof(p_serials) <> 'array' OR jsonb_array_length(p_serials) = 0 THEN
        RAISE EXCEPTION 'At least one serial number is required. To remove the whole return, delete it instead.';
    END IF;

    SELECT s INTO v_dup
    FROM (SELECT jsonb_array_elements_text(p_serials) AS s) q
    GROUP BY s HAVING count(*) > 1 LIMIT 1;
    IF v_dup IS NOT NULL THEN
        RAISE EXCEPTION 'Serial "%" appears more than once in this return. Each serial can only be returned once.', v_dup;
    END IF;

    -- Reverse old items (restore stock)
    FOR rec IN
        SELECT serial_number, item_id
        FROM PurchaseReturnItems
        WHERE purchase_return_id = p_return_id
    LOOP
        UPDATE PurchaseUnits SET in_stock = TRUE
        WHERE serial_number = rec.serial_number;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (rec.item_id, rec.serial_number, 'IN', 'PurchaseReturn-Update-Reverse', p_return_id, 1);
    END LOOP;

    -- Remove old items
    DELETE FROM PurchaseReturnItems WHERE purchase_return_id = p_return_id;

    -- Insert new items
    FOR v_serial IN SELECT jsonb_array_elements_text(p_serials)
    LOOP
        IF v_serial IS NULL OR btrim(v_serial) = '' THEN
            RAISE EXCEPTION 'A blank serial number was submitted. Please remove empty serial entries.';
        END IF;

        SELECT pu.unit_id, pu.serial_number, pi.item_id, pi.unit_price, p.vendor_id
        INTO v_unit
        FROM PurchaseUnits pu
        JOIN PurchaseItems pi     ON pu.purchase_item_id = pi.purchase_item_id
        JOIN PurchaseInvoices p   ON pi.purchase_invoice_id = p.purchase_invoice_id
        WHERE pu.serial_number = v_serial;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Serial "%" does not exist in the system. Please check the serial number.', v_serial;
        END IF;

        IF v_unit.vendor_id <> v_vendor_id THEN
            RAISE EXCEPTION 'Serial "%" was not purchased from this vendor. Please check the serial number.', v_serial;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM PurchaseUnits WHERE unit_id = v_unit.unit_id AND in_stock = TRUE
        ) THEN
            RAISE EXCEPTION 'Serial "%" is not in stock, so it cannot be returned to the vendor. It may be sold to a customer or already returned.', v_serial;
        END IF;

        UPDATE PurchaseUnits SET in_stock = FALSE WHERE unit_id = v_unit.unit_id;

        INSERT INTO StockMovements(item_id, serial_number, movement_type, reference_type, reference_id, quantity)
        VALUES (v_unit.item_id, v_serial, 'OUT', 'PurchaseReturn-Update', p_return_id, 1);

        INSERT INTO PurchaseReturnItems(purchase_return_id, item_id, unit_price, serial_number)
        VALUES (p_return_id, v_unit.item_id, v_unit.unit_price, v_serial);

        v_total := v_total + v_unit.unit_price;
    END LOOP;

    -- Update totals and last modifier
    UPDATE PurchaseReturns
    SET total_amount = v_total,
        created_by   = COALESCE(p_created_by, created_by)
    WHERE purchase_return_id = p_return_id;

    PERFORM rebuild_purchase_return_journal(p_return_id);
END;
$$;

COMMIT;

-- ============================================================================
-- READ-ONLY DATA DIAGNOSTICS
-- These queries DO NOT modify anything. They report rows that may have been
-- corrupted while the bugs above were live. Review any output manually.
-- ============================================================================

\echo ''
\echo '=== Diagnostic 1: serials with more than one ACTIVE Sold record (should be empty) ==='
SELECT pu.serial_number, count(*) AS active_sold_records
FROM SoldUnits su
JOIN PurchaseUnits pu ON pu.unit_id = su.unit_id
WHERE su.status = 'Sold'
GROUP BY pu.serial_number
HAVING count(*) > 1
ORDER BY pu.serial_number;

\echo ''
\echo '=== Diagnostic 2: serials marked in stock but with an ACTIVE Sold record (should be empty) ==='
SELECT pu.serial_number, pu.in_stock
FROM PurchaseUnits pu
WHERE pu.in_stock = TRUE
  AND EXISTS (SELECT 1 FROM SoldUnits su WHERE su.unit_id = pu.unit_id AND su.status = 'Sold')
ORDER BY pu.serial_number;

\echo ''
\echo '=== Diagnostic 3: serials out of stock with no active sale and no purchase return (ghost stock, should be empty) ==='
SELECT pu.serial_number
FROM PurchaseUnits pu
WHERE pu.in_stock = FALSE
  AND NOT EXISTS (SELECT 1 FROM SoldUnits su WHERE su.unit_id = pu.unit_id AND su.status = 'Sold')
  AND NOT EXISTS (SELECT 1 FROM PurchaseReturnItems pri WHERE pri.serial_number = pu.serial_number)
ORDER BY pu.serial_number;

\echo ''
\echo '=== Diagnostic 4: journal entries with no lines (should be empty) ==='
SELECT je.journal_id, je.entry_date, je.description
FROM JournalEntries je
LEFT JOIN JournalLines jl ON jl.journal_id = je.journal_id
WHERE jl.line_id IS NULL
ORDER BY je.journal_id;

\echo ''
\echo '=== Diagnostic 5: overall debit/credit balance (both totals must be equal) ==='
SELECT COALESCE(sum(debit),0) AS total_debit, COALESCE(sum(credit),0) AS total_credit
FROM JournalLines;

\echo ''
\echo 'production_fixes.sql applied successfully.'
