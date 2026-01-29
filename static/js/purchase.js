document.addEventListener("DOMContentLoaded", () => {
    // Safely parse the product data passed from the backend
    const productsData = JSON.parse(document.getElementById('products-data').textContent);
    
    const tableBody = document.querySelector("#itemsTable tbody"); // Updated selector ID
    const addRowBtn = document.getElementById("addRowBtn");
    const grandTotalEl = document.getElementById("grandTotal");

    // Pre-build the HTML for the product options dropdown
    const productOptionsHtml = '<option value="" disabled selected>Select Product</option>' +
        productsData.map(p => 
            `<option value="${p.id}" data-price="${p.purchase_price || 0}">${p.name}</option>`
        ).join('');

    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="ps-4">
                <select name="product_id[]" class="form-select input-glass product-select" required>
                    ${productOptionsHtml}
                </select>
            </td>
            <td>
                <input type="number" name="quantity[]" class="form-control input-glass quantity" value="1" min="1" required>
            </td>
            <td>
                <div class="input-group">
                    <span class="input-group-text border-0 bg-transparent text-muted">₹</span>
                    <input type="number" name="price[]" class="form-control input-glass border-start-0 ps-0 price" value="0.00" step="0.01" required>
                </div>
            </td>
            <td class="text-end pe-4 align-middle fw-bold text-dark total-cell">₹0.00</td>
            <td class="align-middle text-center">
                <button type="button" class="btn btn-link text-danger p-0 remove-row">
                    <i class="fa-solid fa-times"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
        calculateTotals();
    }

    tableBody.addEventListener("click", e => {
        if (e.target.closest(".remove-row")) {
            e.target.closest("tr").remove();
            calculateTotals();
        }
    });

    tableBody.addEventListener("change", e => {
        const selectElement = e.target;
        if (selectElement.classList.contains("product-select")) {
            const selectedOption = selectElement.options[selectElement.selectedIndex];
            const price = parseFloat(selectedOption.dataset.price) || 0;
            // Auto-fill price input with the Last Purchase Price
            selectElement.closest("tr").querySelector(".price").value = price.toFixed(2);
            calculateTotals();
        }
    });

    tableBody.addEventListener("input", e => {
        if (e.target.matches(".quantity, .price")) {
            calculateTotals();
        }
    });

    function calculateTotals() {
        let grandTotal = 0;
        document.querySelectorAll("#itemsTable tbody tr").forEach(row => {
            const qty = parseFloat(row.querySelector(".quantity").value) || 0;
            const price = parseFloat(row.querySelector(".price").value) || 0;
            const total = qty * price;
            
            row.querySelector(".total-cell").textContent = '₹' + total.toFixed(2);
            grandTotal += total;
        });
        if(grandTotalEl) grandTotalEl.textContent = '₹' + grandTotal.toFixed(2);
    }
    
    if (addRowBtn) addRowBtn.addEventListener("click", createRow);

    // Initial Row
    if(tableBody && tableBody.children.length === 0) createRow();
});
