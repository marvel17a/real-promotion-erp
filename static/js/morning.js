document.addEventListener("DOMContentLoaded", () => {
    // 1. UI Elements Cache (With Safety Checks)
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"), // Matched to HTML
        dateInput: getEl("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    // 2. Validate Critical Elements exist
    if (!ui.employeeSelect || !ui.dateInput || !ui.tableBody || !ui.addRowBtn) {
        console.error("Critical UI elements missing. Check HTML IDs.");
        return; // Stop execution if UI is broken
    }

    // 3. State & Data
    let currentStockData = {};
    const productsData = window.productsData || [];
    const productOptionsHtml = window.productOptions || '<option value="">Error loading products</option>';
    const productsMap = new Map(productsData.map(p => [String(p.id), p]));
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    // 4. Core Functions
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) {
            // Don't clear table, just stop
            return;
        }

        updateStatus('loading', 'Checking stock...');

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                // Warning logic (e.g. no prev stock)
                currentStockData = {}; 
                updateStatus('warning', 'New allocation (No previous stock found)');
            } else {
                currentStockData = data;
                updateStatus('success', 'Stock synced with previous records');
            }

            // Update all existing rows with new stock data
            updateAllRows();

        } catch (error) {
            console.error("Fetch Error:", error);
            updateStatus('error', 'Connection failed. Please refresh.');
        }
    }

    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index ps-4 fw-bold text-muted small py-3"></td>
            <td class="text-center">
                <img src="${DEFAULT_IMG}" class="product-thumb" alt="Product">
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    <option value="">-- Select Product --</option>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row"><i class="fa-solid fa-trash-can"></i></button>
            </td>
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
        
        // 1. Update Image
        const product = productsMap.get(productId);
        if (product && product.image) {
            // Handle both full URLs and filenames
            img.src = product.image.startsWith('http') ? product.image : `/static/uploads/${product.image}`;
            img.onerror = () => { img.src = DEFAULT_IMG; };
        } else {
            img.src = DEFAULT_IMG;
        }

        // 2. Update Stock
        let openingQty = 0;
        if (currentStockData[productId]) {
            openingQty = parseInt(currentStockData[productId].remaining) || 0;
        }
        openingInput.value = openingQty;

        // 3. Update Price (API price takes priority over Master price)
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
            tOpening += parseInt(row.querySelector(".opening").value) || 0;
            tGiven += parseInt(row.querySelector(".given").value) || 0;
            tAll += parseInt(row.querySelector(".total").value) || 0;
            tGrand += parseFloat(row.querySelector(".amount").value) || 0;
        });

        if(ui.totals.opening) ui.totals.opening.textContent = tOpening;
        if(ui.totals.given) ui.totals.given.textContent = tGiven;
        if(ui.totals.all) ui.totals.all.textContent = tAll;
        if(ui.totals.grand) ui.totals.grand.textContent = tGrand.toFixed(2);
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            const idx = tr.querySelector(".row-index");
            if(idx) idx.textContent = i + 1;
        });
    }

    function updateStatus(type, msg) {
        if(!ui.fetchMsg) return;
        ui.fetchMsg.innerHTML = msg;
        ui.fetchMsg.className = "w-100 text-center small fw-bold mt-2"; // Reset
        
        if(type === 'loading') ui.fetchMsg.classList.add('text-primary');
        if(type === 'success') {
            ui.fetchMsg.classList.add('text-success');
            setTimeout(() => ui.fetchMsg.innerHTML = '', 3000);
        }
        if(type === 'error') ui.fetchMsg.classList.add('text-danger');
        if(type === 'warning') ui.fetchMsg.classList.add('text-warning');
    }

    // 5. Event Listeners
    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    
    // The Button Fix
    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault(); // Prevent form submit
        createRow();
        recalculateTotals();
    });

    // Delegation
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
            recalculateRow(e.target.closest("tr"));
            recalculateTotals();
        }
    });
    
    // Initial call just in case inputs are pre-filled
    fetchStockData();
});
