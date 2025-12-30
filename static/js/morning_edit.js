document.addEventListener("DOMContentLoaded", () => {
    const tableBody = document.querySelector("#productTable tbody");
    const addRowBtn = document.getElementById("addRow");
    
    // Totals Elements
    const totalGivenEl = document.getElementById("totalGiven");
    const totalAllEl = document.getElementById("totalAll");
    const grandTotalEl = document.getElementById("grandTotal");

    // Product Map for quick lookup
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";
    
    if (window.productsData) {
        window.productsData.forEach(p => productsMap.set(String(p.id), p));
    }

    // --- 1. INITIALIZE EXISTING ROWS ---
    // Recalculate totals on load to ensure accuracy
    recalculateTotals();

    // --- 2. ADD ROW ---
    addRowBtn.addEventListener("click", () => {
        const tr = document.createElement("tr");
        tr.classList.add("item-row");
        
        tr.innerHTML = `
            <td class="text-center text-muted fw-bold row-index"></td>
            <td>
                <div class="prod-img-box">
                    <img src="${DEFAULT_IMG}" class="product-thumb">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select product-dropdown table-input" required>
                    <option value="">-- Select --</option>
                    ${window.productOptions}
                </select>
                <input type="hidden" name="item_id[]" value="new_item">
            </td>
            <td><input type="number" name="opening[]" class="table-input opening" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="given[]" class="table-input given input-qty" min="0" value="0" required></td>
            <td><input type="number" name="total[]" class="table-input total" value="0" readonly tabindex="-1"></td>
            <td><input type="number" name="price[]" class="table-input price text-end" step="0.01" value="0.00" readonly tabindex="-1"></td>
            <td><input type="number" name="amount[]" class="table-input amount text-end fw-bold text-primary" value="0.00" readonly tabindex="-1"></td>
            <td class="text-center">
                <button type="button" class="btn btn-sm text-danger btn-remove-row"><i class="fa-solid fa-trash-can fa-lg"></i></button>
            </td>
        `;
        tableBody.appendChild(tr);
        updateRowIndexes();
    });

    // --- 3. EVENT DELEGATION ---
    tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if (confirm("Remove this item?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });

    tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            const row = e.target.closest("tr");
            const productId = e.target.value;
            const product = productsMap.get(productId);
            
            const priceInput = row.querySelector(".price");
            const img = row.querySelector(".product-thumb");

            if (product) {
                priceInput.value = parseFloat(product.price).toFixed(2);
                img.src = product.image || DEFAULT_IMG;
            } else {
                priceInput.value = "0.00";
                img.src = DEFAULT_IMG;
            }
            recalculateRow(row);
        }
    });

    tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            recalculateRow(e.target.closest("tr"));
        }
    });

    // --- 4. CALCULATIONS ---
    function recalculateRow(row) {
        const opening = parseInt(row.querySelector(".opening").value) || 0;
        const given = parseInt(row.querySelector(".given").value) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;

        const total = opening + given;
        const amount = total * price;

        row.querySelector(".total").value = total;
        row.querySelector(".amount").value = amount.toFixed(2);
        
        recalculateTotals();
    }

    function recalculateTotals() {
        let tGiven = 0, tAll = 0, tGrand = 0;
        
        tableBody.querySelectorAll("tr").forEach(row => {
            const given = parseInt(row.querySelector(".given").value) || 0;
            const total = parseInt(row.querySelector(".total").value) || 0;
            const amount = parseFloat(row.querySelector(".amount").value) || 0;

            tGiven += given;
            tAll += total;
            tGrand += amount;
        });

        if(totalGivenEl) totalGivenEl.textContent = tGiven;
        if(totalAllEl) totalAllEl.textContent = tAll;
        if(grandTotalEl) grandTotalEl.textContent = tGrand.toFixed(2);
    }

    function updateRowIndexes() {
        tableBody.querySelectorAll("tr").forEach((tr, i) => {
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }
});
