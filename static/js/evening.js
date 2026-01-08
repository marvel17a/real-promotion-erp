document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);
    const ui = {
        empSelect: getEl("employee"), 
        dateInput: getEl("date"),
        fetchBtn: getEl("btnFetch"),
        form: getEl("eveningForm"),
        tableBody: getEl("rowsArea"),
        msg: getEl("fetchMsg"),
        block: getEl("submittedBlock"),
        
        hidden: {
            allocId: getEl('allocation_id'),
            hEmp: getEl('h_employee'),
            hDate: getEl('h_date'),
            status: getEl('formStatus'),
            draftId: getEl('draft_id'),
            timestamp: getEl('timestampInput')
        },
        payment: {
            totalAmt: getEl('totalAmount'), dispTotal: getEl('totAmount'),
            discount: getEl('discount'), cash: getEl('cash'), online: getEl('online'), due: getEl('dueAmount')
        },
        footer: {
            totalQty: getEl('totTotal'), soldQty: getEl('totSold'), returnQty: getEl('totReturn'), remainQty: getEl('totRemain')
        }
    };

    function updateClock() {
        const now = new Date();
        if(getEl('liveClock')) getEl('liveClock').textContent = now.toLocaleTimeString('en-US', { hour12: true });
        const iso = now.toISOString().slice(0, 19).replace('T', ' ');
        if(ui.hidden.timestamp) ui.hidden.timestamp.value = iso;
    }
    setInterval(updateClock, 1000);
    updateClock();

    if(ui.fetchBtn) {
        ui.fetchBtn.addEventListener('click', async () => {
            const empId = ui.empSelect.value;
            const dateVal = ui.dateInput.value;
            if (!empId || !dateVal) return alert("Select Employee & Date");

            ui.msg.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
            ui.form.classList.add('d-none');
            ui.block.classList.add('d-none');

            try {
                const fd = new FormData();
                fd.append('employee_id', empId);
                fd.append('date', dateVal);

                const res = await fetch('/api/fetch_evening_data', { method: 'POST', body: fd });
                const text = await res.text();
                let data;
                try { data = JSON.parse(text); } catch(e) { throw new Error("Server Error (Invalid JSON). Check logs."); }

                if (data.status === 'success') {
                    renderTable(data.products, data.source);
                    ui.hidden.allocId.value = data.allocation_id || '';
                    ui.hidden.hEmp.value = empId;
                    const [d, m, y] = dateVal.split('-');
                    ui.hidden.hDate.value = `${y}-${m}-${d}`;

                    if (data.source === 'draft' && data.draft_data) populateDraft(data.draft_id, data.draft_data);
                    else resetDraft();

                    ui.form.classList.remove('d-none');
                    ui.msg.innerHTML = '';
                    calculateDue(); 
                } else if (data.status === 'submitted') {
                    ui.block.classList.remove('d-none');
                    ui.msg.innerHTML = '';
                } else {
                    ui.msg.innerHTML = `<span class="text-danger">${data.message}</span>`;
                }
            } catch (e) {
                console.error(e);
                ui.msg.innerHTML = `<span class="text-danger">${e.message}</span>`;
            }
        });
    }

    function renderTable(products, source) {
        ui.tableBody.innerHTML = "";
        let badge = source === 'draft' ? 'Draft' : (source === 'previous_leftover' ? 'Previous Leftover' : 'Morning Allocation (Aggregated)');
        if(getEl('fetchMsg')) getEl('fetchMsg').innerHTML = `<span class="badge bg-info text-dark mb-2">${badge}</span>`;

        if(!products || !products.length) { ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center">No Stock Found</td></tr>'; return; }

        products.forEach((p, i) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="text-center">${i+1}</td>
                <td><img src="${p.image}" width="40" class="rounded"></td>
                <td>${p.name}<input type="hidden" name="product_id[]" value="${p.product_id}"></td>
                <td><input type="text" name="total_qty[]" class="form-control-plaintext text-center fw-bold total-qty" value="${p.total_qty}" readonly></td>
                <td><input type="number" name="sold[]" class="form-control text-center sold-input" value="${p.sold_qty || ''}" placeholder="0"></td>
                <td class="text-end"><input type="text" name="price[]" class="form-control-plaintext text-end price-val" value="${p.unit_price.toFixed(2)}" readonly></td>
                <td class="text-end fw-bold row-amt">0.00</td>
                <td><input type="number" name="return[]" class="form-control text-center return-input" value="${p.return_qty || ''}" placeholder="0"></td>
                <td class="text-center fw-bold remaining-qty">0</td>
            `;
            ui.tableBody.appendChild(row);
        });
        calculateDue();
    }

    function calculateDue() {
        let gTotal = 0, tQty = 0, tSold = 0, tRet = 0, tRem = 0;
        ui.tableBody.querySelectorAll('tr').forEach(row => {
            const tot = parseInt(row.querySelector('.total-qty').value) || 0;
            const soldInp = row.querySelector('.sold-input');
            const retInp = row.querySelector('.return-input');
            let sold = parseInt(soldInp.value) || 0;
            let ret = parseInt(retInp.value) || 0;
            const price = parseFloat(row.querySelector('.price-val').value) || 0;

            if (sold + ret > tot) { soldInp.style.borderColor = 'red'; } else { soldInp.style.borderColor = ''; }

            const rem = tot - sold - ret;
            row.querySelector('.remaining-qty').textContent = rem;
            const amt = sold * price;
            row.querySelector('.row-amt').textContent = amt.toFixed(2);

            gTotal += amt; tQty += tot; tSold += sold; tRet += ret; tRem += rem;
        });

        ui.payment.totalAmt.value = gTotal.toFixed(2);
        ui.payment.dispTotal.textContent = gTotal.toFixed(2);
        
        if(ui.footer.totalQty) ui.footer.totalQty.textContent = tQty;
        if(ui.footer.soldQty) ui.footer.soldQty.textContent = tSold;
        if(ui.footer.returnQty) ui.footer.returnQty.textContent = tRet;
        if(ui.footer.remainQty) ui.footer.remainQty.textContent = tRem;

        const disc = parseFloat(ui.payment.discount.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        if(ui.payment.due) ui.payment.due.textContent = (gTotal - (disc + online + cash)).toFixed(2);
    }

    ui.tableBody.addEventListener('input', e => { if(e.target.matches('.sold-input, .return-input')) calculateDue(); });
    [ui.payment.discount, ui.payment.online, ui.payment.cash].forEach(el => el.addEventListener('input', calculateDue));

    function populateDraft(id, d) {
        ui.hidden.draftId.value = id;
        ui.payment.discount.value = d.discount || '';
        ui.payment.online.value = d.online_money || '';
        ui.payment.cash.value = d.cash_money || '';
        // Add ledger fields if needed
    }
    function resetDraft() {
        ui.hidden.draftId.value = '';
        ui.payment.discount.value = '';
        ui.payment.online.value = '';
        ui.payment.cash.value = '';
    }

    window.saveDraft = function() { ui.hidden.status.value = 'draft'; ui.form.submit(); };
    window.submitFinal = function() { ui.hidden.status.value = 'final'; if(confirm("Confirm Final Submit?")) ui.form.submit(); };
});
