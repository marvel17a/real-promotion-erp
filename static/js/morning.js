document.addEventListener("DOMContentLoaded", () => {

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

    if (!ui.employeeSelect || !ui.tableBody) return;

    let currentStockData = {};
    const productsData = window.productsData || [];
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55?text=Img";

    // ✅ Build dropdown options from JSON
    let productOptionsHtml = '<option value="">-- Select --</option>';
    productsData.forEach(p => {
        productsMap.set(String(p.id), p);
        productOptionsHtml += `<option value="${p.id}">${p.name}</option>`;
    });

    /* ---------------------------------------------------
       FETCH STOCK
    --------------------------------------------------- */
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if (!employeeId || !dateStr) return;

        ui.fetchMsg.innerHTML =
            '<span class="text-primary"><i class="fas fa-spinner fa-spin"></i> Checking stock...</span>';

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (data.error && response.status !== 500) {
                currentStockData = {};
                ui.fetchMsg.innerHTML = '<span class="text-warning small">New Day (No previous stock)</span>';
            } else {
                currentStockData = data;
                ui.fetchMsg.innerHTML = '<span class="text-success small">Stock Synced</span>';
            }

            updateAllRows();
            setTimeout(() => ui.fetchMsg.innerHTML = '', 3000);

        } catch (error) {
            ui.fetchMsg.innerHTML = '<span class="text-danger small">Connection Error</span>';
        }
    }

    /* ---------------------------------------------------
       CREATE ROW
    --------------------------------------------------- */
    function createRow() {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold small py-3"></td>

            <td class="text-center">
                <div class="img-box">
                    <img src="${DEFAULT_IMG}" class="product-thumb" alt="Product"
                         style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </td>

            <td>
                <select name="product_id[]" class="form-select product-dropdown" required>
                    ${productOptionsHtml}
                </select>
            </td>

            <td><input type="number" name="opening[]" class="form-control opening" value="0" readonly></td>
            <td><input type="number" name="given[]" class="form-control given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control total" value="0" readonly></td>
            <td><input type="number" name="price[]" class="form-control price" step="0.01" value="0.00" readonly></td>
            <td><input type="number" name="amount[]" class="form-control amount text-end" value="0.00" readonly></td>

            <td class="text-center">
                <button type="button" class="btn btn-link text-danger p-0 btn-remove-row">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;

        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    /* ---------------------------------------------------
       UPDATE ROW DATA
    --------------------------------------------------- */
    function updateRowData(row, productId) {

        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");

        const product = productsMap.get(productId);

        // ✅ Image
        if (product && product.image) {
            img.src = product.image.startsWith("http")
                ? product.image
                : `/static/uploads/${product.image}`;
        } else {
            img.src = DEFAULT_IMG;
        }

        // ✅ Opening Stock
        let openingQty = currentStockData[productId]
            ? parseInt(currentStockData[productId].remaining) || 0
            : 0;

        openingInput.value = openingQty;

        // ✅ Price
        let price = currentStockData[productId]
            ? parseFloat(currentStockData[productId].price)
            : product
            ? parseFloat(product.price)
            : 0;

        priceInput.value = price.toFixed(2);

        recalculateRow(row);
    }

    /* ---------------------------------------------------
       RECALCULATE ROW
    --------------------------------------------------- */
    function recalculateRow(row) {
        const opening = parseInt(row.querySelector(".opening").value) || 0;
        const given = parseInt(row.querySelector(".given").value) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;

        const total = opening + given;
        const amount = total * price;

        row.querySelector(".total").value = total;
        row.querySelector(".amount").value = amount.toFixed(2);
    }

    /* ---------------------------------------------------
       RECALCULATE TOTALS
    --------------------------------------------------- */
    function recalculateTotals() {
        let tOpening = 0, tGiven = 0, tAll = 0, tGrand = 0;

        ui.tableBody.querySelectorAll("tr").forEach(row => {
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

    /* ---------------------------------------------------
       UPDATE ROW INDEXES
    --------------------------------------------------- */
    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }

    /* ---------------------------------------------------
       EVENT LISTENERS
    --------------------------------------------------- */
    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault();
        createRow();
        recalculateTotals();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if (confirm("Remove this item?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
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

    fetchStockData();
});
