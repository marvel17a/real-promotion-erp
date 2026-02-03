document.addEventListener("DOMContentLoaded", () => {
    
    const getEl = (id) => document.getElementById(id);
    
    const ui = {
        empSelect: getEl("employee"), 
        dateInput: getEl("date"),
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
            totalAmt: getEl('totalAmount'), 
            dispTotal: getEl('totAmount'),  
            discount: getEl('discount'),
            cash: getEl('cash'),
            online: getEl('online'),
            due: getEl('dueAmount') // This is our target field
        },

        footer: {
            totalQty: getEl('totTotal'),
            soldQty: getEl('totSold'),
            returnQty: getEl('totReturn'),
            remainQty: getEl('totRemain')
        }
    };

    // --- 1. LIVE CLOCK ---
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: false });
        document.getElementById('liveClock').innerText = timeString;
        if(ui.hidden.timestamp) ui.hidden.timestamp.value = now.toISOString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- 2. FETCH DATA ---
    async function fetchData() {
        const empId = ui.empSelect.value;
        const dateVal = ui.dateInput.value;
        if (!empId || !dateVal) return;

        ui.msg.classList.remove('d-none');
        ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-5">Loading data...</td></tr>';
        
        // Reset Draft ID & Hidden Fields
        resetDraft();

        try {
            const res = await fetch(`/get_morning_allocation?employee_id=${empId}&date=${dateVal}`);
            const data = await res.json();
            
            ui.msg.classList.add('d-none');
            ui.hidden.hEmp.value = empId;
            ui.hidden.hDate.value = dateVal;

            if (data.status === 'submitted') {
                ui.block.classList.remove('d-none');
                ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-5 text-muted">Settlement already submitted for this date.</td></tr>';
                return;
            } else {
                ui.block.classList.add('d-none');
            }

            if (data.products && data.products.length > 0) {
                ui.hidden.allocId.value = data.allocation_id;
                renderTable(data.products);
                
                // If draft exists, load it
                if(data.draft) {
                    loadDraftData(data.draft);
                }
            } else {
                ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-5 text-warning">No Morning Allocation found for this employee/date.</td></tr>';
            }
        } catch (err) {
            console.error(err);
            ui.tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error loading data.</td></tr>';
        }
    }

    function renderTable(products) {
        ui.tableBody.innerHTML = '';
        products.forEach((p, index) => {
            const tr = document.createElement('tr');
            
            // Calc remain logic handled in input event
            const remain = p.qty; 

            tr.innerHTML = `
                <td class="ps-4 fw-bold text-muted">${index + 1}</td>
                <td><img src="${p.image}" class="rounded shadow-sm" style="width: 40px; height: 40px; object-fit: cover;"></td>
                <td>
                    <div class="fw-bold text-dark">${p.name}</div>
                    <div class="small text-muted">Stock: ${p.qty}</div>
                    <input type="hidden" name="product_ids[]" value="${p.id}">
                    <input type="hidden" name="prices[]" value="${p.price}">
                </td>
                <td class="text-center">₹ ${p.price}</td>
                <td class="text-center fw-bold text-primary">${p.qty}</td>
                <td class="bg-success bg-opacity-10">
                    <input type="number" name="sold_qtys[]" class="form-control form-control-sm text-center fw-bold sold-input" 
                           min="0" max="${p.qty}" placeholder="0">
                </td>
                <td class="bg-danger bg-opacity-10">
                    <input type="number" name="return_qtys[]" class="form-control form-control-sm text-center fw-bold return-input" 
                           min="0" max="${p.qty}" placeholder="0">
                </td>
                <td class="text-end pe-4 fw-bold row-amount">0.00</td>
            `;
            ui.tableBody.appendChild(tr);
        });
        calculateTotals();
    }

    // --- 3. CALCULATIONS (CORE LOGIC MODIFIED HERE) ---
    function calculateTotals(e) {
        let grandTotal = 0;
        let tQty = 0, tSold = 0, tReturn = 0;

        const rows = ui.tableBody.querySelectorAll('tr');
        rows.forEach(row => {
            const price = parseFloat(row.querySelector('[name="prices[]"]').value) || 0;
            const totalQty = parseInt(row.cells[4].innerText) || 0;
            
            const soldInput = row.querySelector('.sold-input');
            const returnInput = row.querySelector('.return-input');
            
            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Auto-adjust logic
            if (e && e.target === soldInput) {
                ret = totalQty - sold;
                if (ret < 0) { ret = 0; sold = totalQty; soldInput.value = sold; }
                returnInput.value = ret;
            } else if (e && e.target === returnInput) {
                sold = totalQty - ret;
                if (sold < 0) { sold = 0; ret = totalQty; returnInput.value = ret; }
                soldInput.value = sold;
            }

            const amount = sold * price;
            row.querySelector('.row-amount').innerText = amount.toFixed(2);
            
            grandTotal += amount;
            tQty += totalQty;
            tSold += sold;
            tReturn += ret;
        });

        ui.payment.totalAmt.value = grandTotal.toFixed(2);
        ui.payment.dispTotal.innerText = "₹ " + grandTotal.toFixed(2);

        ui.footer.totalQty.innerText = tQty;
        ui.footer.soldQty.innerText = tSold;
        ui.footer.returnQty.innerText = tReturn;

        calculateDue(); // Trigger Payment Logic
    }

    // --- NEW: MODIFIED DUE LOGIC ---
    function calculateDue(e) {
        const sales = parseFloat(ui.payment.totalAmt.value) || 0;
        const discount = parseFloat(ui.payment.discount.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;

        const netPayable = sales - discount;
        const totalPaid = cash + online;
        
        // Difference: +ve means DUE, -ve means OVERPAID (Surplus)
        const balance = netPayable - totalPaid;
        const dueEl = ui.payment.due;

        // Reset Styles
        dueEl.className = "form-control fw-bold text-center border-0"; 
        // Remove yellow bg if it was added dynamically (handled by bootstrap bg-warning class on input)
        dueEl.classList.remove("bg-warning", "text-white", "text-danger", "text-success", "bg-white");

        // Logic 1: CLEARED (Zero Due)
        if (Math.abs(balance) < 0.1) {
            dueEl.value = "CLEARED";
            dueEl.classList.add("bg-white", "text-success");
        } 
        // Logic 2: DUE (Red Text, -Sign)
        else if (balance > 0) {
            dueEl.value = "-" + balance.toFixed(2);
            dueEl.classList.add("bg-white", "text-danger");
        } 
        // Logic 3: OVERPAID (Yellow Box, Green Text, +Sign)
        else {
            const surplus = Math.abs(balance).toFixed(2);
            dueEl.value = "+" + surplus + " Paid Cash";
            
            // Add Yellow Background and Green Text
            dueEl.classList.add("bg-warning", "text-success");
            // NOTE: bg-warning is Bootstrap yellow. text-success is green.
            // If you want text-dark on yellow, change text-success to text-dark.
            // Requirement was "Yellow color ho text green".
        }
    }

    function loadDraftData(draft) {
        if(draft.id) ui.hidden.draftId.value = draft.id;
        
        setVal('discount', draft.discount);
        setVal('cash', draft.cash_collected);
        setVal('online', draft.online_collected);
        setVal('note', draft.note);
        setVal('emp_debit_note', draft.emp_debit_note);
        setVal('emp_credit_note', draft.emp_credit_note);

        const rows = ui.tableBody.querySelectorAll('tr');
        rows.forEach((row, i) => {
            if (draft.items[i]) {
                const soldIn = row.querySelector('.sold-input');
                const retIn = row.querySelector('.return-input');
                if(soldIn) soldIn.value = draft.items[i].sold;
                if(retIn) retIn.value = draft.items[i].return;
            }
        });
        calculateTotals();
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

    // --- LISTENERS ---
    ui.empSelect.addEventListener('change', fetchData);
    ui.dateInput.addEventListener('change', fetchData);

    ui.tableBody.addEventListener('input', (e) => {
        if (e.target.matches('.sold-input, .return-input')) calculateTotals(e);
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
        
        const emp = ui.empSelect.value;
        if(!emp) { alert("Please select an employee first."); return; }

        if(!confirm("Are you sure you want to SUBMIT this settlement? Inventory will be deducted.")) return;
        ui.form.submit();
    };
});
