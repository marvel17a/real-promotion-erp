/**
 * This is the JavaScript for 'edit_form.html' (was 'morning_edit.html').
 */

document.addEventListener("DOMContentLoaded", () => {
    // --- 1. DOM Element Cache ---
    const ui = {
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: document.getElementById("addRow"),
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

    function createRow(productData = {}) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index"></td>
            <td class="text-start">
                <select name="product_id[]" class="form-select form-select-sm product-dropdown" required>
                    <option value="">-- Select Product --</option>
                    ${productOptionsHtml}
                </select>
                <!-- This hidden input tells the backend this is a NEW item -->
                <input type="hidden" name="item_id[]" value="new_item">
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

    // --- 3. Event Listeners ---
    
    // Run totals once on page load to populate the footer
    recalculateTotals();

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
});
// NO SYNTAX ERROR: No extra '}' at the end.
