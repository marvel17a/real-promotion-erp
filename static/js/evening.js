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
        // Footer IDs matching HTML
        footer: {
            total: getEl('totTotal'), // Total Product Qty
            sold: getEl('totSold'),   // Total Sold
            return: getEl('totReturn'), // Total Return
            remain: getEl('totRemain'), // Total Left
            amount: getEl('totAmount')  // Total Amount
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

        // Format DB Timestamp
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

        // Reset UI
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
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);

            // 1. Check for HTTP Error Codes (404, 500)
            if (!response.ok) {
                throw new Error(`Server Error: ${response.status} ${response.statusText}`);
            }

            // 2. Check content-type to ensure we got JSON, not HTML (which causes the '<' error)
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                const textData = await response.text(); // Read text for debugging
                console.error("Server returned HTML instead of JSON:", textData);
                throw new Error("Server returned an HTML page (likely an error or login page) instead of data.");
            }

            // 3. Safe to parse JSON
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            if(ui.hidden.allocationId) ui.hidden.allocationId.value = data.allocation_id;
            
            if(ui.fetchMsg) {
                ui.fetchMsg.classList.remove('d-none');
                if(data.allocation_date && data.allocation_date !== dateStr) {
                    ui.fetchMsg.innerHTML = `<i class="fa-solid fa-clock-rotate-left me-2"></i> Fetched pending allocation from: ${data.allocation_date}`;
                    ui.fetchMsg.className = "alert alert-warning mt-3 rounded-3 border-0 shadow-sm fw-bold";
                } else {
                    ui.fetchMsg.innerHTML = '<i class="fa-solid fa-check-circle me-2"></i> Data loaded successfully';
                    ui.fetchMsg.className = "alert alert-success mt-3 rounded-3 border-0 shadow-sm fw-bold";
                }
            }
            
            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-warning p-4 fw-bold">No items allocated to this employee on this date.</td></tr>';
                return;
            }

            renderTable(data.items);

        } catch (error) {
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger p-4 fw-bold">${error.message}</td></tr>`;
            if(ui.fetchMsg) {
                ui.fetchMsg.classList.remove('d-none');
                ui.fetchMsg.textContent = error.message;
                ui.fetchMsg.className = "alert alert-danger mt-3 rounded-3 border-0 shadow-sm fw-bold";
            }
        }
    }

    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        
        items.forEach((item, index) => {
            const totalQty = parseInt(item.total_qty);
            const price = parseFloat(item.unit_price);
            
            let imgSrc = item.image || DEFAULT_IMG;

            const rowHtml = `
                <tr class="item-row">
                    <td class="ps-4 text-muted fw-bold">${index + 1}</td>
                    <td>
                         <div class="table-img-box">
                            <img src="${imgSrc}" class="product-thumb" alt="img" onerror="this.src='${DEFAULT_IMG}'">
                        </div>
                    </td>
                    <td>
                        <div class="fw-bold text-dark">${item.product_name}</div>
                        <input type="hidden" name="product_id[]" value="${item.product_id}">
                        <input type="hidden" name="total_qty[]" value="${totalQty}">
                        <input type="hidden" name="price[]" class="price-input" value="${price.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <span class="badge bg-secondary fs-6 text-white">${totalQty}</span>
                    </td>
                    <td>
                        <input type="number" name="sold[]" class="form-control sold" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td>
                        <input type="text" class="form-control-plaintext text-end fw-bold" value="${price.toFixed(2)}" readonly>
                    </td>
                    <td class="text-end fw-bold text-primary amount-display fs-5">0.00</td>
                    <td>
                        <input type="number" name="return[]" class="form-control return" min="0" max="${totalQty}" placeholder="0">
                    </td>
                    <td class="text-center">
                        <input type="number" name="remaining[]" class="form-control-plaintext text-center fw-bold text-warning remain-input" 
                               value="${totalQty}" readonly>
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
        // Handle rows if rendered from backend (server-side template)
        const allRows = ui.tableBody.querySelectorAll('tr');

        allRows.forEach(row => {
            // Check if it's a valid data row (has inputs)
            if(!row.querySelector('input[name="total_qty[]"]')) return;

            const totalQty = parseInt(row.querySelector('input[name="total_qty[]"]').value) || 0;
            const price = parseFloat(row.querySelector('.price-input, .unit-price').value) || 0;
            
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            const remainInput = row.querySelector('.remain-input, .remaining-qty');
            const amountDisplay = row.querySelector('.amount-display, .row-amount');
            
            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Logic: Left = Total - Sold - Return.
            let remaining = totalQty - sold - ret;

            // Prevent negative remaining
            if (remaining < 0) {
                remaining = 0; 
                // Note: Logic here simply floors remaining at 0 for visual calculation
                // Ideally, you add validation to stop input if (sold + return > total)
            }
            
            if(remainInput.tagName === 'INPUT') {
                remainInput.value = remaining;
            } else {
                remainInput.textContent = remaining;
            }

            const revenue = sold * price;
            
            if(amountDisplay.tagName === 'INPUT') {
                 // if it's an input? usually it's text
            } else {
                 amountDisplay.textContent = revenue.toFixed(2);
            }

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
});
