(function () {
  function initNewArrivalsReorder() {
    const table = document.getElementById("result_list");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    let initialOrder = [];
    let statusToast = null;
    let isDragging = false;
    let draggedRow = null;
    let activePointerId = null;
    let capturedElement = null;

    // Helper: Extract Product ID from row
    function getRowProductId(row) {
      if (!row) return null;
      if (row.dataset && row.dataset.productId) return row.dataset.productId;

      // 1. Check for action select checkbox
      const checkbox = row.querySelector("input.action-select");
      if (checkbox && checkbox.value) {
        return checkbox.value;
      }
      // 2. Check for ID table cell
      const idCell = row.querySelector("td.field-id, th.field-id");
      if (idCell && idCell.textContent.trim()) {
        return idCell.textContent.trim();
      }
      // 3. Fallback: Parse from change URL
      const link = row.querySelector('th a, td a[href*="/change/"]');
      if (link) {
        const href = link.getAttribute("href") || "";
        const match = href.match(/\/([^\/]+)\/change\//);
        if (match && match[1]) {
          return decodeURIComponent(match[1]);
        }
        return link.textContent.trim();
      }
      return null;
    }

    // Helper: Capture current row ID sequence
    function getOrderArray() {
      const rows = tbody.querySelectorAll("tr");
      const order = [];
      rows.forEach(function (r) {
        const pid = getRowProductId(r);
        if (pid) order.push(pid);
      });
      return order;
    }

    // Helper: Setup row IDs and drag handles
    function setupRows() {
      const rows = tbody.querySelectorAll("tr");
      rows.forEach(function (r, idx) {
        const pid = getRowProductId(r);
        if (pid) r.dataset.productId = pid;

        const orderCell = r.querySelector("td.field-new_arrival_order, th.field-new_arrival_order, td:first-child, th:first-child");
        if (orderCell && !orderCell.querySelector(".drag-handle-grip")) {
          const grip = document.createElement("span");
          grip.className = "drag-handle-grip";
          grip.title = "Drag to reorder New Arrivals";
          grip.innerHTML = "⠿";
          orderCell.prepend(grip);
        }
      });
    }

    // Helper: Refresh visible order numbers in table
    function updateVisibleOrderNumbers() {
      const rows = tbody.querySelectorAll("tr");
      rows.forEach(function (r, idx) {
        const orderCell = r.querySelector("td.field-new_arrival_order, th.field-new_arrival_order");
        if (orderCell) {
          const grip = orderCell.querySelector(".drag-handle-grip");
          orderCell.innerHTML = "";
          if (grip) {
            orderCell.appendChild(grip);
          } else {
            const newGrip = document.createElement("span");
            newGrip.className = "drag-handle-grip";
            newGrip.title = "Drag to reorder New Arrivals";
            newGrip.innerHTML = "⠿";
            orderCell.appendChild(newGrip);
          }
          const badge = document.createElement("span");
          badge.className = "order-number-badge";
          badge.textContent = "#" + (idx + 1);
          orderCell.appendChild(badge);
        }
      });
    }

    setupRows();
    updateVisibleOrderNumbers();
    initialOrder = getOrderArray();

    // Helper: CSRF token extractor
    function getCsrfToken() {
      const cookieValue = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
      if (cookieValue) return cookieValue;
      const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
      return inp ? inp.value : "";
    }

    // Create floating status toast indicator
    function createStatusToast() {
      var old = document.getElementById("reorder-status-toast");
      if (old) old.remove();

      const toast = document.createElement("div");
      toast.id = "reorder-status-toast";
      toast.style.cssText = `
        display: none;
        position: fixed;
        top: 80px;
        right: 28px;
        z-index: 999999;
        padding: 10px 18px;
        background: #1e293b;
        color: #ffffff;
        font-weight: 700;
        font-size: 13px;
        border-radius: 10px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.1);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        align-items: center;
        gap: 8px;
      `;
      document.body.appendChild(toast);
      return toast;
    }

    statusToast = createStatusToast();

    function showToast(text, bg, autoHideMs) {
      if (!statusToast) statusToast = createStatusToast();
      statusToast.innerHTML = text;
      statusToast.style.background = bg || "#1e293b";
      statusToast.style.display = "flex";
      statusToast.style.opacity = "1";
      statusToast.style.transform = "translateY(0)";

      if (autoHideMs) {
        setTimeout(function () {
          statusToast.style.opacity = "0";
          statusToast.style.transform = "translateY(-8px)";
          setTimeout(function () {
            statusToast.style.display = "none";
          }, 300);
        }, autoHideMs);
      }
    }

    // Auto-Save Order Function
    function saveOrder() {
      const currentOrder = getOrderArray();
      if (!currentOrder.length) return;

      showToast("⏳ Saving new arrival order...", "#3b82f6");

      fetch("/api/products/reorder_new_arrivals/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ product_ids: currentOrder }),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.success) {
            initialOrder = currentOrder;
            updateVisibleOrderNumbers();
            showToast("✅ New arrival order saved!", "#10b981", 2000);
          } else {
            showToast("⚠️ Save failed: " + (data.error || "Unknown error"), "#ef4444", 4000);
          }
        })
        .catch(function (err) {
          console.error("Reorder error:", err);
          showToast("⚠️ Network error while saving order", "#ef4444", 4000);
        });
    }

    // -----------------------------------------------------------------
    // High-Precision Pointer Drag Engine (Universal: Touch, Mobile, Mouse)
    // -----------------------------------------------------------------
    tbody.addEventListener("pointerdown", function (e) {
      const grip = e.target.closest(".drag-handle-grip");
      const row = e.target.closest("tr");
      if (!row || !row.parentNode || row.parentNode !== tbody) return;

      // Don't intercept clicks on inputs, action checkboxes, or action buttons unless on grip
      if (e.target.closest("input, select, button, textarea") && !grip) {
        return;
      }

      draggedRow = row;
      isDragging = false;
      const startY = e.clientY;
      activePointerId = e.pointerId;
      capturedElement = e.target;

      // Try capturing pointer for flawless mobile touch movement
      try {
        if (capturedElement && capturedElement.setPointerCapture) {
          capturedElement.setPointerCapture(activePointerId);
        }
      } catch (err) {}

      function onPointerMove(moveEvent) {
        if (!draggedRow) return;

        const diffY = Math.abs(moveEvent.clientY - startY);
        if (diffY > 3 && !isDragging) {
          isDragging = true;
          draggedRow.classList.add("dragging-row");
          document.body.style.userSelect = "none";
          document.body.style.cursor = "grabbing";
        }

        if (isDragging) {
          if (moveEvent.cancelable) {
            moveEvent.preventDefault();
          }

          const otherRows = Array.from(tbody.querySelectorAll("tr")).filter(function (r) {
            return r !== draggedRow;
          });

          if (otherRows.length === 0) return;

          const clientY = moveEvent.clientY;

          // 1. Check if dragging above first row (Top Position Placement)
          const firstRow = otherRows[0];
          const firstRect = firstRow.getBoundingClientRect();
          if (clientY < firstRect.top + firstRect.height / 2) {
            if (draggedRow !== firstRow) {
              tbody.insertBefore(draggedRow, firstRow);
              updateVisibleOrderNumbers();
            }
            return;
          }

          // 2. Check if dragging below last row (Bottom Position Placement)
          const lastRow = otherRows[otherRows.length - 1];
          const lastRect = lastRow.getBoundingClientRect();
          if (clientY > lastRect.bottom - lastRect.height / 2) {
            if (draggedRow.nextElementSibling !== null || tbody.lastElementChild !== draggedRow) {
              tbody.appendChild(draggedRow);
              updateVisibleOrderNumbers();
            }
            return;
          }

          // 3. Middle rows: find closest row to insert before/after
          for (let i = 0; i < otherRows.length; i++) {
            const targetRow = otherRows[i];
            const rect = targetRow.getBoundingClientRect();
            if (clientY >= rect.top && clientY <= rect.bottom) {
              if (clientY < rect.top + rect.height / 2) {
                targetRow.before(draggedRow);
              } else {
                targetRow.after(draggedRow);
              }
              updateVisibleOrderNumbers();
              break;
            }
          }
        }
      }

      function onPointerUp(upEvent) {
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerup", onPointerUp);
        document.removeEventListener("pointercancel", onPointerUp);
        document.body.style.userSelect = "";
        document.body.style.cursor = "";

        try {
          if (capturedElement && capturedElement.releasePointerCapture && activePointerId !== null) {
            capturedElement.releasePointerCapture(activePointerId);
          }
        } catch (err) {}

        if (draggedRow) {
          draggedRow.classList.remove("dragging-row");
          draggedRow = null;
        }

        if (isDragging) {
          isDragging = false;
          const currentOrder = getOrderArray();
          const changed = JSON.stringify(initialOrder) !== JSON.stringify(currentOrder);
          if (changed) {
            updateVisibleOrderNumbers();
            saveOrder();
          }
        }
      }

      document.addEventListener("pointermove", onPointerMove, { passive: false });
      document.addEventListener("pointerup", onPointerUp);
      document.addEventListener("pointercancel", onPointerUp);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNewArrivalsReorder);
  } else {
    initNewArrivalsReorder();
  }
})();
