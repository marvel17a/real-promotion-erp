document.addEventListener("DOMContentLoaded", () => {
    
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
    
    const DEFAULT_IMG = "https://via.placeholder.com/40?text=?";

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        ui.tableBody.innerHTML = '<tr><td colspan="7" class="text-center p-4"><div class="spinner-border text-primary" role="status"></div></td></tr>';
        ui.fetchMsg.textContent = "";

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted p-4">Select Employee and Date.</td></tr>';
            return;
        }

        ui.hidden.employee.value = employeeId;
        ui.hidden.date.value = dateStr;

        try {
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();

            if (!response.ok || data.error) throw new Error(data.error || 'No data.');

            ui.hidden.allocationId.value = data.allocation_id;
            
            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-warning p-4 fw-bold">No items found.</td></tr>';
                return;
            }

            renderTable(data.items);
            ui.fetchMsg.innerHTML = '<span class="text-success"><i class="fa-solid fa-check"></i> Data loaded</span>';

        } catch (error) {
            ui.tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger p-4">${error.message}</td></tr>`;
            ui.fetchMsg.textContent = error.message;
            ui.fetchMsg.className = "text-danger";
        }
    }

    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach(item => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.unit_price);
            
            let imgSrc = DEFAULT_IMG;
            if(item.image) {
                imgSrc = item.image.startsWith('http') ? item.image : `/static/uploads/${item.image}`;
            }

            const rowHtml = `
                <tr class="item-row">
                    <td class="ps-4 text-center">
                        <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
                    </td>
                    <td>
                        <div class="fw-bold text-dark text-start">${item.product_name}</div>
                        <input type="hidden" name="product_id[]" value="${item.product_id}">
                        <input type="hidden" name="total_qty[]" value="${totalQty}">
                        <input type="hidden" name="price[]" class="price-input" value="${price.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border px-3 py-2 rounded-pill">${totalQty}</span>
                    </td>
                    <td>
                        <input type="number" name="sold[]" class="form-control sold" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td>
                        <input type="number" name="return[]" class="form-control return" min="0" max="${totalQty}" placeholder="0">
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

    function recalculateTotals() {
        let grandTotalSold = 0, grandTotalAmount = 0;
        const rows = ui.tableBody.querySelectorAll('.item-row');

        rows.forEach(row => {
            const totalQty = parseInt(row.querySelector('input[name="total_qty[]"]').value) || 0;
            const price = parseFloat(row.querySelector('.price-input').value) || 0;
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            const remainInput = row.querySelector('.remain-input');
            
            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            if ((sold + ret) > totalQty) {
                ret = totalQty - sold;
                if(ret < 0) { sold = totalQty; ret = 0; }
                soldInput.value = sold || '';
                returnInput.value = ret || '';
            }

            const revenue = sold * price;
            remainInput.value = totalQty - sold - ret;
            row.querySelector('.amount-display').textContent = revenue.toFixed(2);

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
        const disc = parseFloat(ui.payment.discount.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;
        const due = total - (disc + cash + online);
        ui.payment.due.textContent = due.toFixed(2);
    }

    if(ui.fetchButton) ui.fetchButton.addEventListener("click", fetchMorningAllocation);
    
    ui.tableBody.addEventListener('input', e => {
        if (e.target.matches('.sold, .return')) recalculateTotals();
    });
    
    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) el.addEventListener('input', calculateDue);
    });
});
