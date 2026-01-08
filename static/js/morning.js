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

    let productOptionsHtml = '<option value="">-- Select --</option>';
    if (window.productsData) window.productsData.forEach(p => productOptionsHtml += `<option value="${p.id}" data-price="${p.price}" data-stock="${p.stock}" data-img="${p.image}">${p.name}</option>`);
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    function updateClock() {
        const now = new Date();
        if(ui.clockDisplay) ui.clockDisplay.textContent = now.toLocaleTimeString('en-US', { hour12: true });
        if(ui.timestampInput) ui.timestampInput.value = now.getFullYear() + '-' + String(now.getMonth()+1).padStart(2,'0') + '-' + String(now.getDate()).padStart(2,'0') + ' ' + String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0') + ':' + String(now.getSeconds()).padStart(2,'0');
    }
    setInterval(updateClock, 1000);
    updateClock();

    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;
        if (!empId || !dateVal) return;

        ui.fetchMsg.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
        ui.historyList.innerHTML = '';
        ui.tableBody.innerHTML = '';
        ui.addRowBtn.style.display = 'none';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${empId}&date=${dateVal}`);
            const data = await response.json();

            if (data.evening_settled) {
                ui.fetchMsg.innerHTML = '<div class="alert alert-warning py-2 shadow-sm"><i class="fa-solid fa-lock me-2"></i>Evening Finalized.</div>';
                document.querySelector('.btn-save').style.display = 'none';
                return;
            }
            ui.addRowBtn.style.display = 'block';
            document.querySelector('.btn-save').style.display = 'block';

            if (data.mode === 'restock') {
                ui.fetchMsg.innerHTML = '<span class="badge bg-warning text-dark mb-2">Restock Mode</span>';
                if(data.existing_items && data.existing_items.length > 0) {
                    let html = `<div class="card border-warning mb-3 shadow-sm"><div class="card-header bg-warning bg-opacity-10 small fw-bold">TOTAL STOCK WITH EMPLOYEE (Aggregated)</div><div class="card-body p-2 d-flex flex-wrap gap-2">`;
                    data.existing_items.forEach(item => {
                        html += `<div class="d-flex align-items-center border rounded p-1 pe-3 bg-white"><img src="${item.image}" width="35" class="rounded me-2"><div><div class="small fw-bold lh-1">${item.name}</div><div class="badge bg-secondary mt-1">Total: ${item.qty}</div></div></div>`;
                    });
                    html += `</div></div>`;
                    ui.historyList.innerHTML = html;
                }
            } else {
                ui.fetchMsg.innerHTML = '<span class="text-success small fw-bold">New Allocation</span>';
            }
            
            // Populate Opening in Table (Always)
            if (data.opening_stock && data.opening_stock.length > 0) {
                data.opening_stock.forEach(item => createRow(item));
            } else {
                createRow();
            }
            
            // Ensure at least one row in Restock
            if(data.mode === 'restock' && ui.tableBody.children.length === 0) createRow();
            
            recalculateTotals();

        } catch (error) {
            console.error(error);
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Error</span>';
            ui.addRowBtn.style.display = 'block';
            createRow();
        }
    }

    function createRow(data = null) {
        const tr = document.createElement("tr");
        let open = data ? data.remaining : 0;
        let price = data ? data.price : 0;
        let img = data ? data.image : DEFAULT_IMG;

        tr.innerHTML = `
            <td class="text-center row-index"></td>
            <td><img src="${img}" class="product-thumb" width="40"></td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>${productOptionsHtml}</select>
                <div class="small text-danger fw-bold mt-1 stock-warning" style="display:none;"></div>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="${open}" readonly></td>
            <td><input type="number" name="given[]" class="form-control given" value="0"></td>
            <td><input type="number" name="total[]" class="form-control total" value="${open}" readonly></td>
            <td><input type="number" name="price[]" class="form-control price text-end" value="${price.toFixed(2)}" readonly></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly></td>
            <td><button type="button" class="btn btn-danger btn-sm remove-row">X</button></td>
        `;
        ui.tableBody.appendChild(tr);
        if(data) tr.querySelector('.product-dropdown').value = data.product_id;

        tr.querySelector('.product-dropdown').addEventListener('change', function() {
            const opt = this.selectedOptions[0];
            tr.querySelector('.price').value = opt.getAttribute('data-price') || 0;
            tr.querySelector('.product-thumb').src = opt.getAttribute('data-img') || DEFAULT_IMG;
        });
        tr.querySelector('.given').addEventListener('input', function() {
            const op = parseInt(tr.querySelector('.opening').value)||0;
            const giv = parseInt(this.value)||0;
            const pr = parseFloat(tr.querySelector('.price').value)||0;
            tr.querySelector('.total').value = op + giv;
            tr.querySelector('.amount').value = ((op + giv) * pr).toFixed(2);
        });
        tr.querySelector('.remove-row').addEventListener('click', function() { tr.remove(); });
    }

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    ui.addRowBtn.addEventListener("click", () => createRow());
});
