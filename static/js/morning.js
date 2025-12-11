document.addEventListener("DOMContentLoaded", () => {
    const ui = {
        employeeSelect: document.getElementById("employee_id"),
        dateInput: document.getElementById("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: document.getElementById("addRow"),
        fetchMsg: document.getElementById("fetchMsg"),
        totals: {
            opening: document.getElementById("totalOpening"),
            given: document.getElementById("totalGiven"),
            all: document.getElementById("totalAll"),
            grand: document.getElementById("grandTotal")
        }
    };

    let currentStockData = {};
    const productsMap = new Map((window.productsData || []).map(p => [String(p.id), p]));
    const DEFAULT_IMG = "https://via.placeholder.com/40?text=?";

    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-5"><i class="fa-solid fa-arrow-up me-2"></i>Select Employee & Date to start</td></tr>';
            return;
        }

        ui.fetchMsg.innerHTML = '<span class="text-primary"><i class="fas fa-spinner fa-spin"></i> Checking stock...</span>';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                currentStockData = {}; 
                ui.fetchMsg.innerHTML = '<span class="text-warning"><i class="fa-solid fa-circle-exclamation"></i> New day (No previous stock)</span>';
            } else {
                currentStockData = data;
                ui.fetchMsg.innerHTML = '<span class="text-success"><i class="fa-solid fa-check-circle"></i> Opening stock synced</span>';
            }

            if (ui.tableBody.rows.length === 1 && ui.tableBody.rows[0].cells.length === 1) {
                ui.tableBody.innerHTML = '';
            }

            updateAllRows();
            setTimeout(() => ui.fetchMsg.innerHTML = '', 3000);

        } catch (error) {
            ui.fetchMsg.innerHTML = '<span class="text-danger">Connection Failed</span>';
        }
    }

    function createRow() {
        if (ui.tableBody.rows.length === 1 && ui.tableBody.rows[0].cells.length === 1) {
            ui.tableBody.innerHTML = '';
        }

        const tr = document.createElement("tr");

        let optionsHtml = '<option value="">-- Select --</option>';
        (window.productOptions || []).forEach(opt => {
            optionsHtml += `<option value="${opt.id}">${opt.name}</option>`;
        });

        tr.innerHTML = `
            <td class="row-index ps-4 fw-bold text-muted small"></td>
            <td class="text-center">
                <img src="${DEFAULT_IMG}" class="product-thumb" alt="img">
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${optionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="0" readonly></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="0" readonly></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="0.00" readonly></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly></td>
            <td class="text-center"><button type="button" class="btn btn-link text-danger p-0 btn-remove-row"><i class="fa-solid fa-trash-can"></i></button></td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
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

    function updateRowData(row, productId) {
        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        
        const product = productsMap.get(productId);
        if (product && product.image) {
            img.src = product.image.startsWith('http') ? product.image : `/static/uploads/${product.image}`;
            img.onerror = () => { img.src = DEFAULT_IMG; };
        } else {
            img.src = DEFAULT_IMG;
        }

        let openingQty = 0;
        if (currentStockData[productId]) {
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
            if (!row.querySelector(".total")) return;

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
            const idx = tr.querySelector(".row-index");
            if(idx) idx.textContent = i + 1;
        });
    }

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    
    ui.addRowBtn.addEventListener("click", () => {
        createRow();
        recalculateTotals();
    });

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            e.target.closest("tr").remove();
            updateRowIndexes();
            recalculateTotals();
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
});
