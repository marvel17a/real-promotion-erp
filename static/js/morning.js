document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);

    const ui = {
        employeeSelect: getEl("employee_id"),
        dateInput: getEl("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    // Guard: required DOM not present
    if (!ui.employeeSelect || !ui.tableBody) return;

    let currentStockData = {};
    let isRestockMode = false;

    const productsData = Array.isArray(window.productsData) ? window.productsData : [];
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    let productOptionsHtml = '<option value="">-- Select --</option>';
    productsData.forEach(p => {
        const id = String(p.id);
        productsMap.set(id, p);
        productOptionsHtml += `<option value="${id}">${p.name}</option>`;
    });

    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        ui.fetchMsg.innerHTML =
            '<span class="text-primary"><i class="fas fa-spinner fa-spin"></i> Checking...</span>';

        try {
            const response = await fetch(
                `/api/fetch_stock?employee_id=${encodeURIComponent(employeeId)}&date=${encodeURIComponent(dateStr)}`
            );
            const data = await response.json();

            if (data.error && response.status !== 500) {
                currentStockData = {};
                isRestockMode = false;
                ui.fetchMsg.innerHTML =
                    '<span class="text-secondary small">Start New Allocation</span>';
            } else {
                currentStockData = data.stock || {};
                isRestockMode = data.mode === "restock";

                if (isRestockMode) {
                    ui.fetchMsg.innerHTML =
                        '<span class="text-warning fw-bold small"><i class="fa-solid fa-plus-circle"></i> Restock Mode: Adding to existing list</span>';
                } else {
                    ui.fetchMsg.innerHTML =
                        '<span class="text-success small"><i class="fa-solid fa-check"></i> Stock Synced</span>';
                }
            }

            updateAllRows();
        } catch (error) {
            console.error("fetchStockData error:", error);
            ui.fetchMsg.innerHTML =
                '<span class="text-danger small">Error</span>';
        }
    }

    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold small py-3"></td>
            <td class="text-center">
                <div class="img-box">
                    <img src="${DEFAULT_IMG}" class="product-thumb" alt="Product"
                         style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateRowData(row, productId) {
        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");

        const product = productsMap.get(String(productId));

        if (product && product.image) {
            const src = product.image.startsWith("http")
                ? product.image
                : `/static/uploads/${product.image}`;
            img.src = src;
            img.onerror = () => {
                img.src = DEFAULT_IMG;
            };
        } else {
            img.src = DEFAULT_IMG;
        }

        // Opening logic
        let openingQty = 0;
        if (!isRestockMode && currentStockData[productId]) {
            openingQty = parseInt(currentStockData[productId].remaining) || 0;
        }
        openingInput.value = openingQty;

        // Price logic
        let price = 0;
        if (currentStockData[productId]) {
            price = parseFloat(currentStockData[productId].price) || 0;
        } else if (product && product.price != null) {
            price = parseFloat(product.price) || 0;
        }
        priceInput.value = price.toFixed(2);

        recalculateRow(row);
    }

    function recalculateRow(row) {
        const opening = parseInt(row.querySelector(".opening").value) || 0;
        const given = parseInt(row.querySelector(".given").value) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;

        const total = opening + given;
        const amount = total * price;

        row.querySelector(".total").value = total;
        row.querySelector(".amount").value = amount.toFixed(2);
    }

    function recalculateTotals() {
        let tOpening = 0;
        let tGiven = 0;
        let tAll = 0;
        let tGrand = 0;

        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const openingEl = row.querySelector(".opening");
            if (!openingEl) return;

            tOpening += parseInt(openingEl.value) || 0;
            tGiven += parseInt(row.querySelector(".given").value) || 0;
            tAll += parseInt(row.querySelector(".total").value) || 0;
            tGrand += parseFloat(row.querySelector(".amount").value) || 0;
        });

        ui.totals.opening.textContent = tOpening;
        ui.totals.given.textContent = tGiven;
        ui.totals.all.textContent = tAll;
        ui.totals.grand.textContent = tGrand.toFixed(2);
    }

    function updateAllRows() {
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const select = row.querySelector(".product-dropdown");
            if (select && select.value) {
                updateRowData(row, select.value);
            }
        });
        recalculateTotals();
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            const indexCell = tr.querySelector(".row-index");
            if (indexCell) indexCell.textContent = i + 1;
        });
    }

    // Events
    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault();
        createRow();
        recalculateTotals();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        const btn = e.target.closest(".btn-remove-row");
        if (!btn) return;

        if (confirm("Remove this row?")) {
            btn.closest("tr").remove();
            updateRowIndexes();
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            const row = e.target.closest("tr");
            updateRowData(row, e.target.value);
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            const row = e.target.closest("tr");
            recalculateRow(row);
            recalculateTotals();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
            const inputs = Array.from(
                document.querySelectorAll("input:not([readonly]), select")
            );
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        }
    });

    // Initial fetch
    fetchStockData();
});
