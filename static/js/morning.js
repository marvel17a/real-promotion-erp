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
        historyList: getEl("historyList")
    };

    // Digital Clock
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

    // Fetch
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;
        if (!empId || !dateVal) return;

        ui.fetchMsg.innerHTML = '<span class="text-primary fw-bold"><i class="fas fa-spinner fa-spin"></i> Checking stock...</span>';
        if(ui.historyList) ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = '';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${empId}&date=${dateVal}`);
            const data = await response.json();

            // 1. Locked
            if (data.evening_settled) {
                ui.fetchMsg.innerHTML = '<div class="alert alert-warning py-2"><i class="fa-solid fa-lock"></i> Evening Finalized. Locked.</div>';
                ui.addRowBtn.style.display = 'none';
                document.querySelector('.btn-save').style.display = 'none';
                return;
            } else {
                ui.addRowBtn.style.display = 'block';
                document.querySelector('.btn-save').style.display = 'block';
            }

            // 2. Restock Mode
            if (data.mode === 'restock') {
                ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark mb-2">Restock Mode</span>';
                
                if(data.existing_items && data.existing_items.length > 0) {
                    let html = `<div class="card border-warning mb-3"><div class="card-header bg-warning bg-opacity-10 small fw-bold">Stock Given Today (Aggregated)</div><div class="card-body p-2 d-flex flex-wrap gap-2">`;
                    data.existing_items.forEach(item => {
                        html += `<div class="d-flex align-items-center border rounded p-1 pe-3 bg-white"><img src="${item.image}" width="35" class="rounded me-2"><div><div class="small fw-bold">${item.name}</div><div class="badge bg-secondary">Added: ${item.qty}</div></div></div>`;
                    });
                    html += `</div></div>`;
                    ui.historyList.innerHTML = html;
                }
                createRow(); // Empty row for new entry
            } 
            
            // 3. Normal Mode
            else {
                ui.fetchMsg.innerHTML = '<span class="text-success small fw-bold">Ready</span>';
                if (data.opening_stock && data.opening_stock.length > 0) {
                    data.opening_stock.forEach(item => createRow(item));
                } else {
                    createRow();
                }
            }

        } catch (error) {
            console.error(error);
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Error fetching</span>';
            createRow();
        }
    }

    // Helpers
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";
    let productOptions = '<option value="">Select</option>';
    if(window.productsData) window.productsData.forEach(p => productOptions += `<option value="${p.id}" data-price="${p.price}" data-img="${p.image}">${p.name}</option>`);

    function createRow(data = null) {
        const tr = document.createElement("tr");
        let op = data ? data.remaining : 0;
        let pr = data ? data.price : 0;
        let im = data ? data.image : DEFAULT_IMG;

        tr.innerHTML = `
            <td class="text-center row-index"></td>
            <td><img src="${im}" class="product-thumb" width="40"></td>
            <td><select name="product_id[]" class="form-select product-dropdown" required>${productOptions}</select></td>
            <td><input type="number" name="opening[]" class="form-control opening" value="${op}" readonly></td>
            <td><input type="number" name="given[]" class="form-control given" value="0"></td>
            <td><input type="number" name="total[]" class="form-control total" value="${op}" readonly></td>
            <td><input type="number" name="price[]" class="form-control price text-end" value="${pr}" readonly></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly></td>
            <td><button type="button" class="btn btn-danger btn-sm remove-row">X</button></td>
        `;
        ui.tableBody.appendChild(tr);
        if(data) tr.querySelector('.product-dropdown').value = data.product_id;
        
        // Trigger calculation if data present
        if(data) {
             // Logic to trigger recalc would go here, usually handled by event listeners on input
        }
    }

    // Events
    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    ui.addRowBtn.addEventListener("click", () => createRow());
    
    ui.tableBody.addEventListener("change", e => {
        if(e.target.matches('.product-dropdown')) {
            const opt = e.target.selectedOptions[0];
            const row = e.target.closest('tr');
            row.querySelector('.price').value = opt.getAttribute('data-price') || 0;
            row.querySelector('.product-thumb').src = opt.getAttribute('data-img') || DEFAULT_IMG;
        }
    });

    // ... Calculation logic remains standard ...
});

    // --- 4. CALCULATIONS ---
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

        const productId = row.querySelector(".product-dropdown").value;
        const warningEl = row.querySelector(".stock-warning");

        if (productId) {
            const product = productsMap.get(productId);
            const maxAvailable = product ? product.stock : 999999;

            if (given > maxAvailable) {
                given = maxAvailable;
                givenInput.value = maxAvailable;
                warningEl.textContent = `Only ${maxAvailable} available`;
                warningEl.style.display = 'block';
            } else {
                warningEl.style.display = 'none';
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
            if (!row.querySelector(".opening")) return;
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

    // --- EVENTS ---
    ui.addRowBtn.addEventListener("click", e => {
        e.preventDefault();
        createRow();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if (confirm("Remove row?")) {
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

    document.addEventListener("keydown", e => {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll("input:not([readonly]), select"));
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) inputs[index + 1].focus();
        }
    });
});

