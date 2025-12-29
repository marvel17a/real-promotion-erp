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
    
    if (!ui.fetchButton) return;

    // Check if we have draft data loaded (rows exist)
    if (ui.tableBody.querySelectorAll('tr td.row-index').length > 0) {
        recalculateTotals();
        calculateDue();
    }

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center p-5"><div class="spinner-border text-primary"></div></td></tr>';
        
        try {
            const formData = new FormData();
            formData.append('employee_id', employeeId);
            formData.append('date', dateStr);

            const response = await fetch('/api/fetch_evening_data', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                ui.fetchMsg.classList.add('d-none');
                
                // Set Hidden Fields
                ui.hidden.allocationId.value = data.allocation_id;
                ui.hidden.employee.value = employeeId;
                ui.hidden.date.value = dateStr;

                // Build Table Rows - UPDATED ORDER
                ui.tableBody.innerHTML = '';
                data.products.forEach((p, index) => {
                    const row = document.createElement('tr');
                    
                    // Order: #, Img, Product Name, Total, Sold, Price, Amount, Return, Left
                    row.innerHTML = `
                        <td class="ps-4 text-muted row-index">${index + 1}</td>
                        <td>
                            <div class="img-box-small">
                                <img src="${p.image}" class="img-fixed-size" onerror="this.src='/static/img/no-img.png'">
                            </div>
                        </td>
                        <td class="fw-bold text-dark">
                            ${p.name}
                            <input type="hidden" name="product_id[]" value="${p.id}">
                        </td>
                        <td class="text-center">
                            <input type="number" name="total_qty[]" class="form-control-plaintext text-center fw-bold total-qty" value="${p.total_qty}" readonly>
                        </td>
                        <td>
                            <input type="number" name="sold[]" class="form-control sold" placeholder="0" min="0">
                        </td>
                        <td>
                            <input type="number" name="price[]" class="form-control-plaintext text-end unit-price" value="${p.price}" readonly>
                        </td>
                        <td class="text-end fw-bold text-primary row-amount">0.00</td>
                        <td>
                            <input type="number" name="return[]" class="form-control return" placeholder="0" min="0">
                        </td>
                        <td class="text-center text-muted remaining-qty">${p.total_qty}</td>
                    `;
                    ui.tableBody.appendChild(row);
                });
                recalculateTotals();

            } else {
                ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-5 text-danger">${data.message}</td></tr>`;
                ui.hidden.allocationId.value = "";
            }
        } catch (error) {
            console.error("Error:", error);
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-5 text-danger">Error fetching data.</td></tr>`;
        }
    }

    function recalculateTotals() {
        let gTotal = 0, gSold = 0, gReturn = 0, gRemain = 0, gAmount = 0;

        const rows = ui.tableBody.querySelectorAll('tr');
        rows.forEach(row => {
            const total = parseInt(row.querySelector('.total-qty')?.value) || 0;
            const price = parseFloat(row.querySelector('.unit-price')?.value) || 0;
            
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            
            if(!soldInput) return; // Skip if not a data row

            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Logic: Remaining = Total - Sold - Return
            // Prevent negative logic: usually Sold + Return <= Total
            // Auto adjust logic could go here, keeping simple for now
            
            let remain = total - sold - ret;
            if (remain < 0) remain = 0; // Prevent negative stock

            // Update row display
            row.querySelector('.remaining-qty').textContent = remain;
            
            const amount = sold * price;
            row.querySelector('.row-amount').textContent = amount.toFixed(2);

            // Accumulate
            gTotal += total;
            gSold += sold;
            gReturn += ret;
            gRemain += remain;
            gAmount += amount;
        });

        // Update Footer
        if(ui.footer.total) ui.footer.total.textContent = gTotal;
        if(ui.footer.sold) ui.footer.sold.textContent = gSold;
        if(ui.footer.return) ui.footer.return.textContent = gReturn;
        if(ui.footer.remain) ui.footer.remain.textContent = gRemain;
        if(ui.footer.amount) ui.footer.amount.textContent = gAmount.toFixed(2);

        // Update Form Total Field
        if(ui.payment.totalAmount) {
            ui.payment.totalAmount.value = gAmount.toFixed(2);
            calculateDue(); // Trigger Due Calc
        }
    }

    function calculateDue() {
        if(!ui.payment.totalAmount) return;

        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const disc = parseFloat(ui.payment.discount?.value) || 0;
        const cash = parseFloat(ui.payment.cash?.value) || 0;
        const online = parseFloat(ui.payment.online?.value) || 0;
        const due = total - (disc + cash + online);
        
        if(ui.payment.due) ui.payment.due.textContent = due.toFixed(2);
    }

    ui.fetchButton.addEventListener("click", (e) => {
        e.preventDefault();
        fetchMorningAllocation();
    });
    
    ui.tableBody.addEventListener('input', e => {
        if (e.target.matches('.sold, .return')) recalculateTotals();
    });
    
    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) el.addEventListener('input', calculateDue);
    });

    // Disable Enter Key submitting form, move focus instead?
    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
        }
    });
});
