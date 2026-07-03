(function () {
  "use strict";

  const ENHANCED = "smartDescriptionEnhanced";
  const VALUE_SETTER = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  const VALUE_GETTER = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").get;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function parseCsvLine(line) {
    const cells = [];
    let cell = "";
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (ch === '"') {
        if (quoted && line[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          quoted = !quoted;
        }
      } else if (ch === "," && !quoted) {
        cells.push(cell.trim());
        cell = "";
      } else {
        cell += ch;
      }
    }
    cells.push(cell.trim());
    return cells;
  }

  function normalizeRows(rows) {
    const width = Math.max(...rows.map((row) => row.length));
    return rows.map((row) => {
      const copy = row.slice();
      while (copy.length < width) copy.push("");
      return copy;
    });
  }

  function parseTable(text) {
    const clean = String(text || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (!clean) return null;
    const lines = clean.split("\n").filter((line) => line.trim() !== "");
    if (lines.length < 2) return null;

    let rows = null;
    if (lines.some((line) => line.includes("\t"))) {
      rows = lines.map((line) => line.split("\t").map((cell) => cell.trim()));
    } else if (lines.every((line) => line.includes(","))) {
      rows = lines.map(parseCsvLine);
    }

    if (!rows) return null;
    rows = rows.filter((row) => row.length > 1);
    if (rows.length < 2) return null;

    const maxWidth = Math.max(...rows.map((row) => row.length));
    const rowsWithData = rows.filter((row) => row.some((cell) => cell.trim() !== ""));
    if (maxWidth < 2 || rowsWithData.length < 2) return null;

    return normalizeRows(rows);
  }

  function rowsToText(rows) {
    return rows.map((row) => row.map((cell) => String(cell ?? "").replace(/\t/g, " ").replace(/\n/g, " ")).join("\t")).join("\n");
  }

  function tableFromDom(table) {
    return Array.from(table.rows).map((tr) =>
      Array.from(tr.cells).map((cell) => cell.textContent.trim())
    );
  }

  function renderTable(rows, className) {
    const head = rows[0] || [];
    const body = rows.slice(1);
    return `
      <table class="${className}" data-smart-desc-table>
        <thead>
          <tr>${head.map((cell) => `<th contenteditable="true">${escapeHtml(cell)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${body.map((row) => `<tr>${row.map((cell) => `<td contenteditable="true">${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    `;
  }

  function renderInlineTable(rows) {
    return `
      ${renderTable(rows, "smart-desc__table")}
      <div class="smart-desc__table-summary">
        <span>${Math.max(rows.length - 1, 0)} rows</span>
        <span>${rows[0]?.length || 0} columns</span>
      </div>
    `;
  }

  function formatCount(textarea) {
    const value = VALUE_GETTER.call(textarea);
    const max = Number(textarea.getAttribute("maxlength")) || 1000;
    return `${value.length} / ${max}`;
  }

  function setNativeValue(textarea, value) {
    VALUE_SETTER.call(textarea, value);
  }

  function dispatchInput(textarea) {
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    textarea.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function copyText(text, button) {
    try {
      await navigator.clipboard.writeText(text || "");
    } catch (_) {
      const temp = document.createElement("textarea");
      temp.value = text || "";
      temp.style.position = "fixed";
      temp.style.left = "-9999px";
      document.body.appendChild(temp);
      temp.select();
      document.execCommand("copy");
      temp.remove();
    }
    button.classList.add("is-copied");
    const original = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-check"></i>';
    setTimeout(() => {
      button.classList.remove("is-copied");
      button.innerHTML = original;
    }, 900);
  }

  function enhance(textarea) {
    if (!textarea || textarea.dataset[ENHANCED] === "1") return;
    textarea.dataset[ENHANCED] = "1";

    const wrapper = document.createElement("div");
    wrapper.className = "smart-desc";
    wrapper.innerHTML = `
      <div class="smart-desc__bar">
        <div class="smart-desc__meta">
          <span class="smart-desc__mode"><i class="fa-solid fa-wand-magic-sparkles"></i> Smart note</span>
          <span class="smart-desc__count">0</span>
        </div>
        <div class="smart-desc__actions">
          <button type="button" class="smart-desc__btn" data-sd-copy title="Copy description"><i class="fa-regular fa-copy"></i> Copy</button>
          <button type="button" class="smart-desc__btn smart-desc__btn--text" data-sd-raw title="Show or hide raw text">Edit raw</button>
          <button type="button" class="smart-desc__btn" data-sd-expand title="Expand editor"><i class="fa-solid fa-up-right-and-down-left-from-center"></i> Expand</button>
        </div>
      </div>
      <div class="smart-desc__table-wrap"></div>
    `;

    textarea.parentNode.insertBefore(wrapper, textarea);
    wrapper.appendChild(textarea);

    const tableWrap = wrapper.querySelector(".smart-desc__table-wrap");
    const mode = wrapper.querySelector(".smart-desc__mode");
    const count = wrapper.querySelector(".smart-desc__count");
    const rawButton = wrapper.querySelector("[data-sd-raw]");
    const copyButton = wrapper.querySelector("[data-sd-copy]");
    const expandButton = wrapper.querySelector("[data-sd-expand]");

    let tableRows = null;
    let syncing = false;

    function syncFromTable() {
      const table = tableWrap.querySelector("[data-smart-desc-table]");
      if (!table) return;
      tableRows = tableFromDom(table);
      syncing = true;
      setNativeValue(textarea, rowsToText(tableRows));
      dispatchInput(textarea);
      syncing = false;
      count.textContent = formatCount(textarea);
      const summary = tableWrap.querySelector(".smart-desc__table-summary");
      if (summary) {
        summary.innerHTML = `<span>${Math.max(tableRows.length - 1, 0)} rows</span><span>${tableRows[0]?.length || 0} columns</span>`;
      }
    }

    function update(shouldParse) {
      const value = VALUE_GETTER.call(textarea);
      const parsed = shouldParse ? parseTable(value) : tableRows;
      if (parsed) {
        tableRows = parsed;
        wrapper.classList.add("is-table");
        mode.innerHTML = '<i class="fa-solid fa-table"></i> Smart note';
        tableWrap.innerHTML = renderInlineTable(tableRows);
      } else {
        tableRows = null;
        wrapper.classList.remove("is-table", "is-raw");
        mode.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Smart note';
        tableWrap.innerHTML = "";
      }
      count.textContent = formatCount(textarea);
      rawButton.style.display = tableRows ? "inline-flex" : "none";
    }

    Object.defineProperty(textarea, "value", {
      configurable: true,
      get() {
        return VALUE_GETTER.call(this);
      },
      set(value) {
        VALUE_SETTER.call(this, value);
        if (!syncing) update(true);
      },
    });

    textarea.addEventListener("input", () => {
      if (!syncing) update(true);
    });

    textarea.addEventListener("paste", () => {
      setTimeout(() => update(true), 0);
    });

    tableWrap.addEventListener("input", syncFromTable);
    tableWrap.addEventListener("blur", syncFromTable, true);

    rawButton.addEventListener("click", () => {
      wrapper.classList.toggle("is-raw");
      rawButton.textContent = wrapper.classList.contains("is-raw") ? "Preview" : "Edit raw";
    });

    copyButton.addEventListener("click", () => {
      copyText(tableRows ? rowsToText(tableRows) : VALUE_GETTER.call(textarea), copyButton);
    });

    expandButton.addEventListener("click", () => openExpandedEditor(textarea, tableRows));

    function openExpandedEditor(field, currentRows) {
      const currentValue = VALUE_GETTER.call(field);
      const currentTable = currentRows || parseTable(currentValue);
      if (!window.Swal) {
        const nextValue = window.prompt("Description", currentValue);
        if (nextValue !== null) {
          field.value = nextValue;
          dispatchInput(field);
        }
        return;
      }

      const html = currentTable
        ? `<div class="smart-desc-modal"><div class="smart-desc-modal__hint"><i class="fa-solid fa-table"></i> Edit cells directly. Apply keeps the same spreadsheet-friendly format.</div><div class="smart-desc-modal__table-wrap">${renderTable(currentTable, "")}</div></div>`
        : `<div class="smart-desc-modal"><div class="smart-desc-modal__hint"><i class="fa-solid fa-wand-magic-sparkles"></i> Edit the note, then apply it to the description field.</div><textarea data-sd-modal-textarea>${escapeHtml(currentValue)}</textarea></div>`;

      Swal.fire({
        title: "Description",
        html,
        width: currentTable ? "980px" : "680px",
        showCancelButton: true,
        confirmButtonText: "Apply",
        cancelButtonText: "Close",
        confirmButtonColor: "#2f80ed",
        cancelButtonColor: "#64748b",
        customClass: { popup: "smart-desc-swal" },
        preConfirm: () => {
          const popup = Swal.getPopup();
          const modalTable = popup.querySelector("[data-smart-desc-table]");
          const modalText = popup.querySelector("[data-sd-modal-textarea]");
          return modalTable ? rowsToText(tableFromDom(modalTable)) : modalText.value;
        },
      }).then((result) => {
        if (!result.isConfirmed) return;
        field.value = result.value || "";
        dispatchInput(field);
      });
    }

    update(true);
  }

  function initSmartDescriptions() {
    document.querySelectorAll('textarea[name="description"]').forEach(enhance);
  }

  document.addEventListener("DOMContentLoaded", initSmartDescriptions);
  window.refreshSmartDescriptions = initSmartDescriptions;
})();
