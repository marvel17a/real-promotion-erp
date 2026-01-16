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
    let productOptionsHtml = '<option value="">-- Select --</option>';
    
    const productsMap = new Map();
    if (Array.isArray(productsData)) {
        productsData.forEach(p => {
            p.stock = (p.stock === null || p.stock === undefined) ? 0 : parseInt(p.stock);
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}" data-stock="${p.stock}">${p.name}</option>`;
        });
    }
    
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    // 1. Digital Clock
    function updateClock() {
        const now = new Date();
        if(ui.clockDisplay) ui.clockDisplay.textContent = now.toLocaleTimeString('en-US', { hour12: true });
        
        const iso = now.getFullYear() + '-' + 
                   String(now.getMonth()+1).padStart(2,'0') + '-' + 
                   String(now.getDate()).padStart(2,'0') + ' ' + 
                   String(now.getHours()).padStart(2,'0') + ':' + 
                   String(now.getMinutes()).padStart(2,'0') + ':' + 
                   String(now.getSeconds()).padStart(2,'0');
        
        if(ui.timestampInput) ui.timestampInput.value = iso;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Fetch Data
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;

        if (!empId || !dateVal) return;

        ui.fetchMsg.innerHTML = '<span class="text-primary fw-bold"><i class="fas fa-spinner fa-spin"></i> Checking stock...</span>';
        if(ui.historyList) ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = '';

        const saveBtn = document.querySelector('.btn-save');
        if(ui.addRowBtn) ui.addRowBtn.style.display = 'none';
        if(saveBtn) saveBtn.style.display = 'none';

        try {
            const formData = new FormData();
            formData.append("employee_id", empId);
            formData.append("date", dateVal);

            const response = await fetch("/api/fetch_stock", { method: "POST", body: formData });
            const data = await response.json();

            // Check Lock
            if (data.evening_settled) {
                ui.fetchMsg.innerHTML = '<div class="alert alert-warning py-2 shadow-sm"><i class="fa-solid fa-lock me-2"></i>Evening Settlement Complete.</div>';
                return;
            }

            // Unlock
            if(ui.addRowBtn) ui.addRowBtn.style.display = 'block';
            if(saveBtn) saveBtn.style.display = 'block';

            if (data.error) {
                ui.fetchMsg.innerHTML = `<span class="text-danger small">${data.error}</span>`;
                createRow(); return;
            }

            isRestockMode = (data.mode === 'restock');

            // --- RESTOCK MODE DISPLAY ---
            if (isRestockMode) {
                ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark mb-2">Restock Mode (Inventory Loaded)</span>';
                if(ui.historyList) ui.historyList.innerHTML = ''; 
            } else {
                ui.fetchMsg.innerHTML = '<span class="text-success small fw-bold">Fresh Allocation</span>';
            }

            // --- POPULATE TABLE (With Aggregated Opening) ---
            let rowsAdded = 0;
            if (data.opening_stock && data.opening_stock.length > 0) {
                data.opening_stock.forEach(item => {
                    if (parseInt(item.remaining) > 0) {
                        createRow(item);
                        rowsAdded++;
                    }
                });
            }
            
            // If no rows were added (e.g. all stock sold or fresh day), add one empty row
            if (rowsAdded === 0) {
                createRow();
            }

            recalculateTotals();

        } catch (error) {
            console.error(error);
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Connection Failed</span>';
            if(ui.addRowBtn) ui.addRowBtn.style.display = 'block';
            createRow();
        }
    }

    // 3. Create Row Helper
    function createRow(prefillData = null) {
        const tr = document.createElement("tr");
        let pid = "", open = 0, price = 0, img = DEFAULT_IMG;

        if(prefillData) {
            pid = prefillData.product_id;
            open = prefillData.remaining; 
            price = prefillData.price;
            if(prefillData.image) img = prefillData.image;
        }

        // Dropdown selection logic
        let options = productOptionsHtml;
        if(pid) {
            options = options.replace(`value="${pid}"`, `value="${pid}" selected`);
        }

        tr.innerHTML = `
            <td class="text-center text-muted fw-bold row-index"></td>
            <td class="text-center"><div class="prod-img-box"><img src="${img}" class="product-thumb" onerror="this.src='${DEFAULT_IMG}'"></div></td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>${options}</select>
                <div class="small text-danger fw-bold mt-1 stock-warning" style="display:none;"></div>
            </td>
            <td><input type="number" name="opening[]" class="table-input opening" value="${open}" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="table-input given input-qty" placeholder="0"></td>
            <td><input type="number" name="total[]" class="table-input total" value="${open}" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="table-input price text-end" value="${price.toFixed(2)}" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="table-input amount text-end fw-bold text-primary" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center"><button type="button" class="btn btn-sm text-danger btn-remove-row"><i class="fa-solid fa-trash-can fa-lg"></i></button></td>
        `;
        ui.tableBody.appendChild(tr);
        
        updateRowIndexes();
        if(prefillData) recalculateRow(tr);
    }

    // 4. Calculations
    function updateRowData(row, pid) {
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        const prod = productsMap.get(pid);
        
        if(prod) {
            priceInput.value = parseFloat(prod.price).toFixed(2);
            img.src = prod.image || DEFAULT_IMG;
        } else {
            priceInput.value = "0.00";
            img.src = DEFAULT_IMG;
        }
        recalculateRow(row);
    }

    function recalculateRow(row) {
        const op = parseInt(row.querySelector(".opening").value) || 0;
        const givInput = row.querySelector(".given");
        let giv = parseInt(givInput.value) || 0;
        const pr = parseFloat(row.querySelector(".price").value) || 0;
        const pid = row.querySelector(".product-dropdown").value;
        const warn = row.querySelector(".stock-warning");

        if(pid) {
            const p = productsMap.get(pid);
            const max = p ? p.stock : 9999;
            if(giv > max) {
                warn.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-1"></i>Only ${max} in warehouse`;
                warn.style.display = 'block';
                givInput.style.borderColor = 'red';
            } else { 
                warn.style.display = 'none'; 
                givInput.style.borderColor = '';
            }
        }

        const tot = op + giv;
        row.querySelector(".total").value = tot;
        row.querySelector(".amount").value = (tot * pr).toFixed(2);
        
        recalculateTotals();
    }

    function recalculateTotals() {
        let tOpen = 0, tGiv = 0, tTot = 0, tAmt = 0;
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            if(!row.querySelector(".opening")) return;
            
            tOpen += parseInt(row.querySelector(".opening").value)||0;
            tGiv += parseInt(row.querySelector(".given").value)||0;
            tTot += parseInt(row.querySelector(".total").value)||0;
            tAmt += parseFloat(row.querySelector(".amount").value)||0;
        });
        ui.totals.opening.textContent = tOpen;
        ui.totals.given.textContent = tGiv;
        ui.totals.all.textContent = tTot;
        ui.totals.grand.textContent = tAmt.toFixed(2);
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => tr.querySelector(".row-index").textContent = i + 1);
    }

    // --- EVENTS ---
    ui.addRowBtn.addEventListener("click", (e) => { e.preventDefault(); createRow(); });
    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    
    ui.tableBody.addEventListener("click", e => {
        if(e.target.closest(".btn-remove-row")) {
            // FIX: Warn user that deleting from view doesn't delete physical stock from DB if opening > 0
            const tr = e.target.closest("tr");
            const op = parseInt(tr.querySelector(".opening").value) || 0;
            let confirmMsg = "Remove row?";
            
            if (op > 0) {
                confirmMsg = "Removing this row will reverse the stock deduction for this item upon saving. Continue?";
            }
            
            if(confirm(confirmMsg)) { 
                tr.remove(); 
                updateRowIndexes(); 
                recalculateTotals(); 
            }
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if(e.target.matches(".product-dropdown")) {
            updateRowData(e.target.closest("tr"), e.target.value);
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if(e.target.matches(".given")) {
            recalculateRow(e.target.closest("tr"));
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll("input:not([readonly]), select"));
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) inputs[index + 1].focus();
        }
    });
});



