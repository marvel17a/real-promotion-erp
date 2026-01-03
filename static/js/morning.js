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
            p.stock = (p.stock === null || p.stock === undefined) ? 0 : parseInt(p.stock);
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}" data-stock="${p.stock}">${p.name}</option>`;
        });
    }

    // --- 1. DIGITAL CLOCK ---
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        if(ui.clockDisplay) ui.clockDisplay.textContent = timeString;
        
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
    // --- 2. FETCH DATA FUNCTION ---
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;

        // 1. Check if Evening Settlement is already done (Hide Buttons)
        const completedEmps = window.completedEmployees || [];
        const isEveningDone = completedEmps.includes(parseInt(empId));

        if (isEveningDone) {
            ui.addRowBtn.style.display = 'none';
            document.querySelector('.btn-save').style.display = 'none';
            ui.fetchMsg.innerHTML = '<div class="alert alert-warning py-1"><i class="fa-solid fa-lock me-2"></i>Evening Settlement Done. View Only.</div>';
            // Stop further fetching if locked (optional, but safer)
            return; 
        } else {
            ui.addRowBtn.style.display = 'block';
            document.querySelector('.btn-save').style.display = 'block';
            ui.fetchMsg.innerHTML = '';
        }

        if (!empId || !dateVal) return;

        // UI Reset
        ui.fetchMsg.innerHTML = '<span class="text-primary fw-bold"><i class="fas fa-spinner fa-spin"></i> Checking stock...</span>';
        if(ui.historyList) ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = ''; // Clear table

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${empId}&date=${dateVal}`);
            const data = await response.json();

            // Handle Errors
            if (data.error) {
                ui.fetchMsg.innerHTML = `<span class="text-danger small">${data.error}</span>`;
                createRow(); // Add empty row fallback
                return;
            }

            isRestockMode = (data.mode === 'restock');

            // --- SCENARIO A: RESTOCK MODE ---
            if (isRestockMode) {
                ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark mb-2">Restock Mode Active</span>';
                
                // Show Allocated Products in History Section
                if(data.existing_items && data.existing_items.length > 0) {
                    let historyHtml = `
                        <div class="card border-warning mb-3 shadow-sm">
                            <div class="card-header bg-warning bg-opacity-10 text-dark fw-bold small">
                                <i class="fa-solid fa-box-open me-1"></i> ALREADY ALLOCATED TODAY
                            </div>
                            <div class="card-body p-2 d-flex flex-wrap gap-2">
                    `;
                    
                    data.existing_items.forEach(item => {
                        historyHtml += `
                            <div class="d-flex align-items-center border rounded p-1 pe-3 bg-white" style="min-width: 160px;">
                                <img src="${item.image}" class="rounded me-2" width="40" height="40" style="object-fit:cover;">
                                <div>
                                    <div class="fw-bold small text-dark lh-1">${item.name}</div>
                                    <div class="badge bg-primary mt-1">Qty: ${item.qty}</div>
                                </div>
                            </div>
                        `;
                    });
                    
                    historyHtml += '</div></div>';
                    ui.historyList.innerHTML = historyHtml;
                }
                
                // Add one empty row for new products
                createRow();
            } 
            
            // --- SCENARIO B: NORMAL MODE (OPENING STOCK) ---
            else {
                ui.fetchMsg.innerHTML = '<span class="text-success small fw-bold"><i class="fa-solid fa-check"></i> Ready for Allocation</span>';
                
                if (data.opening_stock && data.opening_stock.length > 0) {
                    // Pre-fill table with Yesterday's Remaining
                    data.opening_stock.forEach(item => {
                        // item contains: product_id, name, remaining, price, image
                        createRow(item); 
                    });
                } else {
                    // No history, fresh start
                    createRow();
                }
            }
            
            recalculateTotals();

        } catch (error) {
            console.error(error);
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Connection Failed</span>';
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
            <td class="text-center text-muted fw-bold row-index"></td>
            <td class="text-center">
                <div class="prod-img-box">
                    <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${productOptionsHtml}
                </select>
                <div class="small text-danger fw-bold mt-1 stock-warning" style="display:none; font-size: 0.75rem;"></div>
            </td>
            <td><input type="number" name="opening[]" class="table-input opening" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="table-input given input-qty" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="table-input total" value="${openingVal}" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="table-input price text-end" step="0.01" value="${priceVal.toFixed(2)}" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="table-input amount text-end fw-bold text-primary" value="0.00" readonly tabindex="-1"></td>
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
        const warningEl = row.querySelector(".stock-warning");

        warningEl.style.display = 'none';

        const product = productsMap.get(productId);
        if (product) {
            priceInput.value = parseFloat(product.price).toFixed(2);
            img.src = product.image || DEFAULT_IMG;
            recalculateRow(row);
        } else {
            img.src = DEFAULT_IMG;
            priceInput.value = "0.00";
        }
    }

    function recalculateRow(row) {
        const opening = parseInt(row.querySelector(".opening").value) || 0;
        const givenInput = row.querySelector(".given");
        let given = parseInt(givenInput.value) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;

        const dropdown = row.querySelector(".product-dropdown");
        const productId = dropdown.value;
        const warningEl = row.querySelector(".stock-warning");

        if (productId) {
            const product = productsMap.get(productId);
            const maxAvailable = product ? parseInt(product.stock) : 999999;

            if (given > maxAvailable) {
                given = maxAvailable;
                givenInput.value = maxAvailable;
                warningEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-1"></i>Only ${maxAvailable} left!`;
                warningEl.style.display = 'block';
                givenInput.style.borderColor = 'red';
            } else {
                warningEl.style.display = 'none';
                givenInput.style.borderColor = '';
            }
        }

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

