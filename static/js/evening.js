document.addEventListener("DOMContentLoaded", () => {
    
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee"), 
        dateInput: getEl("date"),
        fetchButton: getEl("btnFetch"),
        tableBody: getEl("rowsArea"),
        fetchMsg: getEl("fetchMsg"),
        hidden: {
            allocationId: getEl('allocation_id'),
            employee: getEl('h_employee'),
            date: getEl('h_date'),
        },
        footer: {
            total: getEl('totTotal'),
            sold: getEl('totSold'),
            return: getEl('totReturn'),
            remain: getEl('totRemain'),
            amount: getEl('totAmount')
        },
        payment: {
            totalAmount: getEl('totalAmount'),
            discount: getEl('discount'),
            cash: getEl('cash'),
            online: getEl('online'),
            due: getEl('dueAmount')
        }
    };
    
    // Only proceed if elements exist
    if (!ui.fetchButton) return;

    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        // Loading State
        ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Loading Data...</p></td></tr>';
        if(ui.fetchMsg) ui.fetchMsg.textContent = "";

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted p-5 fw-bold">Please Select Employee and Date first.</td></tr>';
            return;
        }

        if(ui.hidden.employee) ui.hidden.employee.value = employeeId;
        if(ui.hidden.date) ui.hidden.date.value = dateStr;

        try {
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (!response.ok || data.error) throw new Error(data.error || 'No data found for this selection.');

            if(ui.hidden.allocationId) ui.hidden.allocationId.value = data.allocation_id;
            
            // Show status message regarding date
            if(data.allocation_date && data.allocation_date !== dateStr) {
                ui.fetchMsg.innerHTML = `<span class="badge bg-warning text-dark"><i class="fa-solid fa-clock-rotate-left"></i> Fetched pending allocation from: ${data.allocation_date}</span>`;
            } else {
                ui.fetchMsg.innerHTML = '<span class="badge bg-success"><i class="fa-solid fa-check"></i> Data Loaded Successfully</span>';
            }
            
            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-warning p-5 fw-bold">No items found for this allocation.</td></tr>';
                return;
            }

            renderTable(data.items);

        } catch (error) {
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger p-5 fw-bold"><i class="fa-solid fa-circle-exclamation me-2"></i>${error.message}</td></tr>`;
            if(ui.fetchMsg) ui.fetchMsg.innerHTML = `<span class="text-danger">${error.message}</span>`;
        }
    }

    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach((item, index) => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.unit_price);
            
            let imgSrc = item.image || DEFAULT_IMG;

            const rowHtml = `
                <tr class="item-row fade-in">
                    <td class="ps-4 text-muted fw-bold">${index + 1}</td>
                    <td class="text-center">
                        <img src="${imgSrc}" class="img-thumbnail-custom" onerror="this.src='${DEFAULT_IMG}'">
                    </td>
                    <td>
                        <div class="fw-bold text-dark">${item.product_name}</div>
                        <input type="hidden" name="product_id[]" value="${item.product_id}">
                        <input type="hidden" name="total_qty[]" value="${totalQty}">
                        <input type="hidden" name="price[]" class="price-input" value="${price.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border px-3 py-2 rounded-pill fs-6">${totalQty}</span>
                    </td>
                    <td class="text-center">
                        <input type="number" name="sold[]" class="table-input sold" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td class="text-end">
                        <span class="text-muted">${price.toFixed(2)}</span>
                    </td>
                    <td class="text-end fw-bold text-primary amount-display">0.00</td>
                    <td class="text-center">
                        <input type="number" name="return[]" class="table-input return" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td class="text-center">
                        <span class="remain-text fw-bold text-secondary">0</span>
                        <input type="hidden" name="remaining[]" class="remain-input" value="${totalQty}">
                    </td>
                </tr>
            `;
            ui.tableBody.insertAdjacentHTML('beforeend', rowHtml);
        });

        recalculateTotals();
    }

    function recalculateTotals() {
        let gTotal = 0, gSold = 0, gReturn = 0, gRemain = 0, gAmount = 0;
        const rows = ui.tableBody.querySelectorAll('.item-row');

        rows.forEach(row => {
            const totalQty = parseInt(row.querySelector('input[name="total_qty[]"]').value) || 0;
            const price = parseFloat(row.querySelector('.price-input').value) || 0;
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            const remainInput = row.querySelector('.remain-input');
            const remainText = row.querySelector('.remain-text');
            
            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Logic: Sold + Return cannot exceed Total. 
            // If user types too much, we prioritize Sold, then adjust Return.
            if ((sold + ret) > totalQty) {
                // Adjust Return to fit
                ret = totalQty - sold;
                if(ret < 0) { sold = totalQty; ret = 0; }
                
                // Update UI inputs
                // Note: We avoid aggressive overwriting while typing, but strictly enforce limits on blur/calculation
                soldInput.value = sold || '';
                returnInput.value = ret || '';
            }

            const revenue = sold * price;
            const remaining = totalQty - sold - ret; // Should be 0 usually if fully accounted, or >0 if lost? 
            // Actually usually Morning = Sold + Return. So Remaining = Morning - (Sold + Return).
            
            if(remainInput) remainInput.value = remaining;
            if(remainText) remainText.textContent = remaining;
            
            row.querySelector('.amount-display').textContent = revenue.toFixed(2);

            gTotal += totalQty;
            gSold += sold;
            gReturn += ret;
            gRemain += remaining;
            gAmount += revenue;
        });

        if(ui.footer.total) ui.footer.total.textContent = gTotal;
        if(ui.footer.sold) ui.footer.sold.textContent = gSold;
        if(ui.footer.return) ui.footer.return.textContent = gReturn;
        if(ui.footer.remain) ui.footer.remain.textContent = gRemain;
        if(ui.footer.amount) ui.footer.amount.textContent = gAmount.toFixed(2);
        
        if(ui.payment.totalAmount) ui.payment.totalAmount.value = gAmount.toFixed(2);
        
        calculateDue();
    }

    function calculateDue() {
        if(!ui.payment.totalAmount) return;

        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const disc = parseFloat(ui.payment.discount?.value) || 0;
        const cash = parseFloat(ui.payment.cash?.value) || 0;
        const online = parseFloat(ui.payment.online?.value) || 0;
        
        // Due = Total - (Discount + Cash + Online)
        const due = total - (disc + cash + online);
        
        if(ui.payment.due) ui.payment.due.textContent = due.toFixed(2);
    }

    // --- Event Listeners ---

    ui.fetchButton.addEventListener("click", (e) => {
        e.preventDefault();
        fetchMorningAllocation();
    });
    
    // Use delegation for table inputs
    ui.tableBody.addEventListener('input', e => {
        if (e.target.matches('.sold, .return')) {
            recalculateTotals();
        }
    });
    
    // Finance Inputs
    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) el.addEventListener('input', calculateDue);
    });

    // Enter key navigation
    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON" && e.target.tagName !== "TEXTAREA") {
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll("input:not([readonly]), select"));
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        }
    });
    
    // Initial Calc in case data exists (Edit Mode)
    if(ui.payment.totalAmount && parseFloat(ui.payment.totalAmount.value) > 0) {
        calculateDue();
    }
});
