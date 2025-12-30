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

    let productOptionsHtml = '<option value="">-- Select Product --</option>';
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
        if(ui.clockDisplay) ui.clockDisplay.innerHTML = `<i class="fa-regular fa-clock me-2 text-warning"></i> ${timeString}`;
        
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

        ui.fetchMsg.innerHTML = '<span class="text-primary fw-bold"><i class="fas fa-spinner fa-spin me-2"></i> Checking database...</span>';
        if(ui.historyList) ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = '';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                isRestockMode = false;
                ui.fetchMsg.innerHTML = '<div class="alert alert-light border shadow-sm"><i class="fa-solid fa-plus-circle text-primary me-2"></i>Start New Allocation</div>';
                createRow(); 
            } else {
                isRestockMode = (data.mode === 'restock');
                
                // 1. Auto-Fill Yesterday's Remaining (Only in Normal Mode)
                if (!isRestockMode && data.opening_stock && data.opening_stock.length > 0) {
                    data.opening_stock.forEach(stockItem => {
                        createRow(stockItem); 
                    });
                    ui.fetchMsg.innerHTML = '<div class="alert alert-success border-0 shadow-sm py-2"><i class="fa-solid fa-check-circle me-2"></i> Previous Closing Stock Loaded</div>';
                } else {
                    createRow();
                    ui.fetchMsg.innerHTML = isRestockMode ? '' : '<div class="alert alert-secondary border-0 py-2">No pending stock from yesterday.</div>';
                }

                // 2. Restock Mode History
                if (isRestockMode) {
                    ui.fetchMsg.innerHTML = '<div class="alert alert-warning border-warning fw-bold shadow-sm"><i class="fa-solid fa-triangle-exclamation me-2"></i>RESTOCK MODE: Employee already has stock today. Adding more.</div>';
                    
                    if(data.existing_items && data.existing_items.length > 0) {
                        let historyHtml = `
                            <div class="restock-card">
                                <h6 class="fw-bold text-dark mb-3"><i class="fa-solid fa-box-open me-2"></i>CURRENT STOCK ON HAND:</h6>
                                <div class="d-flex flex-wrap">
                        `;
                        
                        data.existing_items.forEach(item => {
                            historyHtml += `
                                <div class="restock-item">
                                    <img src="${item.image}" alt="img">
                                    <div class="lh-1">
                                        <div class="small fw-bold text-dark">${item.name}</div>
                                        <div class="badge bg-primary rounded-pill mt-1">Qty: ${item.qty}</div>
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
            ui.fetchMsg.innerHTML = '<span class="text-danger fw-bold">Connection Error</span>';
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
            <td class="row-index text-center text-muted fw-bold"></td>
            <td class="text-center">
                <div class="prod-img-box">
                    <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select table-input product-dropdown" required>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="table-input opening text-muted bg-light" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="table-input given input-given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="table-input total fw-bold text-dark bg-light" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="table-input price text-end bg-light" step="0.01" value="${priceVal.toFixed(2)}" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="table-input amount text-end fw-bold text-primary bg-light" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-sm text-danger btn-remove-row"><i class="fa-solid fa-trash-can fa-lg"></i></button>
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
