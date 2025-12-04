document.addEventListener("DOMContentLoaded", () => {
    const ui = {
        employeeSelect: document.getElementById("employee"),
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
            total: document.getElementById('totTotal'),
            sold: document.getElementById('totSold'),
            return: document.getElementById('totReturn'),
            remain: document.getElementById('totRemain'),
            amount: document.getElementById('totAmount')
        },
        payment: {
            totalAmount: document.getElementById('totalAmount'),
            online: document.getElementById('online'),
            cash: document.getElementById('cash'),
            discount: document.getElementById('discount'),
            dueAmount: document.getElementById('dueAmount')
        }
    };

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;
        clearTableAndMessages();
        if (!employeeId || !dateStr) {
            ui.fetchMsg.textContent = "Please select an employee and date.";
            return;
        }
        ui.hidden.employee.value = employeeId;
        ui.hidden.date.value = dateStr;
        ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-center p-4">Loading...</td></tr>';
        try {
            const response = await fetch(`/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch data.');
            ui.hidden.allocationId.value = data.allocation_id;
            if (!data.items || data.items.length === 0) {
                ui.fetchMsg.textContent = "No morning allocation found for this selection.";
                return;
            }
            renderTable(data.items);
            ui.fetchMsg.textContent = "Data loaded successfully.";
            ui.fetchMsg.className = "small text-success mt-2";
        } catch (error) {
            ui.fetchMsg.textContent = `Error: ${error.message}`;
            ui.fetchMsg.className = "small text-danger mt-2";
        }
    }

    function renderTable(items) {
        ui.tableBody.innerHTML = '';
        items.forEach((item, index) => {
            const rowHtml = `
                <tr>
                    <td>${index + 1}</td>
                    <td class="text-start">
                        ${item.product_name}
                        <input type="hidden" name="product_id[]" value="${item.product_id}">
                        <input type="hidden" name="total_qty[]" value="${item.total_qty}">
                    </td>
                    <td class="total-cell">${item.total_qty}</td>
                    <td><input type="number" name="sold[]" class="form-control form-control-sm sold" min="0" max="${item.total_qty}" ></td>
                    <td><input type="number" name="return[]" class="form-control form-control-sm return" min="0" max="${item.total_qty}"></td>
                    <td><input type="number" name="remaining[]" class="form-control form-control-sm remain" value="${item.total_qty}" readonly></td>
                    <td>
                        ${parseFloat(item.unit_price).toFixed(2)}
                        <input type="hidden" name="price[]" value="${parseFloat(item.unit_price).toFixed(2)}">
                    </td>
                    <td class="amount">0.00</td>
                </tr>
            `;
            ui.tableBody.insertAdjacentHTML('beforeend', rowHtml);
        });
        recalculateTotals();
    }

    function clearTableAndMessages() {
        ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-muted p-4">Select an employee and date to load allocation.</td></tr>';
        ui.fetchMsg.textContent = '';
        if (ui.hidden.allocationId) ui.hidden.allocationId.value = '';
        recalculateTotals();
    }

    function recalculateTotals() {
        let totTotal = 0, totSold = 0, totReturn = 0, totRemain = 0, totAmount = 0;
        ui.tableBody.querySelectorAll("tr").forEach(row => {
            const total = parseInt(row.querySelector('.total-cell')?.innerText) || 0;
            const soldInput = row.querySelector('.sold');
            const returnInput = row.querySelector('.return');
            if (!soldInput || !returnInput) return;

            let sold = parseInt(soldInput.value) || 0;
            let returned = parseInt(returnInput.value) || 0;

            // --- Validation: Sold + Return cannot exceed Total ---
            if ((sold + returned) > total) {
                returned = total - sold; // Adjust return qty automatically
                if (returned < 0) returned = 0;
                returnInput.value = returned;
                soldInput.classList.add('is-invalid');
                returnInput.classList.add('is-invalid');
            } else {
                soldInput.classList.remove('is-invalid');
                returnInput.classList.remove('is-invalid');
            }

            const price = parseFloat(row.querySelector("input[name='price[]']").value) || 0;
            const remaining = total - sold - returned;
            const rowAmount = sold * price;

            row.querySelector('.remain').value = remaining;
            row.querySelector('.amount').innerText = rowAmount.toFixed(2);

            totTotal += total;
            totSold += sold;
            totReturn += returned;
            totRemain += remaining;
            totAmount += rowAmount;
        });

        ui.footer.total.innerText = totTotal;
        ui.footer.sold.innerText = totSold;
        ui.footer.return.innerText = totReturn;
        ui.footer.remain.innerText = totRemain;
        ui.footer.amount.innerText = totAmount.toFixed(2);
        ui.payment.totalAmount.value = totAmount.toFixed(2);
        calculateDueAmount();
    }

    function calculateDueAmount() {
        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const online = parseFloat(ui.payment.online.value) ||0 ;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const discount = parseFloat(ui.payment.discount.value) || 0;
        const due = total - (online + cash + discount);
        ui.payment.dueAmount.innerText = due.toFixed(2);
    }

    ui.fetchButton.addEventListener("click", fetchMorningAllocation);
    ui.tableBody.addEventListener('input', e => {
        if (e.target.matches('.sold, .return')) {
            recalculateTotals();
        }
    });
    [ui.payment.online, ui.payment.cash, ui.payment.discount].forEach(input => {
        input.addEventListener('input', calculateDueAmount);
    });
});



async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value; // Flatpickr puts the value here

        // Debugging Logs
        console.log("Fetching for:", { employeeId, dateStr });

        ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Loading stock data...</div></td></tr>';
        ui.fetchMsg.textContent = "";

        if (!employeeId || !dateStr) {
            ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted p-4">Please select both Employee and Date.</td></tr>';
            return;
        }

        ui.hidden.employee.value = employeeId;
        ui.hidden.date.value = dateStr;

        try {
            // Fetch Request
            const url = `/api/fetch_morning_allocation?employee_id=${employeeId}&date=${dateStr}`;
            console.log("Request URL:", url);
            
            const response = await fetch(url);
            
            // Check for HTTP errors (like 500 or 404)
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server Error: ${response.status}`);
            }

            const data = await response.json();
            console.log("Data Received:", data); // See if data arrives

            ui.hidden.allocationId.value = data.allocation_id;

            if (!data.items || data.items.length === 0) {
                ui.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-warning p-4 fw-bold">No items found in morning allocation.</td></tr>';
                return;
            }

            renderTable(data.items);
            ui.fetchMsg.className = "small text-success mt-2";
            ui.fetchMsg.textContent = "Data loaded successfully.";

        } catch (error) {
            console.error("Fetch Error:", error);
            ui.tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger p-4">Error: ${error.message}</td></tr>`;
        }
    }
