document.addEventListener("DOMContentLoaded", () => {
    
    // 1. UI Elements (Must match HTML IDs)
    const ui = {
        employeeSelect: document.getElementById("employee_id"), 
        dateInput: document.getElementById("date"),
        fetchButton: document.getElementById("btnFetch"),
        tableBody: document.getElementById("rowsArea"),
        fetchMsg: document.getElementById("fetchMsg"),
        
        hidden: {
            allocationId: document.getElementById('allocation_id'),
            employee: document.getElementById('h_employee'),
            date: document.getElementById('h_date'),
        },
        
        footer: {
            sold: document.getElementById('totSold'),
            amount: document.getElementById('totAmount')
        },
        
        payment: {
            totalAmount: document.getElementById('totalAmount'),
            discount: document.getElementById('discount'),
            cash: document.getElementById('cash'),
            online: document.getElementById('online'),
            due: document.getElementById('dueAmount')
        }
    };

    // 2. Fetch Data
    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        // Reset Table
        ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Loading data...</div></td></tr>';
        ui.fetchMsg.textContent = "";
        ui.fetchMsg.className = "mt-2 fw-bold";

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted p-4">Please select Employee and Date.</td></tr>';
            return;
        }

        // Set Hidden Values (CRITICAL for Backend)
        ui.hidden.employee.value = employeeId;
        ui.hidden.date.value = dateStr;

        try {
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'No data found.');
            }

            ui.hidden.allocationId.value = data.allocation_id;

            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-warning p-4 fw-bold">No items allocated this morning.</td></tr>';
                return;
            }

            renderTable(data.items);
            ui.fetchMsg.textContent = "Data loaded successfully.";
            ui.fetchMsg.classList.add("text-success");

        } catch (error) {
            console.error(error);
            ui.tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger p-4">Error: ${error.message}</td></tr>`;
            ui.fetchMsg.textContent = error.message;
            ui.fetchMsg.classList.add("text-danger");
        }
    }

    // 3. Render
    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach(item => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.unit_price);
            
            const rowHtml = `
                <tr class="item-row">
                    <td>
                        <div class="fw-bold text-dark">${item.product_name}</div>
                        <input type="hidden" name="product_id[]" value="${item.product_id}">
                        <input type="hidden" name="total_qty[]" value="${totalQty}">
                        <input type="hidden" name="price[]" class="price-input" value="${price.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border fs-6">${totalQty}</span>
                    </td>
                    <td>
                        <input type="number" name="sold[]" class="form-control form-control-lg text-center fw-bold text-primary sold-input" 
                               min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td>
                        <input type="number" name="return[]" class="form-control form-control-lg text-center text-danger return-input" 
                               min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td class="text-center">
                        <input type="number" name="remaining[]" class="form-control-plaintext text-center fw-bold text-muted remain-input" 
                               value="${totalQty}" readonly>
                    </td>
                    <td class="text-end pe-4">
                        <span class="fw-bold text-dark">₹ <span class="amount-display">0.00</span></span>
                    </td>
                </tr>
            `;
            ui.tableBody.insertAdjacentHTML('beforeend', rowHtml);
        });

        recalculateTotals();
    }

    // 4. Calculations
    function recalculateTotals() {
        let grandTotalSold = 0;
        let grandTotalAmount = 0;

        const rows = ui.tableBody.querySelectorAll('.item-row');

        rows.forEach(row => {
            const totalQty = parseInt(row.querySelector('input[name="total_qty[]"]').value) || 0;
            const price = parseFloat(row.querySelector('.price-input').value) || 0;
            
            const soldInput = row.querySelector('.sold-input');
            const returnInput = row.querySelector('.return-input');
            const remainInput = row.querySelector('.remain-input');
            const amountDisplay = row.querySelector('.amount-display');

            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Logic: Sold + Return cannot exceed Total
            if ((sold + ret) > totalQty) {
                // Adjust Return to fit
                ret = totalQty - sold;
                if(ret < 0) { sold = totalQty; ret = 0; }
                
                soldInput.value = sold || '';
                returnInput.value = ret || '';
            }

            const remaining = totalQty - sold - ret;
            const revenue = sold * price;

            remainInput.value = remaining;
            amountDisplay.textContent = revenue.toFixed(2);

            grandTotalSold += sold;
            grandTotalAmount += revenue;
        });

        ui.footer.sold.textContent = grandTotalSold;
        ui.footer.amount.textContent = grandTotalAmount.toFixed(2);
        
        ui.payment.totalAmount.value = grandTotalAmount.toFixed(2);
        
        calculateDue();
    }

    function calculateDue() {
        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const discount = parseFloat(ui.payment.discount.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;

        const due = total - (discount + cash + online);
        
        ui.payment.due.textContent = due.toFixed(2);
    }

    // 5. Events
    if(ui.fetchButton) ui.fetchButton.addEventListener("click", fetchMorningAllocation);

    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input') || e.target.matches('.return-input')) {
            recalculateTotals();
        }
    });

    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) el.addEventListener('input', calculateDue);
    });
});
