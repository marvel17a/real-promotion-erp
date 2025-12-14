document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"),
        dateInput: getEl("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        historyList: getEl("historyList"),
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    if (!ui.employeeSelect || !ui.tableBody) return;

    let isRestockMode = false;
    const productsData = window.productsData || [];
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    // Build Dropdown Options
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
        if(ui.historyList) ui.historyList.innerHTML = '';
        
        // Clear existing rows before fetching
        ui.tableBody.innerHTML = '';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                isRestockMode = false;
                ui.fetchMsg.innerHTML = '<span class="text-secondary small">Start New Allocation</span>';
                createRow(); // Start with one empty row
            } else {
                isRestockMode = (data.mode === 'restock');
                
                // 1. Handle "Yesterday's Remaining" (Auto-Fill)
                if (data.opening_stock && data.opening_stock.length > 0) {
                    data.opening_stock.forEach(stockItem => {
                        createRow(stockItem); // Create row pre-filled with this stock
                    });
                    ui.fetchMsg.innerHTML = '<span class="text-success small"><i class="fa-solid fa-check"></i> Remaining stock loaded</span>';
                } else {
                    // No previous stock found, just empty row
                    createRow();
                    ui.fetchMsg.innerHTML = '<span class="text-secondary small">No pending stock</span>';
                }

                // 2. Handle "Restock Mode" (Show history)
                if (isRestockMode) {
                    ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark">Restock Mode</span>';
                    if(data.existing_items && data.existing_items.length > 0) {
                        let historyHtml = '<div class="alert alert-light border mt-3"><small class="fw-bold text-muted">ALREADY GIVEN TODAY:</small><div class="d-flex flex-wrap gap-2 mt-2">';
                        data.existing_items.forEach(item => {
                            historyHtml += `<span class="badge bg-secondary p-2 d-flex align-items-center gap-2"><img src="${item.image}" style="width:20px;height:20px;border-radius:50%"> ${item.name}: ${item.qty}</span>`;
                        });
                        historyHtml += '</div></div>';
                        if(ui.historyList) ui.historyList.innerHTML = historyHtml;
                    }
                }
            }
            recalculateTotals();

        } catch (error) {
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Error</span>';
            createRow();
        }
    }

    // Pass 'prefillData' to auto-populate row
    function createRow(prefillData = null) {
        const tr = document.createElement("tr");
        
        // Initial values
        let productId = "";
        let openingVal = 0;
        let priceVal = 0.00;
        let imgSrc = DEFAULT_IMG;

        if (prefillData) {
            productId = prefillData.product_id;
            openingVal = prefillData.remaining;
            priceVal = prefillData.price;
            if(prefillData.image) imgSrc = prefillData.image;
        }

        // Build HTML with pre-selected values
        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold small py-3"></td>
            <td class="text-center">
                <div class="img-box">
                    <img src="${imgSrc}" class="product-thumb" alt="Product" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="${priceVal.toFixed(2)}" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        `;
        
        ui.tableBody.appendChild(tr);
        
        // Set dropdown value if prefilled
        if(productId) {
            tr.querySelector('.product-dropdown').value = productId;
        }
        
        updateRowIndexes();
        // Recalculate immediately for auto-filled rows
        if(prefillData) recalculateRow(tr);
    }

    function updateRowData(row, productId) {
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        
        const product = productsMap.get(productId);
        if (product) {
            priceInput.value = parseFloat(product.price).toFixed(2);
            if(product.image) {
                img.src = product.image;
                img.onerror = () => { img.src = DEFAULT_IMG; };
            } else {
                img.src = DEFAULT_IMG;
            }
        } else {
            img.src = DEFAULT_IMG;
            priceInput.value = "0.00";
        }
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
        
        recalculateTotals();
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

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }

    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault();
        createRow();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if(confirm("Remove row?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            updateRowData(e.target.closest("tr"), e.target.value);
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            recalculateRow(e.target.closest("tr"));
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
