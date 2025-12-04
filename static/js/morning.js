document.addEventListener("DOMContentLoaded", () => {
    
    // 1. UI Elements Cache
    const ui = {
        employeeSelect: document.getElementById("employee"),
        dateInput: document.getElementById("date"),
        fetchButton: document.getElementById("btnFetch"),
        tableBody: document.getElementById("rowsArea"),
        fetchMsg: document.getElementById("fetchMsg"),
        
        // Hidden Fields for Form Submission
        hidden: {
            allocationId: document.getElementById('allocation_id'),
            employee: document.getElementById('h_employee'),
            date: document.getElementById('h_date'),
        },
        
        // Footer Totals
        footer: {
            sold: document.getElementById('totSold'),
            amount: document.getElementById('totAmount')
        },
        
        // Payment Inputs
        payment: {
            totalAmount: document.getElementById('totalAmount'),
            online: document.getElementById('online'),
            cash: document.getElementById('cash'),
            discount: document.getElementById('discount'),
            dueAmount: document.getElementById('dueAmount')
        },

        // Sticky Footer
        stickyDue: document.getElementById('stickyDue')
    };

    // 2. Fetch Data Function
    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        // Reset Table
        ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Loading stock data...</div></td></tr>';
        ui.fetchMsg.textContent = "";

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted p-4">Please select both Employee and Date.</td></tr>';
            return;
        }

        // Set Hidden Values for Submission
        ui.hidden.employee.value = employeeId;
        ui.hidden.date.value = dateStr;

        try {
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (!response.ok) throw new Error(data.error || 'Failed to fetch data.');

            ui.hidden.allocationId.value = data.allocation_id;

            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-warning p-4 fw-bold">No morning allocation found for this date/employee.</td></tr>';
                return;
            }

            renderTable(data.items);
            ui.fetchMsg.className = "small text-success mt-2";
            ui.fetchMsg.textContent = "Data loaded successfully.";

        } catch (error) {
            console.error(error);
            ui.tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger p-4">Error: ${error.message}</td></tr>`;
        }
    }

    // 3. Render Table Rows (Matched to New HTML)
    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach((item, index) => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.unit_price);
            
            const rowHtml = `
                <tr class="item-row">
                    <td class="ps-4">
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
                        <span class="fw-bold text-dark fs-5">₹ <span class="amount-display">0.00</span></span>
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

            // Validation: Cannot exceed total
            if ((sold + ret) > totalQty) {
                // Prioritize Sold, adjust Return
                ret = totalQty - sold;
                if (ret < 0) { 
                    sold = totalQty; 
                    ret = 0; 
                }
                soldInput.value = sold || '';
                returnInput.value = ret || '';
            }

            // Calc Remaining & Amount
            const remaining = totalQty - sold - ret;
            const revenue = sold * price;

            remainInput.value = remaining;
            amountDisplay.textContent = revenue.toFixed(2);

            // Add to Grand Totals
            grandTotalSold += sold;
            grandTotalAmount += revenue;
        });

        // Update Footer
        ui.footer.sold.textContent = grandTotalSold;
        ui.footer.amount.textContent = grandTotalAmount.toFixed(2);
        
        // Update Payment Card
        ui.payment.totalAmount.value = grandTotalAmount.toFixed(2);

        calculateDue();
    }

    function calculateDue() {
        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const discount = parseFloat(ui.payment.discount.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;

        const due = total - (discount + cash + online);
        
        ui.payment.dueAmount.textContent = due.toFixed(2);
        
        // Update Sticky Footer
        if(ui.stickyDue) {
            ui.stickyDue.textContent = due.toFixed(2);
        }
    }

    // 5. Event Listeners
    if(ui.fetchButton) {
        ui.fetchButton.addEventListener("click", fetchMorningAllocation);
    }

    // Delegate Input Events for Table (Performance)
    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input') || e.target.matches('.return-input')) {
            recalculateTotals();
        }
    });

    // Payment Inputs
    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(input => {
        if(input) {
            input.addEventListener('input', calculateDue);
        }
    });

});
