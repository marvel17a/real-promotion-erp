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
    
    // Product Map for quick access
    const productsMap = new Map();
    if (Array.isArray(productsData)) {
        productsData.forEach(p => {
            p.stock = (p.stock === null || p.stock === undefined) ? 0 : parseInt(p.stock);
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}" data-stock="${p.stock}">${p.name}</option>`;
        });
    }

    // --- LIVE CLOCK ---
    setInterval(() => {
        const now = new Date();
        if(ui.clockDisplay) ui.clockDisplay.textContent = now.toLocaleTimeString();
        if(ui.timestampInput) {
            const pad = n => String(n).padStart(2, '0');
            ui.timestampInput.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
        }
    }, 1000);

    // --- FETCH DATA ---
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;
        if(!empId || !dateVal) return;

        ui.fetchMsg.innerHTML = '<span class="text-info"><i class="fa-solid fa-spinner fa-spin"></i> Checking stock...</span>';
        
        try {
            const formData = new FormData();
            formData.append("employee_id", empId);
            formData.append("date", dateVal);

            const res = await fetch("/api/fetch_stock", { method: "POST", body: formData });
            // Handle HTTP errors
            if (!res.ok) throw new Error(`Server returned ${res.status}`);
            
            const data = await res.json();

            if (data.error) {
                // Show the specific error from backend
                ui.fetchMsg.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> ${data.error}</span>`;
                return;
            }

            if (data.evening_settled) {
                ui.fetchMsg.innerHTML = '<span class="text-danger fw-bold">Evening Settlement Done for this date. Locked.</span>';
                ui.addRowBtn.disabled = true;
                ui.tableBody.innerHTML = "";
                return;
            } else {
                ui.addRowBtn.disabled = false;
            }

            ui.tableBody.innerHTML = "";
            isRestockMode = (data.mode === 'restock');

            if (isRestockMode) {
                ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark"><i class="fa-solid fa-rotate"></i> Restock Mode (Aggregated)</span>';
                
                // Show Allocation History (Existing Items)
                if (data.existing_items && data.existing_items.length > 0) {
                    renderHistory(data.existing_items);
                } else {
                    if(ui.historyList) ui.historyList.innerHTML = '<div class="text-muted small">No items given yet today.</div>';
                }
                
                // Add empty row for new allocation
                createRow(); 

            } else {
                ui.fetchMsg.innerHTML = '<span class="badge bg-success"><i class="fa-solid fa-sun"></i> Fresh Morning Allocation</span>';
                if(ui.historyList) ui.historyList.innerHTML = "";

                // Populate opening stock (Yesterday's Leftover)
                if (data.opening_stock && data.opening_stock.length > 0) {
                    data.opening_stock.forEach(item => createRow(item));
                } else {
                    createRow();
                }
            }
            recalculateTotals();

        } catch (err) {
            console.error(err);
            ui.fetchMsg.innerHTML = `<span class="text-danger">Connection Failed: ${err.message}</span>`;
        }
    }

    function renderHistory(items) {
        if(!ui.historyList) return;
        let html = '<div class="d-flex flex-wrap gap-2">';
        items.forEach(item => {
            html += `
            <div class="border rounded px-2 py-1 bg-light shadow-sm d-flex align-items-center gap-2">
                <img src="${item.image}" width="30" height="30" class="rounded">
                <div>
                    <div class="fw-bold small lh-1">${item.name}</div>
                    <div class="text-primary small fw-bold">Qty: ${item.qty}</div>
                </div>
            </div>`;
        });
        html += '</div>';
        ui.historyList.innerHTML = html;
    }

    function createRow(data = null) {
        const tr = document.createElement("tr");
        tr.className = "fade-in";
        
        const productId = data ? data.product_id : "";
        const openingVal = data ? data.remaining : 0;
        // In restock mode, opening is 0 for new rows. In normal mode, it's leftover.
        // But if data is provided (normal mode), we lock opening.
        const openingReadonly = data ? "readonly" : ""; 

        // Build options ensuring selected value
        let options = productOptionsHtml.replace(`value="${productId}"`, `value="${productId}" selected`);

        tr.innerHTML = `
            <td class="text-center fw-bold text-muted row-index"></td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown">
                    ${options}
                </select>
            </td>
            <td>
                <div class="input-group input-group-sm">
                    <span class="input-group-text border-0 bg-transparent">₹</span>
                    <input type="number" name="price[]" class="form-control-plaintext price" readonly value="${data ? data.price : 0}">
                </div>
            </td>
            <td>
                <input type="number" name="opening[]" class="form-control form-control-sm text-center opening" 
                       value="${openingVal}" ${openingReadonly} min="0">
            </td>
            <td>
                <input type="number" name="given[]" class="form-control form-control-sm text-center given" value="0" min="0">
            </td>
            <td class="text-center fw-bold text-primary total-qty">
                ${openingVal}
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateRowData(tr, productId) {
        const prod = productsMap.get(productId);
        const priceInput = tr.querySelector(".price");
        if (prod) {
            priceInput.value = prod.price;
        } else {
            priceInput.value = 0;
        }
    }

    function recalculateRow(tr) {
        const op = parseInt(tr.querySelector(".opening").value) || 0;
        const giv = parseInt(tr.querySelector(".given").value) || 0;
        const total = op + giv;
        tr.querySelector(".total-qty").textContent = total;
        recalculateTotals();
    }

    function recalculateTotals() {
        let tOp = 0, tGiv = 0, tAll = 0, tAmt = 0;
        ui.tableBody.querySelectorAll("tr").forEach(tr => {
            const op = parseInt(tr.querySelector(".opening").value) || 0;
            const giv = parseInt(tr.querySelector(".given").value) || 0;
            const pr = parseFloat(tr.querySelector(".price").value) || 0;
            
            tOp += op;
            tGiv += giv;
            tAll += (op + giv);
            tAmt += (giv * pr); // Only charge for Given, typically? Or Opening too? Usually Morning form calc value of Given.
        });

        ui.totals.opening.textContent = tOp;
        ui.totals.given.textContent = tGiv;
        ui.totals.all.textContent = tAll;
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
            if(confirm("Remove row?")) { e.target.closest("tr").remove(); updateRowIndexes(); recalculateTotals(); }
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if(e.target.matches(".product-dropdown")) {
            updateRowData(e.target.closest("tr"), e.target.value);
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if(e.target.matches(".given") || e.target.matches(".opening")) {
            recalculateRow(e.target.closest("tr"));
        }
    });
});
