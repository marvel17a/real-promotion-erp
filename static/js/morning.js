document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"),
        dateInput: getEl("date"),
        timestampInput: getEl("timestampInput"),
        clockDisplay: getEl("liveClock"),
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
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    let productOptionsHtml = '<option value="">-- Select --</option>';
    if (Array.isArray(productsData)) {
        productsData.forEach(p => {
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}">${p.name}</option>`;
        });
    }

    // --- 1. DIGITAL CLOCK ---
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        if(ui.clockDisplay) ui.clockDisplay.textContent = timeString;
        
        // Format for DB (YYYY-MM-DD HH:MM:SS)
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        if(ui.timestampInput) ui.timestampInput.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- 2. FETCH DATA ---
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        ui.fetchMsg.innerHTML = '<span class="text-primary"><i class="fas fa-spinner fa-spin"></i> Checking...</span>';
        if(ui.historyList) ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = '';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                isRestockMode = false;
                ui.fetchMsg.innerHTML = '<span class="text-secondary small">Start New Allocation</span>';
                createRow(); 
            } else {
                isRestockMode = (data.mode === 'restock');
                
                // 1. Auto-Fill Yesterday's Remaining (Only in Normal Mode)
                if (!isRestockMode && data.opening_stock && data.opening_stock.length > 0) {
                    data.opening_stock.forEach(stockItem => {
                        createRow(stockItem); 
                    });
                    ui.fetchMsg.innerHTML = '<span class="text-success small"><i class="fa-solid fa-check"></i> Stock Loaded</span>';
                } else {
                    createRow();
                    ui.fetchMsg.innerHTML = isRestockMode ? '' : '<span class="text-secondary small">No pending stock</span>';
                }

                // 2. Restock Mode History
                if (isRestockMode) {
                    ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark">Restock Mode</span>';
                    
                    if(data.existing_items && data.existing_items.length > 0) {
                        let historyHtml = `
                            <div class="card border-warning mb-3 shadow-sm">
                                <div class="card-header bg-warning bg-opacity-10 text-warning fw-bold small d-flex justify-content-between">
                                    <span><i class="fa-solid fa-box-open"></i> CURRENT STOCK WITH EMPLOYEE</span>
                                </div>
                                <div class="card-body p-3 d-flex flex-wrap gap-3">
                        `;
                        
                        data.existing_items.forEach(item => {
                            historyHtml += `
                                <div class="d-flex align-items-center border rounded p-2 pe-3 bg-white shadow-sm" style="min-width: 180px;">
                                    <div class="img-box-small me-3" style="width:40px !important; height:40px !important; min-width:35px !important;">
                                        <img src="${item.image}" style="width:100%; height:100%; object-fit:cover;">
                                    </div>
                                    <div>
                                        <div class="fw-bold small text-dark lh-1">${item.name}</div>
                                        <span class="badge bg-primary rounded-pill mt-1">Total: ${item.qty}</span>
                                    </div>
                                </div>
                            `;
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

    // --- 3. ROW CREATION ---
    function createRow(prefillData = null) {
        const tr = document.createElement("tr");
        
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

        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold small py-3"></td>
            <td class="text-center" style="vertical-align: middle;">
                <div class="img-box-small">
                    <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
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
        if(productId) tr.querySelector('.product-dropdown').value = productId;
        
        updateRowIndexes();
        if(prefillData) recalculateRow(tr);
    }

    // --- 4. CALCULATIONS & EVENTS ---
    function updateRowData(row, productId) {
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        
        const product = productsMap.get(productId);
        if (product) {
            priceInput.value = parseFloat(product.price).toFixed(2);
            if(product.image) {
                img.src = product.image;
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
});
