// $(function () {

//   /* ══════════════════════════════════
//      CONFIG
//   ══════════════════════════════════ */
//   const AUTOCOMPLETE_URL = $("#hubSearchInput").data("autocomplete-url");
//   const UPDATE_URL       = $("#hubSearchInput").data("update-url");
//   const PAGE_SIZE        = 10;
//   const PARTIES_URL = $("#hubSearchInput").data("parties-url");

//   let allParties  = [];
//   let filtered    = [];
//   let currentPage = 1;

//   /* ══════════════════════════════════
//      FETCH ALL PARTIES
//      Uses your existing autocomplete endpoint
//      with empty term to get initial data,
//      then loads full list via a broader query.
//      (Adjust endpoint if you add a dedicated list view)
//   ══════════════════════════════════ */

  
//     function loadParties() {
//         $.ajax({
//             url: PARTIES_URL,
//             method: "GET",
//             dataType: "json",

//             success: function (data) {

//             allParties = data.map(function (p, i) {
//                 return {
//                 name: p.party_name,     // ✅ FIXED
//                 type: p.party_type,     // ✅ FIXED
//                 idx: i
//                 };
//             });

//             filtered = [...allParties];

//             renderStats();
//             renderTable();

//             $("#tableLoading").hide();

//             if (allParties.length === 0) {
//                 $("#emptyState").show();
//             } else {
//                 $("#tableContainer").show();
//             }
//             },

//             error: function (xhr) {
//             console.error(xhr.responseText);
//             $("#tableLoading").html(
//                 '<p style="color:#f87171;">Failed to load parties.</p>'
//             );
//             }
//         });
//     }

//   /* ══════════════════════════════════
//      STATS
//   ══════════════════════════════════ */
//   function renderStats() {
//     const total = allParties.length;

//     const bothCount = allParties.filter(p => p.type === "Both").length;
//     const expenseCount = allParties.filter(p => p.type === "Expense").length;

//     $("#statTotal").text(total);
//     $("#statBoth").text(bothCount);
//     $("#statExpense").text(expenseCount);
//     }

//   /* ══════════════════════════════════
//      TABLE RENDER
//   ══════════════════════════════════ */
//   function renderTable() {
//     const start = (currentPage - 1) * PAGE_SIZE;
//     const page  = filtered.slice(start, start + PAGE_SIZE);
//     const $body = $("#partiesTableBody").empty();

//     if (page.length === 0) {
//       $body.append(`
//         <tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">
//           No parties match your search.
//         </td></tr>
//       `);
//     } else {
//       page.forEach(function (p) {
//         const initials = p.name.slice(0, 2);
//         const row = `
//           <tr>
//             <td>
//               <span class="td-avatar both">${initials}</span>
//               <span class="td-name">${p.name}</span>
//             </td>
//             <td>
//                 <span class="td-badge ${p.type.toLowerCase()}">
//                     ${p.type}
//                 </span>
//             </td>
//             <td style="color:var(--text-muted);font-size:13px;">—</td>
//             <td class="td-balance debit">—</td>
//             <td>
//               <div class="td-actions">
//                 <a class="tbl-btn edit" href="${UPDATE_URL}?search_name=${encodeURIComponent(p.name)}">
//                   <i class="fa-solid fa-pen-to-square"></i> Edit
//                 </a>
//               </div>
//             </td>
//           </tr>
//         `;
//         $body.append(row);
//       });
//     }

//     renderPagination();
//   }

//   /* ══════════════════════════════════
//      PAGINATION
//   ══════════════════════════════════ */
//   function renderPagination() {
//     const total = filtered.length;
//     const pages = Math.ceil(total / PAGE_SIZE);
//     const start = (currentPage - 1) * PAGE_SIZE + 1;
//     const end   = Math.min(currentPage * PAGE_SIZE, total);

//     $("#pagInfo").text(
//       total === 0 ? 'No results' : `Showing ${start}–${end} of ${total}`
//     );

//     const $btns = $("#pagBtns").empty();

