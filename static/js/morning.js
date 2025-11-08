document.addEventListener("DOMContentLoaded", () => {
    // --- 1. DOM Element Cache ---
    const ui = {
        employeeSelect: document.getElementById("employee_id"),
        dateInput: document.getElementById("date"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: document.getElementById("addRow"),
        morningForm: document.getElementById("morningForm"),
        fetchMsg: document.getElementById("fetchMsg"),
        totals: {
            opening: document.getElementById("totalOpening"),
            given: document.getElementById("totalGiven"),
            all: document.getElementById("totalAll"),
            grand: document.getElementById("grandTotal")
        }
    };
    const productOptionsHtml = window.productOptions || "";

    const productsMap = new Map((window.productsData || []).map(p => [String(p.id), p]));


    // --- 2. Core Functions ---
    async function fetchAndPopulate() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        ui.tableBody.innerHTML = ''; 
        ui.fetchMsg.textContent = '';
        recalculateTotals();

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-muted p-4">Select an employee and date to begin.</td></tr>';
            return;
        }

        ui.fetchMsg.textContent = "Checking for previous day's stock...";
        ui.fetchMsg.className = "small text-info mb-2";

        try {
            // Uses NEW API function name
            const response = await fetch(`/api_get_previous_stock?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Network error");

            if (Object.keys(data).length === 0) {
                ui.fetchMsg.textContent = "No remaining stock found. Starting a new allocation.";
                createRow(); 
            } else {
                ui.fetchMsg.textContent = "Previous day's stock loaded successfully.";
                for (const productId in data) {
                    const item = data[productId];
                    createRow({ id: productId, opening: item.remaining, price: item.price });
                }
            }
        } catch (error) {
            console.error('Fetch Error:', error);
            ui.fetchMsg.textContent = `Error: ${error.message}. Starting a new allocation.`;
            ui.fetchMsg.className = "small text-danger mb-2";
            createRow(); 
        } finally {
            recalculateTotals();
        }
    }

    function createRow(productData = {}) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index"></td>
            <td class="text-start">
                <select name="product_id[]" class="form-select form-select-sm product-dropdown" required>
                    <option value="">-- Select Product --</option>
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="opening[]" class="form-control form-control-sm opening" value="${productData.opening || 0}" readonly></td>
            <td><input type="number" name="given[]" class="form-control form-control-sm given" min="0" value="" required></td>
            <td><input type="number" name="total[]" class="form-control form-control-sm total" value="0" readonly></td>
            <td><input type="number" name="price[]" class="form-control form-control-sm price" step="0.01" min="0" value="${productData.price || 0.00}" readonly></td>
            <td><input type="number" name="amount[]" class="form-control form-control-sm amount" value="0" readonly></td>
            <td><button type="button" class="btn-remove-row" title="Remove row">Delete</button></td>
        `;
        const select = tr.querySelector(".product-dropdown");
        if (productData.id) {
            select.value = productData.id;
        }
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function recalculateTotals() {
        let totalOpening = 0, totalGiven = 0, totalAll = 0, grandTotal = 0;
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const opening = parseInt(row.querySelector(".opening")?.value) || 0;
            const given = parseInt(row.querySelector(".given")?.value) || 0;
            const price = parseFloat(row.querySelector(".price")?.value) || 0;
            if (!row.querySelector(".total")) return; 

            const total = opening + given;
            const amount = total * price;

            row.querySelector(".total").value = total;
            row.querySelector(".amount").value = amount.toFixed(2);

            totalOpening += opening;
            totalGiven += given;
            totalAll += total;
            grandTotal += amount;
        });

        ui.totals.opening.textContent = totalOpening;
        ui.totals.given.textContent = totalGiven;
        ui.totals.all.textContent = totalAll;
        ui.totals.grand.textContent = grandTotal.toFixed(2);
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            const indexCell = tr.querySelector(".row-index");
            if (indexCell) indexCell.textContent = i + 1;
        });
    }

    function validateDuplicates(currentSelect) {
        const selectedValues = [...ui.tableBody.querySelectorAll(".product-dropdown")]
            .map(s => s.value).filter(v => v);
        if (selectedValues.filter(v => v === currentSelect.value).length > 1) {
            alert("Duplicate product selected. Please choose a different product.");
            currentSelect.value = "";
        }
    }

    function handleArrowKeyNavigation(e) {
        const key = e.key;
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
            return;
        }

        const activeElement = document.activeElement;
        if (!activeElement || !ui.tableBody.contains(activeElement) || (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'SELECT')) {
            return;
        }

        e.preventDefault();

        const currentRow = activeElement.closest('tr');
        const rows = Array.from(ui.tableBody.children);
        const rowIndex = rows.indexOf(currentRow);
        let targetElement = null;

        if (key === 'ArrowUp' || key === 'ArrowDown') {
            const nextRowIndex = key === 'ArrowDown' ? rowIndex + 1 : rowIndex - 1;
            if (nextRowIndex >= 0 && nextRowIndex < rows.length) {
                const targetRow = rows[nextRowIndex];
                const activeElementClass = activeElement.className.split(' ').find(c => ['product-dropdown', 'given', 'price'].includes(c));
                if (activeElementClass) {
                    targetElement = targetRow.querySelector(`.${activeElementClass}`);
                }
            }
        } else if (key === 'ArrowLeft' || key === 'ArrowRight') {
            const focusableInRow = Array.from(currentRow.querySelectorAll('input:not([readonly]), select'));
            const currentIndexInRow = focusableInRow.indexOf(activeElement);
            const nextIndexInRow = key === 'ArrowRight' ? currentIndexInRow + 1 : currentIndexInRow - 1;

            if (nextIndexInRow >= 0 && nextIndexInRow < focusableInRow.length) {
                targetElement = focusableInRow[nextIndexInRow];
            }
        }

        if (targetElement) {
            targetElement.focus();
            if (targetElement.tagName === 'INPUT' && targetElement.type === 'number') {
                targetElement.select();
            }
        }
    }

    // --- 3. Event Listeners ---
    ui.employeeSelect.addEventListener("change", fetchAndPopulate);
    ui.dateInput.addEventListener("change", fetchAndPopulate);
    ui.addRowBtn.addEventListener("click", () => {
        createRow();
        recalculateTotals();
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given, .price")) {
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            validateDuplicates(e.target);
            const productSelect = e.target;
            const productId = productSelect.value;
            const row = productSelect.closest('tr');
            if (!row) return;

            const priceInput = row.querySelector('.price');
            if (!priceInput) return;

            if (productId) {
                const product = productsMap.get(productId);
                if (product) {
                    priceInput.value = product.price;
                }
            } else {
                priceInput.value = '0.00';
            }
            recalculateTotals();
        }
    });

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            // =========================================
            //  DELETE POPUP ADDED
            // =========================================
            if (confirm("Are you sure you want to delete this row?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });

    ui.tableBody.addEventListener("keydown", handleArrowKeyNavigation);
});
// NO SYNTAX ERROR: No extra '}' at the end.
