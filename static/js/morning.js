document.addEventListener("DOMContentLoaded", () => {
    // 1. Safe Element Getter
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"),
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

    // 2. Safety Check: If HTML is missing, stop silently (don't crash browser)
    if (!ui.employeeSelect || !ui.tableBody || !ui.addRowBtn) {
        console.error("Morning Module: Critical UI elements missing.");
        return;
    }

    // 3. Initialize Data
    let currentStockData = {};
    // Fallback empty array if data isn't loaded
    const productsData = window.productsData || []; 
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    // 4. Build Dropdown Options Dynamically (The Fix)
    let productOptionsHtml = '<option value="">-- Select --</option>';
    
    if (Array.isArray(productsData) && productsData.length > 0) {
        productsData.forEach(p => {
            // Populate Map for fast lookup
            productsMap.set(String(p.id), p);
            // Build Option
            productOptionsHtml += `<option value="${p.id}">${p.name}</option>`;
        });
    } else {
        productOptionsHtml = '<option value="">No products found</option>';
    }

    // 5. Fetch Stock Logic
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        updateStatus('loading', '<i class="fas fa-spinner fa-spin"></i> Checking stock...');

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                currentStockData = {}; // Reset stock for new day
                updateStatus('warning', 'New Allocation (No previous stock)');
            } else {
                currentStockData = data;
                updateStatus('success', 'Stock Synced');
            }
            
            updateAllRows(); // Refresh existing rows with new stock data

        } catch (error) {
            console.error("Fetch error:", error);
            updateStatus('error', 'Connection Failed');
        }
    }

    // 6. Row Creation
    function createRow() {
        // Clear "empty" message if it exists
        if (ui.tableBody.rows.length === 1 && !ui.tableBody.rows[0].querySelector('input')) {
            ui.tableBody.innerHTML = '';
        }

        const tr = document.createElement("tr");
        tr.className = "fade-in-row"; // Animation class
        
        tr.innerHTML = `
            <td class="row-index ps-4 fw-bold text-muted small py-3"></td>
            <td class="text-center">
                <div class="img-box">
                    <img src="${DEFAULT_IMG}" class="product-thumb" alt="Product" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control opening" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row" title="Remove"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateRowData(row, productId) {
        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");
        
        // 1. Image Handling
        const product = productsMap.get(productId);
        if (product && product.image) {
            // Handle full URL vs filename
            const src = product.image.startsWith('http') ? product.image : `/static/uploads/${product.image}`;
            img.src = src;
            img.onerror = () => { img.src = DEFAULT_IMG; };
        } else {
            img.src = DEFAULT_IMG;
        }

        // 2. Stock Handling
        let openingQty = 0;
        if (currentStockData[productId]) {
            openingQty = parseInt(currentStockData[productId].remaining) || 0;
        }
        openingInput.value = openingQty;

        // 3. Price Handling
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
            // Skip invalid rows
            if(!row.querySelector(".opening")) return;

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

    function updateAllRows() {
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const select = row.querySelector(".product-dropdown");
            if (select && select.value) {
                updateRowData(row, select.value);
            }
        });
        recalculateTotals();
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
        ui.fetchMsg.className = "w-100 text-center small fw-bold mt-2"; // reset
        if(type === 'loading') ui.fetchMsg.classList.add('text-primary');
        if(type === 'success') {
            ui.fetchMsg.classList.add('text-success');
            setTimeout(() => ui.fetchMsg.innerHTML = '', 3000);
        }
        if(type === 'warning') ui.fetchMsg.classList.add('text-warning');
        if(type === 'error') ui.fetchMsg.classList.add('text-danger');
    }

    // 7. Event Listeners
    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault(); // Stop any form submit
        createRow();
        recalculateTotals();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    // Event Delegation for dynamic rows
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

    // Check on load
    fetchStockData();
});
