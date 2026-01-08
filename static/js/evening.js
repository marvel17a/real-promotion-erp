document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. UI DEFINITIONS ---
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
            totalAmt: getEl('totalAmount'), // Hidden input
            dispTotal: getEl('totAmount'),  // Footer display text
            discount: getEl('discount'),
            cash: getEl('cash'),
            online: getEl('online'),
            due: getEl('dueAmount')
        },

        footer: {
            totalQty: getEl('totTotal'),
            soldQty: getEl('totSold'),
            returnQty: getEl('totReturn'),
            remainQty: getEl('totRemain')
        }
    };

    // --- 2. LIVE CLOCK LOGIC ---
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        const clockEl = getEl('liveClock');
        if(clockEl) clockEl.textContent = timeString;

        if(ui.hidden.timestamp) {
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            ui.hidden.timestamp.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        }
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- 3. FETCH DATA LOGIC ---
    if(ui.fetchBtn) {
        ui.fetchBtn.addEventListener('click', async () => {
            const empId = ui.empSelect.value;
            const dateVal = ui.dateInput.value;

            if (!empId || !dateVal) {
                alert("Please select Sales Representative and Date.");
                return;
            }

            ui.msg.classList.remove('d-none');
            ui.msg.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking records...';
            
            if(ui.form) ui.form.classList.add('d-none');
            if(ui.block) ui.block.classList.add('d-none');

            try {
                const formData = new FormData();
                formData.append('employee_id', empId);
                formData.append('date', dateVal);

                const res = await fetch('/api/fetch_evening_data', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.status === 'success') {
                    // RENDER TABLE
                    renderTable(data.products, data.source);
                    
                    // SET HIDDEN VALUES
                    if(ui.hidden.allocId) ui.hidden.allocId.value = data.allocation_id || '';
                    if(ui.hidden.hEmp) ui.hidden.hEmp.value = empId;
                    
                    const [d, m, y] = dateVal.split('-');
                    if(ui.hidden.hDate) ui.hidden.hDate.value = `${y}-${m}-${d}`;

                    // DRAFT LOGIC
                    if (data.source === 'draft' && data.draft_data) {
                        populateDraft(data.draft_id, data.draft_data);
                    } else {
                        resetDraft();
                    }

                    ui.form.classList.remove('d-none');
                    ui.msg.classList.add('d-none');
                    calculateDue(); 

                } else if (data.status === 'submitted') {
                    if(ui.block) ui.block.classList.remove('d-none');
                    ui.msg.classList.add('d-none');
                    
                } else {
                    ui.msg.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation me-2"></i>${data.message}</span>`;
                }

            } catch (e) {
                console.error("Fetch Error:", e);
                ui.msg.innerHTML = '<span class="text-danger">Connection Failed. Check console.</span>';
            }
        });
    }

    // --- 4. RENDER TABLE (9 Columns) ---
    function renderTable(products, source) {
        ui.tableBody.innerHTML = "";
        
        let badge = "";
        if(source === 'draft') {
            badge = '<span class="badge bg-warning text-dark mb-2">Draft Mode - Resumed</span>';
        } else if (source === 'previous_leftover') {
            badge = '<span class="badge bg-info text-dark mb-2">Previous Leftover Stock (No Morning Allocation)</span>';
        } else {
            badge = '<span class="badge bg-success mb-2">Morning Allocation</span>';
        }
        
        const statusDiv = document.getElementById('fetchMsg');
        if(statusDiv) {
            statusDiv.innerHTML = badge;
            statusDiv.classList.remove('d-none');
        }

        if(!products || products.length === 0) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">No stock records found.</td></tr>';
            return;
        }

        products.forEach((p, index) => {
            const soldVal = (p.sold_qty && p.sold_qty !== 0) ? p.sold_qty : '';
            const retVal = (p.return_qty && p.return_qty !== 0) ? p.return_qty : '';

            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="text-center text-muted fw-bold align-middle">${index + 1}</td>
                <td class="text-center align-middle">
                    <div class="prod-img-box mx-auto" style="width: 40px; height: 40px;">
                        <img src="${p.image}" class="rounded border" style="width: 100%; height: 100%; object-fit: cover;">
                    </div>
                </td>
                <td class="align-middle">
                    <div class="fw-bold text-dark small text-wrap" style="max-width: 250px;">${p.name}</div>
                    <input type="hidden" name="product_id[]" value="${p.product_id || p.id}">
                </td>
                <td class="align-middle text-center">
                    <input type="text" name="total_qty[]" class="form-control-plaintext text-center fw-bold text-secondary py-0 total-qty" value="${p.total_qty}" readonly>
                </td>
                <td class="align-middle">
                    <input type="number" name="sold[]" class="form-control form-control-sm text-center fw-bold sold-input shadow-sm border-success" placeholder="0" min="0" value="${soldVal}">
                </td>
                <td class="align-middle text-end">
                    <div class="input-group input-group-sm justify-content-end">
                        <span class="input-group-text border-0 bg-transparent pe-1 text-muted">₹</span>
                        <input type="text" name="price[]" class="form-control-plaintext price-val text-end p-0" value="${p.unit_price.toFixed(2)}" readonly style="width: 50px;">
                    </div>
                </td>
                <td class="align-middle text-end pe-3">
                    <span class="fw-bold text-primary row-amt">0.00</span>
                </td>
                <td class="align-middle">
                    <input type="number" name="return[]" class="form-control form-control-sm text-center return-input shadow-sm border-danger" placeholder="0" min="0" value="${retVal}">
                </td>
                <td class="text-center fw-bold text-muted remaining-qty align-middle">0</td>
            `;
            ui.tableBody.appendChild(row);
        });
        calculateDue();
    }

    // --- 5. CALCULATIONS & VALIDATION ---
    function calculateDue(e) {
        let grandTotal = 0;
        let sumTotal = 0;
        let sumSold = 0;
        let sumReturn = 0;
        let sumLeft = 0;

        const rows = ui.tableBody.querySelectorAll('tr');

        rows.forEach(row => {
            const totalInp = row.querySelector('.total-qty');
            if(!totalInp) return;

            const total = parseInt(totalInp.value) || 0;
            const soldInp = row.querySelector('.sold-input');
            const retInp = row.querySelector('.return-input');
            const price = parseFloat(row.querySelector('.price-val').value) || 0;
            const amtEl = row.querySelector('.row-amt');
            const leftEl = row.querySelector('.remaining-qty');

            let sold = parseInt(soldInp.value) || 0;
            let ret = parseInt(retInp.value) || 0;

            // Strict Validation: Sold + Return <= Total
            if (sold + ret > total) {
                // Determine which input caused the error
                if (e && e.target === soldInp) {
                    // alert(`Limit Exceeded! You only have ${total} items.\nMax Sold possible: ${total - ret}`);
                    sold = total - ret;
                    soldInp.value = sold;
                } else if (e && e.target === retInp) {
                    // alert(`Limit Exceeded! You only have ${total} items.\nMax Return possible: ${total - sold}`);
                    ret = total - sold;
                    retInp.value = ret;
                } else {
                    // Fallback reset
                    soldInp.classList.add('is-invalid');
                    retInp.classList.add('is-invalid');
                }
            } else {
                soldInp.classList.remove('is-invalid');
                retInp.classList.remove('is-invalid');
            }

            // Calc Remaining
            const left = total - sold - ret;
            if(leftEl) leftEl.textContent = left;
            
            // Calc Amount
            const rowAmt = sold * price;
            amtEl.textContent = rowAmt.toFixed(2);

            // Accumulate
            grandTotal += rowAmt;
            sumTotal += total;
            sumSold += sold;
            sumReturn += ret;
            sumLeft += left;
        });

        // Update Footer
        if(ui.footer.totalQty) ui.footer.totalQty.textContent = sumTotal;
        if(ui.footer.soldQty) ui.footer.soldQty.textContent = sumSold;
        if(ui.footer.returnQty) ui.footer.returnQty.textContent = sumReturn;
        if(ui.footer.remainQty) ui.footer.remainQty.textContent = sumLeft;
        
        // Update Totals
        if(ui.payment.totalAmt) ui.payment.totalAmt.value = grandTotal.toFixed(2);
        if(ui.payment.dispTotal) ui.payment.dispTotal.textContent = grandTotal.toFixed(2);

        // --- PAYMENT LOGIC UPDATE ---
        const disc = parseFloat(ui.payment.discount.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;

        const totalPay = disc + online + cash;
        
        // VALIDATION REMOVED: Allow higher payment (Employee Profit)
        // if(totalPay > grandTotal + 1.0) { ... } // Removed this block

        const due = grandTotal - totalPay;
        
        if(ui.payment.due) {
            // Logic for Color & Text
            const dueEl = ui.payment.due;
            const balanceBox = document.querySelector('.balance-box'); // Parent Box
            
            // Create or Get the small info text element
            let profitInfoEl = document.getElementById('profitInfo');
            if(!profitInfoEl) {
                profitInfoEl = document.createElement('div');
                profitInfoEl.id = 'profitInfo';
                profitInfoEl.className = 'text-center small fw-bold mb-1';
                profitInfoEl.style.fontSize = '0.8rem';
                // Insert before balance box content
                if(balanceBox) balanceBox.insertBefore(profitInfoEl, balanceBox.firstChild);
            }

            if (due > 0) {
                // Pending (Red)
                dueEl.textContent = due.toFixed(2);
                dueEl.style.color = '#dc3545'; // Red
                profitInfoEl.textContent = "Pending from Employee";
                profitInfoEl.style.color = '#dc3545';
            } else if (due < 0) {
                // Profit/Extra (Green)
                const extra = Math.abs(due).toFixed(2);
                dueEl.textContent = "+" + extra; // Show as positive extra
                dueEl.style.color = '#198754'; // Green
                profitInfoEl.textContent = `Amount paid in cash : Rs.${extra}`;
                profitInfoEl.style.color = '#198754';
            } else {
                // Settled (Zero)
                dueEl.textContent = "0.00";
                dueEl.style.color = '#0d6efd'; // Blue
                profitInfoEl.textContent = "Settled";
                profitInfoEl.style.color = '#6c757d';
            }
        }

        // Auto Due Note Update
        const dueNote = getEl('due_note');
        if(dueNote) {
            if(due > 1) dueNote.value = "Pending Balance";
            else if (due < -1) dueNote.value = "Extra Payment (Profit)";
            else dueNote.value = "Settled";
        }
    }

    // --- 6. HELPERS ---
    function populateDraft(id, d) {
        if(ui.hidden.draftId) ui.hidden.draftId.value = id;
        if(ui.payment.discount) ui.payment.discount.value = d.discount || '';
        if(ui.payment.online) ui.payment.online.value = d.online_money || '';
        if(ui.payment.cash) ui.payment.cash.value = d.cash_money || '';
        
        setVal('emp_credit_amount', d.emp_credit_amount);
        setVal('emp_credit_note', d.emp_credit_note);
        setVal('emp_debit_amount', d.emp_debit_amount);
        setVal('emp_debit_note', d.emp_debit_note);
    }

    function setVal(name, val) {
        const el = document.querySelector(`[name="${name}"]`);
        if(el) el.value = val || '';
    }

    function resetDraft() {
        if(ui.hidden.draftId) ui.hidden.draftId.value = '';
        if(ui.payment.discount) ui.payment.discount.value = '';
        if(ui.payment.online) ui.payment.online.value = '';
        if(ui.payment.cash) ui.payment.cash.value = '';
        document.querySelectorAll('[name^="emp_"]').forEach(el => el.value = '');
    }

    // --- 7. LISTENERS ---
    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input, .return-input')) calculateDue(e);
    });

    [ui.payment.discount, ui.payment.online, ui.payment.cash].forEach(el => {
        if(el) el.addEventListener('input', (e) => calculateDue(e));
    });

    window.saveDraft = function() {
        if(ui.hidden.status) ui.hidden.status.value = 'draft';
        ui.form.submit();
    };

    window.submitFinal = function() {
        if(ui.hidden.status) ui.hidden.status.value = 'final';
        
        const total = parseFloat(ui.payment.totalAmt.value) || 0;
        // Removed 0 check to allow profit on 0 sales if needed, but usually good to keep warning
        if (total === 0 && !confirm("Total Sales is 0. Submit?")) return;
        
        if(confirm("CONFIRM SETTLEMENT?\n\n- Returns will add to stock.\n- Ledger will be updated.")) {
            ui.form.submit();
        }
    };
});
