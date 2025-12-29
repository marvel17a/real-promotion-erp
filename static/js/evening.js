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
    
    if(ui.payment.totalAmount && ui.payment.totalAmount.value > 0) {
        calculateDue();
        recalculateTotals();
    }

    if (!ui.fetchButton) return;

    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    async function fetchMorningAllocation() {
        const employeeId = ui.employeeSelect.value;
        const dateStr = ui.dateInput.value;

        if(!employeeId) {
            alert("Please select an employee first.");
            return;
        }

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
                
                ui.hidden.allocationId.value = data.allocation_id;
                ui.hidden.employee.value = employeeId;
                ui.hidden.date.value = dateStr;

                ui.tableBody.innerHTML = '';
                data.products.forEach((p, index) => {
                    const row = document.createElement('tr');
                    
                    const imgUrl = p.image && p.image !== 'None' ? p.image : '/static/img/no-img.png';

                    // VALIDATION ADDED: sold/return limited to 3 digits
                    row.innerHTML = `
                        <td class="ps-4 text-muted row-index">${index + 1}</td>
                        <td>
                            <div class="img-box-small">
                                <img src="${imgUrl}" class="img-fixed-size" onerror="this.src='/static/img/no-img.png'">
                            </div>
                        </td>
                        <td class="fw-bold text-dark">
                            ${p.name}
                            <input type="hidden" name="product_id[]" value="${p.id}">
                        </td>
                        <td class="text-center">
                            <span class="total-box">${p.total_qty}</span>
                            <input type="hidden" name="total_qty[]" class="total-qty" value="${p.total_qty}">
                        </td>
                        <td>
                            <input type="number" name="sold[]" class="table-input sold" placeholder="0" min="0" max="999"
                                   oninput="if(this.value.length > 3) this.value = this.value.slice(0, 3);">
                        </td>
                        <td>
                            <input type="number" name="price[]" class="form-control-plaintext text-end fw-bold unit-price" value="${p.price}" readonly>
                        </td>
                        <td class="text-end fw-bold text-primary row-amount">0.00</td>
                        <td>
                            <input type="number" name="return[]" class="table-input return" placeholder="0" min="0" max="999"
                                   oninput="if(this.value.length > 3) this.value = this.value.slice(0, 3);">
                        </td>
                        <td class="text-center text-muted remaining-qty fw-bold">${p.total_qty}</td>
                    `;
                    ui.tableBody.appendChild(row);
                });
                recalculateTotals();

            } else {
                ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-5 text-danger fw-bold">${data.message}</td></tr>`;
                ui.hidden.allocationId.value = "";
            }
        } catch (error) {
            console.error("Error:", error);
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-5 text-danger fw-bold">Network Error or Server Issue.</td></tr>`;
        }
    }

    function recalculateTotals() {
        let gTotal = 0, gSold = 0, gReturn = 0, gRemain = 0, gAmount = 0;

        const rows = ui.tableBody.querySelectorAll('tr');
        rows.forEach(row => {
            if(!row.querySelector('.sold')) return;

            const total = parseInt(row.querySelector('.total-qty').value) || 0;
            const price = parseFloat(row.querySelector('.unit-price').value) || 0;
            
            let sold = parseInt(row.querySelector('.sold').value) || 0;
            let ret = parseInt(row.querySelector('.return').value) || 0;

            let remain = total - sold - ret;
            if (remain < 0) {
               // Optional: visual warning handled via CSS or kept negative
            } 

            const remainEl = row.querySelector('.remaining-qty');
            remainEl.textContent = remain;
            if(remain < 0) remainEl.classList.add('text-danger');
            else remainEl.classList.remove('text-danger');
            
            const amount = sold * price;
            row.querySelector('.row-amount').textContent = amount.toFixed(2);

            gTotal += total;
            gSold += sold;
            gReturn += ret;
            gRemain += remain;
            gAmount += amount;
        });

        if(ui.footer.total) ui.footer.total.textContent = gTotal;
        if(ui.footer.sold) ui.footer.sold.textContent = gSold;
        if(ui.footer.return) ui.footer.return.textContent = gReturn;
        if(ui.footer.remain) ui.footer.remain.textContent = gRemain;
        if(ui.footer.amount) ui.footer.amount.textContent = gAmount.toFixed(2);

        if(ui.payment.totalAmount) {
            ui.payment.totalAmount.value = gAmount.toFixed(2);
            calculateDue(); 
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
        
        const sticky = document.getElementById('stickyDue');
        if(sticky) sticky.innerText = due.toFixed(2);
    }

    ui.fetchButton.addEventListener("click", (e) => {
        e.preventDefault();
        fetchMorningAllocation();
    });
    
    ui.tableBody.addEventListener('input', e => {
        if (e.target.matches('.sold, .return')) recalculateTotals();
    });
    
    // Validation for money inputs
    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) {
            el.addEventListener('input', calculateDue);
            el.setAttribute("oninput", "if(this.value.length > 8) this.value = this.value.slice(0, 8); calculateDue()");
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
        }
    });
});
