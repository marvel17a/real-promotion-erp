document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"),
        dateInput: getEl("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        historyList: getEl("historyList"), // New element for restock history
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    if (!ui.employeeSelect || !ui.tableBody) return;

    let currentStockData = {};
    let isRestockMode = false;
    const productsData = window.productsData || [];
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    // Build Dropdown
    let productOptionsHtml = '<option value="">-- Select --</option>';
    if (Array.isArray(productsData)) {
        productsData.forEach(p => {
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}">${p.name}</option>`;
        });
    }

    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        ui.fetchMsg.innerHTML = '<span class="text-primary"><i class="fas fa-spinner fa-spin"></i> Checking...</span>';
        if(ui.historyList) ui.historyList.innerHTML = ''; // Clear history

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                // Error case
                currentStockData = {};
                isRestockMode = false;
                ui.fetchMsg.innerHTML = '';
            } else {
                currentStockData = data.stock || {};
                isRestockMode = (data.mode === 'restock');
                
                if (isRestockMode) {
                    ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark"><i class="fa-solid fa-rotate"></i> Restock Mode: Allocation exists for today.</span>';
                    // Show what was already given
                    if(data.existing_items && data.existing_items.length > 0) {
                        let historyHtml = '<div class="alert alert-light border mt-3"><small class="fw-bold text-muted">ALREADY ALLOCATED TODAY:</small><ul class="list-group list-group-flush mt-2">';
                        data.existing_items.forEach(item => {
                            historyHtml += `<li class="list-group-item d-flex justify-content-between align-items-center bg-transparent">
                                <div><img src="${item.image}" style="width:30px; height:30px; border-radius:4px; margin-right:10px;"> ${item.name}</div>
                                <span class="badge bg-secondary rounded-pill">${item.qty}</span>
                            </li>`;
                        });
                        historyHtml += '</ul></div>';
                        if(ui.historyList) ui.historyList.innerHTML = historyHtml;
                    }
                } else {
                    ui.fetchMsg.innerHTML = '<span class="badge bg-success"><i class="fa-solid fa-check"></i> Stock Synced</span>';
                }
            }
            // Clear current input rows to avoid confusion, or keep them? 
            // Better to keep user input if they typed something. 
            // But we must update "Opening" col based on mode.
            updateAllRows();

        } catch (error) {
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Connection Error</span>';
        }
    }

    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold small py-3"></td>
            <td class="text-center">
                <div class="img-box">
                    <img src="${DEFAULT_IMG}" class="product-thumb" alt="Product" style="width: 100%; height: 100%; object-fit: cover;">
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
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateRowData(row, productId) {
        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        
        const product = productsMap.get(productId);
        if (product && product.image) {
            img.src = product.image;
            img.onerror = () => { img.src = DEFAULT_IMG; };
        } else {
            img.src = DEFAULT_IMG;
        }

        // Logic: 
        // 1. If Restock Mode (Mid-day): Opening is 0 (we are just adding *more*)
        // 2. If Normal Mode (Morning): Opening is Yesterday's Remaining
        let openingQty = 0;
        if (!isRestockMode && currentStockData[productId]) {
            openingQty = parseInt(currentStockData[productId].remaining) || 0;
        }
        openingInput.value = openingQty;

        let price = 0;
        if (currentStockData[productId]) {
            price = parseFloat(currentStockData[productId].price);
        } else if (product) {
            price = parseFloat(product.price);
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
        let tOpening = 0, tGiven = 0, tAll = 0, tGrand = 0;
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            if(!row.querySelector(".opening")) return;
            tOpening += parseInt(row.querySelector(".opening").value) || 0;
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
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }

    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault();
        createRow();
        recalculateTotals();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if(confirm("Remove this row?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            updateRowData(e.target.closest("tr"), e.target.value);
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            recalculateRow(e.target.closest("tr"));
            recalculateTotals();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll("input:not([readonly]), select"));
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        }
    });

    fetchStockData();
});
