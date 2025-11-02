document.addEventListener("DOMContentLoaded", () => {
    // Safely parse the product data passed from the backend
    const productsData = JSON.parse(document.getElementById('products-data').textContent);
    
    const tableBody = document.querySelector("#productTable tbody");
    const addRowBtn = document.getElementById("addRowBtn");
    const grandTotalEl = document.getElementById("grandTotal");
    const form = document.getElementById("purchaseForm");

    // Pre-build the HTML for the product options dropdown for efficiency
    // Includes the special "-- Create New Product --" option
    const productOptionsHtml = '<option value="__new__" class="text-primary fw-bold">-- Create New Product --</option>' +
        productsData.map(p => 
            `<option value="${p.id}" data-price="${p.purchase_price || 0}">${p.name}</option>`
        ).join('');

    /**
     * Creates a new, empty row and adds it to the product table.
     */
    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>
                <select name="product_id[]" class="form-select form-select-sm product-select" required>
                    <option value="" selected>-- Select Product --</option>
                    ${productOptionsHtml}
                </select>
                 <div class="invalid-feedback">Please select a product.</div>
            </td>
            <td><input type="number" name="quantity[]" class="form-control form-control-sm quantity" min="1" value="1" required></td>
            <td><input type="number" name="purchase_price[]" class="form-control form-control-sm purchase-price" step="0.01" min="0" required></td>
            <td class="amount text-end fw-bold">₹0.00</td>
            <td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger btn-remove"><i class="fa-solid fa-trash"></i></button></td>
        `;
        tableBody.appendChild(tr);
    }

    /**
     * Calculates the amount for each row and the grand total for the form.
     */
    function calculateTotals() {
        let grandTotal = 0;
        tableBody.querySelectorAll("tr").forEach(row => {
            const quantity = parseFloat(row.querySelector(".quantity").value) || 0;
            const price = parseFloat(row.querySelector(".purchase-price").value) || 0;
            const amount = quantity * price;
            row.querySelector(".amount").textContent = `₹${amount.toFixed(2)}`;
            grandTotal += amount;
        });
        grandTotalEl.textContent = `₹${grandTotal.toFixed(2)}`;
    }

    /**
     * Handles the logic for creating a new product on-the-fly.
     * @param {HTMLSelectElement} selectElement - The dropdown that triggered the event.
     */
    function handleNewProductCreation(selectElement) {
        const newProductName = prompt("Enter the name for the new product:");

        if (newProductName && newProductName.trim() !== "") {
            const trimmedName = newProductName.trim();
            const newOptionValue = `__new__:${trimmedName}`;
            
            // Create a new option and add it to the select
            const newOption = new Option(trimmedName, newOptionValue, true, true);
            selectElement.add(newOption);
            
            // Focus on the quantity field for a better user experience
            selectElement.closest("tr").querySelector(".quantity").focus();
        } else {
            // Reset to default if the user cancels or enters nothing
            selectElement.value = "";
        }
    }

    // --- EVENT LISTENERS ---

    if (addRowBtn) {
        addRowBtn.addEventListener("click", createRow);
    }

    tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove")) {
            e.target.closest("tr").remove();
            calculateTotals();
        }
    });

    tableBody.addEventListener("change", e => {
        const selectElement = e.target;
        if (selectElement.classList.contains("product-select")) {
            // Check if the "Create New" option was selected
            if (selectElement.value === "__new__") {
                handleNewProductCreation(selectElement);
            } else {
                const selectedOption = selectElement.options[selectElement.selectedIndex];
                const price = selectedOption.dataset.price || 0;
                selectElement.closest("tr").querySelector(".purchase-price").value = parseFloat(price).toFixed(2);
            }
            calculateTotals();
        }
    });

    tableBody.addEventListener("input", e => {
        if (e.target.matches(".quantity, .purchase-price")) {
            calculateTotals();
        }
    });
    
    // --- FORM VALIDATION ---
    if (form) {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    }
    
    // --- INITIALIZATION ---
    createRow();
});