//     // Prev
//     $btns.append(
//       $('<button class="pag-btn">‹ Prev</button>')
//         .prop('disabled', currentPage === 1)
//         .css('opacity', currentPage === 1 ? 0.4 : 1)
//         .on('click', function () { if (currentPage > 1) { currentPage--; renderTable(); } })
//     );

//     // Page numbers (show up to 5)
//     const range = getPageRange(currentPage, pages);
//     range.forEach(function (pg) {
//       $btns.append(
//         $(`<button class="pag-btn ${pg === currentPage ? 'active' : ''}">${pg}</button>`)
//           .on('click', function () { currentPage = pg; renderTable(); })
//       );
//     });

//     // Next
//     $btns.append(
//       $('<button class="pag-btn">Next ›</button>')
//         .prop('disabled', currentPage >= pages)
//         .css('opacity', currentPage >= pages ? 0.4 : 1)
//         .on('click', function () { if (currentPage < pages) { currentPage++; renderTable(); } })
//     );
//   }

//   function getPageRange(cur, total) {
//     const delta = 2;
//     const range = [];
//     for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) {
//       range.push(i);
//     }
//     return range;
//   }

//   /* ══════════════════════════════════
//      SEARCH / FILTER
//   ══════════════════════════════════ */
//   const $hubInput  = $("#hubSearchInput");
//   const $hubSugg   = $("#hubSuggestions");

//   $hubInput.on("input", function () {
//     const q = $(this).val().trim().toUpperCase();

//     // Filter table
//     if (q.length > 0) {
//       filtered = allParties.filter(p => p.name.toUpperCase().includes(q));
//     } else {
//       filtered = [...allParties];
//     }
//     currentPage = 1;
//     renderTable();

//     // Autocomplete dropdown
//     if (q.length < 1) { $hubSugg.hide().empty(); return; }

//     $.ajax({
//       url: AUTOCOMPLETE_URL,
//       data: { term: q },
//       dataType: 'json',
//       success: function (data) {
//         $hubSugg.empty();
//         if (data.length) {
//           data.slice(0, 6).forEach(function (name) {
//             const $item = $(`
//               <div class="suggestion-item">
//                 <div class="si-icon"><i class="fa-solid fa-user"></i></div>
//                 <span class="si-name">${name}</span>
//                 <span class="si-hint">Edit →</span>
//               </div>
//             `).on('click', function () {
//               window.location.href = UPDATE_URL + '?search_name=' + encodeURIComponent(name);
//             });
//             $hubSugg.append($item);
//           });
//           $hubSugg.show();
//         } else {
//           $hubSugg.hide();
//         }
//       }
//     });
//   });

//   $(document).on('click', function (e) {
//     if (!$(e.target).closest('#hubSearchInput, #hubSuggestions').length) {
//       $hubSugg.hide();
//     }
//   });

//   /* ══════════════════════════════════
//      INIT
//   ══════════════════════════════════ */
//   loadParties();

// });





