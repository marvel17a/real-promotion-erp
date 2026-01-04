document.addEventListener("DOMContentLoaded", () => {
    
    // Helper to get element safely
    const getEl = (id) => document.getElementById(id);

    // 1. Define UI Elements (Exact ID Match)
    const ui = {
        empSelect: getEl("employee"), 
        dateInput: getEl("date"),
        fetchBtn: getEl("btnFetch"),
        form: getEl("eveningForm"),
        tableBody: getEl("rowsArea"),
        msg: getEl("fetchMsg"),
        block: getEl("submittedBlock"), // For "Already Submitted" view

        // Hidden Inputs for Backend
        hidden: {
            allocId: getEl('allocation_id'),
            hEmp: getEl('h_employee'),
            hDate: getEl('h_date'),
            status: getEl('formStatus'),
            draftId: getEl('draft_id')
        },
        
        // Payment & Calc Fields
        payment: {
            totalAmt: getEl('totalAmount'), // Hidden total
            dispTotal: getEl('totAmount'),  // Display text in footer
            discount: getEl('discount'),
            cash: getEl('cash'),
            online: getEl('online'),
            due: getEl('dueAmount')
        }
    };

    // --- LIVE CLOCK LOGIC ---
    function updateClock() {
        const now = new Date();
        // 1. Update Display
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        const clockEl = getEl('liveClock');
        if(clockEl) clockEl.textContent = timeString;

        // 2. Update Hidden Timestamp for Backend
        // Format: YYYY-MM-DD HH:MM:SS
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        const timestampInput = document.getElementById('timestampInput');
        if(timestampInput) {
            timestampInput.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        }
    }

    // Start the clock immediately and update every second
    setInterval(updateClock, 1000);
    updateClock(); // Run once on load to avoid 00:00:00 delay

    // 2. Fetch Logic
    //if(ui.fetchBtn) {
      //  ui.fetchBtn.addEventListener('click', async () => {
        //    const empId = ui.empSelect.value;
          //  const dateVal = ui.dateInput.value;

            //if (!empId || !dateVal) {
              //  alert("Please select Employee and Date.");
                //return;
            
//}

    // --- 2. Fetch Logic ---
    if(ui.fetchBtn) {
        ui.fetchBtn.addEventListener('click', async () => {
            const empId = ui.empSelect.value;
            const dateVal = ui.dateInput.value;

            if (!empId || !dateVal) {
                alert("Please select Employee and Date.");
                return;
            }

            // UI Reset (Hide everything first)
            ui.msg.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking status...';
            ui.form.classList.add('d-none'); // Hide Form
            if(ui.block) ui.block.classList.add('d-none'); // Hide Block

            try {
                const formData = new FormData();
                formData.append('employee_id', empId);
                formData.append('date', dateVal);

                const res = await fetch('/api/fetch_evening_data', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.status === 'success') {
                    // 1. DATA FOUND - SHOW FORM
                    renderTable(data.products, data.source);
                    
                    // Fill Hidden Inputs
                    if(ui.hidden.allocId) ui.hidden.allocId.value = data.allocation_id || '';
                    if(ui.hidden.hEmp) ui.hidden.hEmp.value = empId;
                    
                    // Date Conversion
                    const [d, m, y] = dateVal.split('-');
                    if(ui.hidden.hDate) ui.hidden.hDate.value = `${y}-${m}-${d}`;

                    // Handle Draft
                    if (data.source === 'draft' && data.draft_data) {
                        populateDraft(data.draft_id, data.draft_data);
                    } else {
                        resetDraft();
                    }

                    // Reveal Form
                    ui.form.classList.remove('d-none');
                    ui.msg.textContent = "";
                    calculateDue(); 

                } else if (data.status === 'submitted') {
                    // 2. ALREADY SUBMITTED - SHOW BLOCKER
                    // Explicitly ensure form is hidden
                    ui.form.classList.add('d-none'); 
                    // Show the 'Submitted' div
                    if(ui.block) ui.block.classList.remove('d-none');
                    ui.msg.textContent = "";
                    
                } else {
                    // 3. ERROR OR NO DATA
                    ui.msg.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> ${data.message}</span>`;
                }

            } catch (e) {
                console.error("Fetch Error:", e);
                ui.msg.innerHTML = '<span class="text-danger">Server Error. Please check connection.</span>';
            }
        });
    }

            // UI Loading State
            ui.msg.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Fetching data...';
            ui.form.classList.add('d-none');
            if(ui.block) ui.block.classList.add('d-none');

            try {
                const formData = new FormData();
                formData.append('employee_id', empId);
                formData.append('date', dateVal);

                const res = await fetch('/api/fetch_evening_data', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.status === 'success') {
                    // Populate Table
                    renderTable(data.products, data.source);
                    
                    // Populate Hidden Fields
                    if(ui.hidden.allocId) ui.hidden.allocId.value = data.allocation_id || '';
                    if(ui.hidden.hEmp) ui.hidden.hEmp.value = empId;
                    
                    // Date Conversion (dd-mm-yyyy -> yyyy-mm-dd)
                    const [d, m, y] = dateVal.split('-');
                    if(ui.hidden.hDate) ui.hidden.hDate.value = `${y}-${m}-${d}`;

                    // Handle Draft Data Populate
                    if (data.source === 'draft' && data.draft_data) {
                        populateDraft(data.draft_id, data.draft_data);
                    } else {
                        resetDraft();
                    }

                    // Show Form
                    ui.form.classList.remove('d-none');
                    ui.msg.textContent = "";
                    calculateDue(); // Initial Calc

                } else if (data.status === 'submitted') {
                    // Show "Already Submitted" Block
                    if(ui.block) ui.block.classList.remove('d-none');
                    ui.form.classList.add('d-none');
                    ui.msg.textContent = "";
                } else {
                    ui.msg.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> ${data.message}</span>`;
                }

            } catch (e) {
                console.error("Fetch Error:", e);
                ui.msg.innerHTML = '<span class="text-danger">Server Error. Check Console.</span>';
            }
        });
    }

    // 3. Render Table Function
    // --- 3. Render Table (Fixed 9 Columns to match Header) ---
    function renderTable(products, source) {
        ui.tableBody.innerHTML = "";
        
        let badgeClass = 'bg-success';
        let badgeText = 'Loaded Morning Allocation';
        
        if(source === 'previous_leftover') {
            badgeClass = 'bg-info text-dark';
            badgeText = 'Loaded Previous Remaining Stock';
        } else if (source === 'draft') {
            badgeClass = 'bg-warning text-dark';
            badgeText = 'Resumed from Draft';
        }
        
        ui.msg.innerHTML = `<span class="badge ${badgeClass} mb-3 shadow-sm px-3 py-2"><i class="fa-solid fa-layer-group me-2"></i>${badgeText}</span>`;

        if(!products || products.length === 0) {
            ui.tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">No products found.</td></tr>';
            return;
        }

        products.forEach((p, index) => {
            const soldVal = (p.sold_qty !== undefined && p.sold_qty !== 0) ? p.sold_qty : '';
            const retVal = (p.return_qty !== undefined && p.return_qty !== 0) ? p.return_qty : '';

            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="text-center text-muted fw-bold align-middle">${index + 1}</td>
                
                <td class="text-center align-middle">
                    <div class="prod-img-box mx-auto" style="width: 40px; height: 40px;">
                        <img src="${p.image}" class="rounded border" style="width: 100%; height: 100%; object-fit: cover;">
                    </div>
                </td>
                
                <td class="align-middle">
                    <div class="fw-bold text-dark small">${p.name}</div>
                    <input type="hidden" name="product_id[]" value="${p.product_id || p.id}">
                </td>
                
                <td class="align-middle">
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
        calculateDue(); // Recalc rows immediately
    }

    // 4. Calculations
    // --- 4. STRICT CALCULATIONS & VALIDATION ---
    function calculateDue(e) {
        let grandTotal = 0;
        let sumTotalQty = 0;
        let sumSoldQty = 0;
        let sumReturnQty = 0;
        let sumLeft = 0;

        const rows = ui.tableBody.querySelectorAll('tr');

        // --- PART A: STOCK VALIDATION (Row by Row) ---
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

            // [VALIDATION] Check if Sold + Return > Total Stock
            if (sold + ret > total) {
                // Determine which input triggered the event to adjust that specific one
                if (e && e.target === soldInp) {
                    alert(`Cannot sell more than available stock (${total}).\nMax possible Sold: ${total - ret}`);
                    sold = total - ret;
                    soldInp.value = sold; // Auto-correct Input
                } else if (e && e.target === retInp) {
                    alert(`Cannot return more than available stock (${total}).\nMax possible Return: ${total - sold}`);
                    ret = total - sold;
                    retInp.value = ret; // Auto-correct Input
                } else {
                    // Fallback auto-correct (Priority to Sold)
                    if(sold > total) { sold = total; ret = 0; }
                    else { ret = total - sold; }
                    soldInp.value = sold;
                    retInp.value = ret;
                }
            }

            // Visual Styling
            if(sold === 0 && ret === 0) {
                soldInp.classList.remove('border-success', 'fw-bold');
            } else {
                soldInp.classList.add('border-success', 'fw-bold');
            }

            // Calculate Remaining
            const left = total - sold - ret;
            leftEl.textContent = left;

            // Calculate Row Amount
            const rowAmt = sold * price;
            amtEl.textContent = rowAmt.toFixed(2);
            
            // Accumulate
            grandTotal += rowAmt;
            sumTotalQty += total;
            sumSoldQty += sold;
            sumReturnQty += ret;
            sumLeft += left;
        });

        // Update Footer Stats
        if(getEl('totTotal')) getEl('totTotal').textContent = sumTotalQty;
        if(getEl('totSold')) getEl('totSold').textContent = sumSoldQty;
        if(getEl('totReturn')) getEl('totReturn').textContent = sumReturnQty;
        if(getEl('totRemain')) getEl('totRemain').textContent = sumLeft;
        if(getEl('totAmount')) getEl('totAmount').textContent = grandTotal.toFixed(2);

        // Update Payment Total
        if(ui.payment.totalAmt) ui.payment.totalAmt.value = grandTotal.toFixed(2);
        if(ui.payment.dispTotal) ui.payment.dispTotal.textContent = grandTotal.toFixed(2);

        // --- PART B: PAYMENT VALIDATION (Cash/Online/Discount) ---
        validatePayment(grandTotal, e);
    }

    function validatePayment(totalSales, e) {
        let disc = parseFloat(ui.payment.discount.value) || 0;
        let online = parseFloat(ui.payment.online.value) || 0;
        let cash = parseFloat(ui.payment.cash.value) || 0;

        const totalPayment = disc + online + cash;

        // [VALIDATION] Check if Payment > Total Sales
        // Allow variance only if Total Sales is 0 (pre-payment) or small rounding difference
        if (totalPayment > totalSales + 1) { // +1 buffer for float rounding
            if (e && (e.target === ui.payment.discount || e.target === ui.payment.online || e.target === ui.payment.cash)) {
                alert(`Payment Limit Exceeded!\nTotal Sales is ₹${totalSales}\nYou entered Total Payment: ₹${totalPayment}`);
                
                // Auto-correct the field currently being edited
                const currentInput = e.target;
                const otherPayments = totalPayment - (parseFloat(currentInput.value) || 0);
                const maxAllowed = Math.max(0, totalSales - otherPayments);
                
                currentInput.value = maxAllowed.toFixed(2);
                
                // Update variable for calc
                if(currentInput === ui.payment.discount) disc = maxAllowed;
                if(currentInput === ui.payment.cash) cash = maxAllowed;
                if(currentInput === ui.payment.online) online = maxAllowed;
            }
        }

        const due = totalSales - (disc + cash + online);
        
        // Update Due Amount UI
        if(ui.payment.due) ui.payment.due.textContent = due.toFixed(2);
        
        // Update Due Note automatically based on balance
        const dueNote = getEl('due_note');
        if(dueNote) {
            if(due > 1) dueNote.value = "Pending Balance";
            else if (due < -1) dueNote.value = "Excess Payment Error";
            else dueNote.value = "Settled";
        }
    }

    // --- 5. Event Listeners ---
    // Pass 'e' (event) to calculation to know which input triggered it
    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input, .return-input')) calculateDue(e);
    });
    
    if(ui.payment.discount) ui.payment.discount.addEventListener('input', (e) => calculateDue(e));
    if(ui.payment.online) ui.payment.online.addEventListener('input', (e) => calculateDue(e));
    if(ui.payment.cash) ui.payment.cash.addEventListener('input', (e) => calculateDue(e));

    // 5. Populate Draft Data Helpers
    function populateDraft(id, d) {
        if(ui.hidden.draftId) ui.hidden.draftId.value = id;
        
        if(ui.payment.discount) ui.payment.discount.value = d.discount || '';
        if(ui.payment.online) ui.payment.online.value = d.online_money || '';
        if(ui.payment.cash) ui.payment.cash.value = d.cash_money || '';
        
        // Employee Finance Fields (Safe check)
        const crAmt = document.querySelector('[name="emp_credit_amount"]');
        const crNote = document.querySelector('[name="emp_credit_note"]');
        const drAmt = document.querySelector('[name="emp_debit_amount"]');
        const drNote = document.querySelector('[name="emp_debit_note"]');
        
        if(crAmt) crAmt.value = d.emp_credit_amount || '';
        if(crNote) crNote.value = d.emp_credit_note || '';
        if(drAmt) drAmt.value = d.emp_debit_amount || '';
        if(drNote) drNote.value = d.emp_debit_note || '';
    }

    function resetDraft() {
        if(ui.hidden.draftId) ui.hidden.draftId.value = '';
        if(ui.payment.discount) ui.payment.discount.value = '';
        if(ui.payment.online) ui.payment.online.value = '';
        if(ui.payment.cash) ui.payment.cash.value = '';
        
        document.querySelectorAll('[name^="emp_"]').forEach(el => el.value = '');
    }

    // 6. Event Listeners for Calc
    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input, .return-input')) calculateDue();
    });
    
    if(ui.payment.discount) ui.payment.discount.addEventListener('input', calculateDue);
    if(ui.payment.online) ui.payment.online.addEventListener('input', calculateDue);
    if(ui.payment.cash) ui.payment.cash.addEventListener('input', calculateDue);

    // 7. Global Submit Functions (Attached to Window for HTML onclick)
    window.saveDraft = function() {
        if(ui.hidden.status) ui.hidden.status.value = 'draft';
        ui.form.submit();
    };

    window.submitFinal = function() {
        if(ui.hidden.status) ui.hidden.status.value = 'final';
        
        const total = parseFloat(ui.payment.totalAmt.value) || 0;
        if (total === 0) {
            if(!confirm("Total Sales is 0. Are you sure you want to submit?")) return;
        }
        
        if(confirm("FINAL SUBMIT?\n\n- Stock will be deducted.\n- Ledger entries will be created.")) {
            ui.form.submit();
        }
    };
});







