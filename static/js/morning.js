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

    // Fetch Stock
    async function fetchStockData() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;
        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr class="placeholder-row"><td colspan="9" class="text-center text-muted py-5">Select Employee & Date</td></tr>';
            return;
        }

        ui.fetchMsg.textContent = "Checking stock...";
        ui.fetchMsg.className = "alert alert-info mb-3 border-0 shadow-sm";
        ui.fetchMsg.classList.remove("d-none");

        try {
            const response = await fetch(`/api/fetch_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();
            currentStockData = data.error ? {} : data;

            if (ui.tableBody.querySelector(".placeholder-row")) ui.tableBody.innerHTML = "";

            updateAllRows();

            ui.fetchMsg.textContent = "Stock updated.";
            ui.fetchMsg.className = "alert alert-success mb-3 border-0 shadow-sm";
            setTimeout(() => ui.fetchMsg.classList.add("d-none"), 2000);

        } catch (error) {
            ui.fetchMsg.textContent = "Connection error.";
            ui.fetchMsg.className = "alert alert-danger mb-3 border-0";
        }
    }

    // Create Row
    function createRow() {
        if (ui.tableBody.querySelector(".placeholder-row")) ui.tableBody.innerHTML = "";

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index ps-3 text-muted fw-bold"></td>
            <td class="text-center">
                <img src="${DEFAULT_IMG}" class="product-thumb" alt="img">
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown border-0" required>
                    <option value="">-- Select --</option>
                    ${window.productOptions}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control text-center opening bg-light" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="form-control text-center fw-bold text-primary given" min="0" placeholder="0" required></td>
            <td><input type="number" name="total[]" class="form-control text-center bg-light total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="form-control text-center bg-light price" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="form-control text-end amount bg-light" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center"><button type="button" class="btn btn-sm text-danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateAllRows() {
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const select = row.querySelector(".product-dropdown");
            if (select && select.value) updateRowData(row, select.value);
        });
        recalculateTotals();
    }

    function updateRowData(row, productId) {
        const openingInput = row.querySelector(".opening");
        const priceInput = row.querySelector(".price");
        const img = row.querySelector(".product-thumb");

        const product = productsMap.get(productId);
        if (product && typeof product.image === "string" && product.image.length > 0) {
            if (product.image.startsWith("http")) img.src = product.image;
            else img.src = `/static/uploads/${product.image}`;
            img.onerror = () => { img.src = DEFAULT_IMG; };
        } else {
            img.src = DEFAULT_IMG;
        }

        let openingQty = 0;
        if (currentStockData[productId]) openingQty = parseInt(currentStockData[productId].remaining, 10) || 0;
        openingInput.value = openingQty;

        let price = 0;
        if (currentStockData[productId]) price = parseFloat(currentStockData[productId].price) || 0;
        else if (product) price = parseFloat(product.price) || 0;
        priceInput.value = price.toFixed(2);

        recalculateRow(row);
    }

    function recalculateRow(row) {
        const opening = parseInt(row.querySelector(".opening").value, 10) || 0;
        const given = parseInt(row.querySelector(".given").value, 10) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;
        const total = opening + given;

        row.querySelector(".total").value = total;
        row.querySelector(".amount").value = (total * price).toFixed(2);
    }

    function recalculateTotals() {
        let tOpening = 0, tGiven = 0, tAll = 0, tGrand = 0;
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            if (!row.querySelector(".total")) return;
            tOpening += parseInt(row.querySelector(".opening").value, 10) || 0;
            tGiven += parseInt(row.querySelector(".given").value, 10) || 0;
            tAll += parseInt(row.querySelector(".total").value, 10) || 0;
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
            if (idx) idx.textContent = i + 1;
        });
    }

    // Event Listeners
    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);
    ui.addRowBtn.addEventListener("click", () => { createRow(); recalculateTotals(); });

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

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            const row = e.target.closest("tr");
            // Confirmation popup before deletion
            const confirmDelete = confirm("Are you sure you want to delete this item?");
            if (confirmDelete) {
                row.remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });
});
