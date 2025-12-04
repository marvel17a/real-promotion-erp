document.addEventListener("DOMContentLoaded", () => {
    // 1. UI Elements
    const ui = {
        employeeSelect: document.getElementById("employee_id"),
        dateInput: document.getElementById("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: document.getElementById("addRow"),
        fetchMsg: document.getElementById("fetchMsg"),
        // Footer Totals
        totals: {
            opening: document.getElementById("totalOpening"),
            given: document.getElementById("totalGiven"),
            all: document.getElementById("totalAll"),
            grand: document.getElementById("grandTotal")
        }
    };

    // State
    let currentStockData = {}; // Stores fetched stock { product_id: { remaining, price } }
    const productsMap = new Map((window.productsData || []).map(p => [String(p.id), p]));
    const productOptionsHtml = window.productOptions || "";

    // 2. Fetch Previous Day's Stock (Opening Balance)
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        ui.fetchMsg.textContent = "Fetching previous closing stock...";
        ui.fetchMsg.classList.remove('d-none', 'alert-danger', 'alert-success');
        ui.fetchMsg.classList.add('alert-info');

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            currentStockData = data; // Store globally
            
            // Update any existing rows with new stock info
            updateAllRowsStock();
            
            ui.fetchMsg.textContent = "Stock data loaded. Opening balances updated.";
            ui.fetchMsg.classList.remove('alert-info');
            ui.fetchMsg.classList.add('alert-success');
            setTimeout(() => ui.fetchMsg.classList.add('d-none'), 3000);

        } catch (error) {
            console.error("Stock Fetch Error:", error);
            ui.fetchMsg.textContent = "Note: Could not fetch previous stock (New allocation or Error).";
            ui.fetchMsg.classList.remove('alert-info');
            ui.fetchMsg.classList.add('alert-warning');
            currentStockData = {}; // Reset on error
        }
    }

    // 3. Row Management
    function createRow() {
        // Remove "Select Employee..." message if it exists
        if (ui.tableBody.rows.length === 1 && ui.tableBody.rows[0].cells.length > 1) {
            ui.tableBody.innerHTML = '';
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold"></td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    <option value="">-- Select Product --</option>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control text-center opening" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control text-center fw-bold text-primary given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control text-center bg-light total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control text-center bg-light price" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control text-end amount" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center"><button type="button" class="btn btn-sm text-danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateAllRowsStock() {
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
        
        // 1. Set Opening Stock (from API)
        let openingQty = 0;
        if (currentStockData[productId]) {
            openingQty = parseInt(currentStockData[productId].remaining) || 0;
        }
        openingInput.value = openingQty;

        // 2. Set Price (from Window Data or API)
        // API price takes precedence, otherwise fallback to product master price
        let price = 0;
        if (currentStockData[productId]) {
            price = parseFloat(currentStockData[productId].price);
        } else {
            const product = productsMap.get(productId);
            if (product) price = parseFloat(product.price);
        }
        priceInput.value = price.toFixed(2);
        
        recalculateRow(row);
    }

    // 4. Calculations
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
            if (!row.querySelector(".total")) return; // Skip info rows

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

    // 5. Event Listeners
    
    // Fetch Stock when Employee or Date changes
    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    // Add Row
    ui.addRowBtn.addEventListener("click", () => {
        createRow();
        recalculateTotals();
    });

    // Delegate Events inside Table (Input & Click)
    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            e.target.closest("tr").remove();
            updateRowIndexes();
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            const row = e.target.closest("tr");
            updateRowData(row, e.target.value);
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            const row = e.target.closest("tr");
            recalculateRow(row);
            recalculateTotals();
        }
    });

});
