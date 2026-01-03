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
    
    // Live Clock Logic
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        const clockEl = getEl('liveClock');
        if(clockEl) clockEl.textContent = timeString;

        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const tsInput = getEl('timestampInput');
        if(tsInput) tsInput.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    setInterval(updateClock, 1000);
    updateClock();


    if (!ui.fetchButton) return;

    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center p-4"><div class="spinner-border text-primary" role="status"></div></td></tr>';
        if(ui.fetchMsg) {
            ui.fetchMsg.textContent = "";
            ui.fetchMsg.classList.add('d-none');
        }

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted p-4 fw-bold">Please Select Employee and Date first.</td></tr>';
            return;
        }

        if(ui.hidden.employee) ui.hidden.employee.value = employeeId;
        if(ui.hidden.date) ui.hidden.date.value = dateStr;

        try {
            const formData = new FormData();
            formData.append('employee_id', employeeId);
            formData.append('date', dateStr);

               const response = await fetch(`/api/get_evening_stock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        employee_id: employeeId,
        date: dateStr
    })
});


            if (!response.ok) {
                throw new Error(`Server Error: ${response.status}`);
            }

            const data = await response.json();

      if (data.status === 'submitted') {
    ui.fetchMsg.classList.remove('d-none');
    ui.fetchMsg.className = "alert alert-warning mt-3 fw-bold text-center";
    ui.fetchMsg.innerHTML = "Evening settlement already submitted for this date.";
    ui.tableBody.innerHTML = '';
    return;
}



            if(ui.hidden.allocationId) ui.hidden.allocationId.value = data.allocation_id;
            
            if(ui.fetchMsg) {
                ui.fetchMsg.classList.remove('d-none');
                ui.fetchMsg.innerHTML = '<i class="fa-solid fa-check-circle me-2"></i> Data loaded successfully';
                ui.fetchMsg.className = "alert alert-success mt-3 rounded-3 border-0 shadow-sm fw-bold text-center";
            }
            
          if (!Array.isArray(data.items) || data.items.length === 0) {
    ui.tableBody.innerHTML = `
        <tr>
            <td colspan="9" class="text-center text-warning p-4 fw-bold">
                No items available for this employee on selected date.
            </td>
        </tr>
    `;
    return;
}


           // MERGE DUPLICATES (Fix for restock mode)
// BACKEND RETURNS `items`, NOT `products`
const mergedProducts = mergeDuplicateProducts(data.items);
renderTable(mergedProducts);


        } catch (error) {
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger p-4 fw-bold">${error.message}</td></tr>`;
            if(ui.fetchMsg) {
                ui.fetchMsg.classList.remove('d-none');
                ui.fetchMsg.textContent = error.message;
                ui.fetchMsg.className = "alert alert-danger mt-3 rounded-3 border-0 shadow-sm fw-bold text-center";
            }
        }
    }

  function mergeDuplicateProducts(products) {
    if (!Array.isArray(products)) return [];

    const map = new Map();

    products.forEach(item => {
        const id = String(item.product_id ?? item.id);

        if (map.has(id)) {
            const existing = map.get(id);
            existing.total_qty =
                (parseInt(existing.total_qty) || 0) +
                (parseInt(item.total_qty) || 0);
        } else {
            map.set(id, {
                ...item,
                id: item.product_id ?? item.id,
                total_qty: parseInt(item.total_qty) || 0
            });
        }
    });

    return Array.from(map.values());
}


    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach((item, index) => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.price);
            
            let imgSrc = item.image || DEFAULT_IMG;

            const rowHtml = `
                <tr class="item-row">
                    <td class="text-center text-muted fw-bold">${index + 1}</td>
                    <td>
                         <div class="prod-img-box">
                            <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
                        </div>
                    </td>
                    <td>
                        <div class="fw-bold text-dark">${item.name}</div>
                        <input type="hidden" name="product_id[]" value="${item.id}">
                        <input type="hidden" name="total_qty[]" class="total-qty-input" value="${totalQty}">
                        <input type="hidden" name="price[]" class="price-input" value="${price.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <input type="text" class="table-input" value="${totalQty}" readonly style="background:transparent; border:none; box-shadow:none;">
                    </td>
                    <td>
                        <input type="number" name="sold[]" class="table-input sold input-sold" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td>
                        <input type="text" class="table-input text-end fw-bold" value="${price.toFixed(2)}" readonly style="background:transparent; border:none; box-shadow:none;">
                    </td>
                    <td class="text-end fw-bold text-primary amount-display fs-5">0.00</td>
                    <td>
                        <input type="number" name="return[]" class="table-input return input-return" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td class="text-center">
                        <input type="number" name="remaining[]" class="table-input text-center fw-bold text-muted remain-input" 
                               value="${totalQty}" readonly style="background:transparent; border:none; box-shadow:none;">
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
            const totalQtyInput = row.querySelector('input[name="total_qty[]"]');
            if(!totalQtyInput) return;

            const totalQty = parseInt(totalQtyInput.value) || 0;
            const price = parseFloat(row.querySelector('.price-input').value) || 0;
            
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            const remainInput = row.querySelector('.remain-input');
            const amountDisplay = row.querySelector('.amount-display');
            
            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Strict Validation
            if (sold > totalQty) {
                alert(`Sold quantity cannot exceed Total Stock (${totalQty}).`);
                sold = totalQty;
                soldInput.value = totalQty;
            }
            if ((sold + ret) > totalQty) {
                ret = totalQty - sold;
                returnInput.value = ret;
            }

            let remaining = totalQty - sold - ret;
            
            remainInput.value = remaining;
            const revenue = sold * price;
            amountDisplay.textContent = revenue.toFixed(2);

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

    // CASH SETTLEMENT VALIDATION FIX
    function calculateDue(e) {
        if(!ui.payment.totalAmount) return;

        const totalSales = parseFloat(ui.payment.totalAmount.value) || 0;
        let disc = parseFloat(ui.payment.discount?.value) || 0;
        let cash = parseFloat(ui.payment.cash?.value) || 0;
        let online = parseFloat(ui.payment.online?.value) || 0;

        // Validation: Prevent overpayment
        const totalPay = disc + cash + online;
        if (totalPay > totalSales) {
            // If triggered by input event, correct the current input
            if(e && e.target) {
                const currentInput = e.target;
                const otherSum = totalPay - (parseFloat(currentInput.value) || 0);
                const maxAllowed = totalSales - otherSum;
                
                // Correct value
                currentInput.value = maxAllowed.toFixed(2);
                
                // Update variable for calc
                if(currentInput === ui.payment.discount) disc = maxAllowed;
                if(currentInput === ui.payment.cash) cash = maxAllowed;
                if(currentInput === ui.payment.online) online = maxAllowed;
                
                alert(`Payment amount cannot exceed Total Sales Value (₹${totalSales})`);
            }
        }

        const due = totalSales - (disc + cash + online);
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

    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll("input:not([readonly]), select"));
            const index = inputs.indexOf(e.target);
            if (index > -1 && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        }
    });
});