$(function () {

  /* ══════════════════════════════════
     CONFIG
  ══════════════════════════════════ */
  const AUTOCOMPLETE_URL = $("#hubSearchInput").data("autocomplete-url");
  const UPDATE_URL       = $("#hubSearchInput").data("update-url");
  const PAGE_SIZE        = 10;
  const PARTIES_URL      = $("#hubSearchInput").data("parties-url");

  let allParties      = [];
  let filtered        = [];
  let currentPage     = 1;

  /* ── Keyboard nav state ── */
  let suggestionItems = [];   // live NodeList cache
  let activeIdx       = -1;   // -1 = none highlighted

  /* ══════════════════════════════════
     FETCH ALL PARTIES
  ══════════════════════════════════ */
  function loadParties() {
    $.ajax({
      url: PARTIES_URL,
      method: "GET",
      dataType: "json",

      success: function (data) {
        allParties = data.map(function (p, i) {
          return {
            name: p.party_name,
            type: p.party_type,
            idx:  i
          };
        });

        filtered = [...allParties];

        renderStats();
        renderTable();

        $("#tableLoading").hide();

        if (allParties.length === 0) {
          $("#emptyState").show();
        } else {
          $("#tableContainer").show();
        }
      },

      error: function (xhr) {
        console.error(xhr.responseText);
        $("#tableLoading").html(
          '<p style="color:#f87171;">Failed to load parties.</p>'
        );
      }
    });
  }

  /* ══════════════════════════════════
     STATS
  ══════════════════════════════════ */
  function renderStats() {
    const total        = allParties.length;
    const bothCount    = allParties.filter(p => p.type === "Both").length;
    const expenseCount = allParties.filter(p => p.type === "Expense").length;

    $("#statTotal").text(total);
    $("#statBoth").text(bothCount);
    $("#statExpense").text(expenseCount);
  }

  /* ══════════════════════════════════
     TABLE RENDER
  ══════════════════════════════════ */
  function renderTable() {
    const start = (currentPage - 1) * PAGE_SIZE;
    const page  = filtered.slice(start, start + PAGE_SIZE);
    const $body = $("#partiesTableBody").empty();

    if (page.length === 0) {
      $body.append(`
        <tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">
          No parties match your search.
        </td></tr>
      `);
    } else {
      page.forEach(function (p) {
        const initials = p.name.slice(0, 2).toUpperCase();
        const row = `
          <tr>
            <td>
              <span class="td-avatar ${p.type.toLowerCase()}">${initials}</span>
              <span class="td-name">${p.name}</span>
            </td>
            <td>
              <span class="td-badge ${p.type.toLowerCase()}">
                ${p.type}
              </span>
            </td>
            <td style="color:var(--text-muted);font-size:13px;">—</td>
            <td class="td-balance debit">—</td>
            <td>
              <div class="td-actions">
                <a class="tbl-btn edit" href="${UPDATE_URL}?search_name=${encodeURIComponent(p.name)}">
                  <i class="fa-solid fa-pen-to-square"></i> Edit
                </a>
              </div>
            </td>
          </tr>
        `;
        $body.append(row);
      });
    }

    renderPagination();
  }

  /* ══════════════════════════════════
     PAGINATION
  ══════════════════════════════════ */
  function renderPagination() {
    const total = filtered.length;
    const pages = Math.ceil(total / PAGE_SIZE);
    const start = (currentPage - 1) * PAGE_SIZE + 1;
    const end   = Math.min(currentPage * PAGE_SIZE, total);

    $("#pagInfo").text(
      total === 0 ? 'No results' : `Showing ${start}–${end} of ${total}`
    );

    const $btns = $("#pagBtns").empty();

    // Prev
    $btns.append(
      $('<button class="pag-btn">‹ Prev</button>')
        .prop('disabled', currentPage === 1)
        .css('opacity', currentPage === 1 ? 0.4 : 1)
        .on('click', function () { if (currentPage > 1) { currentPage--; renderTable(); } })
    );

    // Page numbers
    const range = getPageRange(currentPage, pages);
    range.forEach(function (pg) {
      $btns.append(
        $(`<button class="pag-btn ${pg === currentPage ? 'active' : ''}">${pg}</button>`)
          .on('click', function () { currentPage = pg; renderTable(); })
      );
    });

    // Next
    $btns.append(
      $('<button class="pag-btn">Next ›</button>')
        .prop('disabled', currentPage >= pages)
        .css('opacity', currentPage >= pages ? 0.4 : 1)
        .on('click', function () { if (currentPage < pages) { currentPage++; renderTable(); } })
    );
  }

  function getPageRange(cur, total) {
    const delta = 2;
    const range = [];
    for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) {
      range.push(i);
    }
    return range;
  }

  /* ══════════════════════════════════
     HELPERS — keyboard highlight
  ══════════════════════════════════ */
  function setActiveItem(idx) {
    // Refresh live list
    suggestionItems = $("#hubSuggestions .suggestion-item").toArray();

    // Clear previous
    suggestionItems.forEach(el => el.classList.remove("suggestion-item--active"));

    activeIdx = idx;

    if (activeIdx >= 0 && activeIdx < suggestionItems.length) {
      const el = suggestionItems[activeIdx];
      el.classList.add("suggestion-item--active");
      // Scroll into view inside dropdown
      el.scrollIntoView({ block: "nearest" });
    }
  }

  function closeSuggestions() {
    $hubSugg.hide().empty();
    activeIdx = -1;
    suggestionItems = [];
  }

  /* ══════════════════════════════════
     SEARCH / FILTER + AUTOCOMPLETE
  ══════════════════════════════════ */
  const $hubInput = $("#hubSearchInput");
  const $hubSugg  = $("#hubSuggestions");

  // Debounce timer
  let acTimer = null;

  $hubInput.on("input", function () {
    const q = $(this).val().trim().toUpperCase();
    activeIdx = -1;   // reset keyboard selection on new input

    // Filter table
    if (q.length > 0) {
      filtered = allParties.filter(p => p.name.toUpperCase().includes(q));
    } else {
      filtered = [...allParties];
    }
    currentPage = 1;
    renderTable();

    // Autocomplete dropdown
    if (q.length < 1) { closeSuggestions(); return; }

    clearTimeout(acTimer);
    acTimer = setTimeout(function () {
      $.ajax({
        url: AUTOCOMPLETE_URL,
        data: { term: q },
        dataType: 'json',
        success: function (data) {
          $hubSugg.empty();
          activeIdx = -1;

          if (data.length) {
            data.slice(0, 6).forEach(function (name) {
              const $item = $(`
                <div class="suggestion-item" tabindex="-1" role="option">
                  <div class="si-icon"><i class="fa-solid fa-user"></i></div>
                  <span class="si-name">${name}</span>
                  <span class="si-hint">Edit →</span>
                </div>
              `).on('click', function () {
                window.location.href = UPDATE_URL + '?search_name=' + encodeURIComponent(name);
              });
              $hubSugg.append($item);
            });

            // Refresh cache after building
            suggestionItems = $hubSugg.find(".suggestion-item").toArray();
            $hubSugg.show();
          } else {
            closeSuggestions();
          }
        }
      });
    }, 160);   // 160 ms debounce
  });

  /* ── Keyboard navigation ── */
  $hubInput.on("keydown", function (e) {
    const isOpen = $hubSugg.is(":visible");

    switch (e.key) {

      // ── Arrow Down ──
      case "ArrowDown":
        e.preventDefault();
        if (!isOpen) return;
        suggestionItems = $hubSugg.find(".suggestion-item").toArray();
        setActiveItem(Math.min(activeIdx + 1, suggestionItems.length - 1));
        break;

      // ── Arrow Up ──
      case "ArrowUp":
        e.preventDefault();
        if (!isOpen) return;
        setActiveItem(Math.max(activeIdx - 1, 0));
        break;

      // ── Enter — navigate to highlighted item ──
      case "Enter":
        if (isOpen && activeIdx >= 0 && suggestionItems[activeIdx]) {
          e.preventDefault();
          suggestionItems[activeIdx].click();
        }
        break;

      // ── Tab — confirm highlighted item or close ──
      case "Tab":
        if (isOpen && activeIdx >= 0 && suggestionItems[activeIdx]) {
          e.preventDefault();
          // Fill input with the selected name
          const selectedName = $(suggestionItems[activeIdx]).find(".si-name").text();
          $hubInput.val(selectedName);
          // Re-filter table with full name
          filtered = allParties.filter(p =>
            p.name.toUpperCase().includes(selectedName.toUpperCase())
          );
          currentPage = 1;
          renderTable();
          closeSuggestions();
        } else {
          closeSuggestions();
        }
        break;

      // ── Escape — close dropdown ──
      case "Escape":
        closeSuggestions();
        $hubInput.blur();
        break;
    }
  });

  /* ── Click outside closes dropdown ── */
  $(document).on('click', function (e) {
    if (!$(e.target).closest('#hubSearchInput, #hubSuggestions').length) {
      closeSuggestions();
    }
  });

  /* ══════════════════════════════════
     INIT
  ══════════════════════════════════ */
  loadParties();

});