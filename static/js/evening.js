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
        },

        form: getEl('eveningForm'),
        msg: getEl('fetchMsg')
    };

    // ================= CLOCK =================
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        const clockEl = getEl('liveClock');
        if(clockEl) clockEl.textContent = timeString;

        const tsInput = getEl('timestampInput');
        if(tsInput) tsInput.value = now.toISOString().slice(0,19).replace('T',' ');
    }
    setInterval(updateClock, 1000);
    updateClock();

    if (!ui.fetchButton) return;

    // ================= FETCH =================
    async function fetchMorningAllocation() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;

        ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center p-4"><div class="spinner-border text-primary"></div></td></tr>';
        ui.msg.textContent = "";

        if (!empId || !dateVal) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center fw-bold">Select Employee & Date</td></tr>';
            return;
        }

        try {
            const fd = new FormData();
            fd.append('employee_id', empId);
            fd.append('date', dateVal);

            const res = await fetch('/api/fetch_evening_data', { method:'POST', body:fd });
            const data = await res.json();

            if (data.status === 'success') {

                renderTable(data.products, data.source);

                ui.hidden.allocationId.value = data.allocation_id || '';
                ui.hidden.employee.value = empId;

                const [y,m,d] = dateVal.split('-');
                ui.hidden.date.value = `${y}-${m}-${d}`;

                // --------- DRAFT LOAD ---------
                if (data.source === 'draft' && data.draft_data) {
                    const dft = data.draft_data;

                    getEl('draft_id').value = data.draft_id || '';

                    ui.payment.discount.value = dft.discount || '';
                    ui.payment.cash.value = dft.cash_money || '';
                    ui.payment.online.value = dft.online_money || '';

                    getEl('emp_credit_amount').value = dft.emp_credit_amount || '';
                    getEl('emp_credit_note').value = dft.emp_credit_note || '';
                    getEl('emp_debit_amount').value = dft.emp_debit_amount || '';
                    getEl('emp_debit_note').value = dft.emp_debit_note || '';
                } else {
                    getEl('draft_id').value = '';
                }

                ui.form.classList.remove('d-none');
                calculateDue();
            } 
            else {
                throw new Error(data.message || 'Fetch failed');
            }

        } catch (err) {
            ui.tableBody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">${err.message}</td></tr>`;
        }
    }

    // ================= RENDER TABLE (REPLACED) =================
    function renderTable(products, source) {
        ui.tableBody.innerHTML = "";

        let badgeClass = 'bg-success';
        let badgeText = 'Loaded Morning Allocation';

        if (source === 'previous_leftover') {
            badgeClass = 'bg-info text-dark';
            badgeText = 'Loaded Previous Remaining Stock';
        } 
        else if (source === 'draft') {
            badgeClass = 'bg-warning text-dark';
            badgeText = 'Draft Mode - Resumed';
        }

        ui.msg.innerHTML = `<span class="badge ${badgeClass} mb-2">${badgeText}</span>`;

        products.forEach(p => {
            const soldVal = p.sold_qty > 0 ? p.sold_qty : '';
            const retVal  = p.return_qty > 0 ? p.return_qty : '';

            const row = document.createElement('tr');
            row.classList.add('item-row');

            row.innerHTML = `
                <td>${p.name}<input type="hidden" name="product_id[]" value="${p.product_id}"></td>
                <td class="text-center"><input type="text" name="total_qty[]" class="total-qty" value="${p.total_qty}" readonly></td>
                <td><input type="number" name="sold[]" class="sold" value="${soldVal}"></td>
                <td><input type="number" name="return[]" class="return" value="${retVal}"></td>
                <td class="text-end">₹${p.unit_price}<input type="hidden" class="price-input" value="${p.unit_price}"></td>
                <td class="text-end fw-bold amount-display">0.00</td>
            `;
            ui.tableBody.appendChild(row);
        });

        recalculateTotals();
    }

    // ================= TOTALS =================
    function recalculateTotals() {
        let gAmount = 0;
        document.querySelectorAll('.item-row').forEach(r => {
            const sold = parseInt(r.querySelector('.sold')?.value)||0;
            const price = parseFloat(r.querySelector('.price-input')?.value)||0;
            const amt = sold * price;
            r.querySelector('.amount-display').textContent = amt.toFixed(2);
            gAmount += amt;
        });
        ui.payment.totalAmount.value = gAmount.toFixed(2);
        calculateDue();
    }

    // ================= DUE =================
    function calculateDue() {
        const total = parseFloat(ui.payment.totalAmount.value)||0;
        const d = parseFloat(ui.payment.discount.value)||0;
        const c = parseFloat(ui.payment.cash.value)||0;
        const o = parseFloat(ui.payment.online.value)||0;
        ui.payment.due.textContent = (total - (d+c+o)).toFixed(2);
    }

    // ================= EVENTS =================
    ui.fetchButton.addEventListener('click', e => {
        e.preventDefault();
        fetchMorningAllocation();
    });

    ui.tableBody.addEventListener('input', e => {
        if(e.target.matches('.sold,.return')) recalculateTotals();
    });

    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el=>{
        if(el) el.addEventListener('input', calculateDue);
    });

});

/* ================= SAVE / FINAL ================= */

window.saveDraft = function(event) {
    getEl('formStatus').value = 'draft';
    const btn = event.target;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saving...';
    document.getElementById('eveningForm').submit();
};

window.submitFinal = function() {
    getEl('formStatus').value = 'final';

    const total = parseFloat(getEl('totalAmount').value)||0;
    if(total === 0 && !confirm('Total is 0. Submit anyway?')) return;

    if(confirm('FINAL SUBMIT?\nThis will lock data and update inventory.')) {
        document.getElementById('eveningForm').submit();
    }
};
