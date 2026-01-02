document.addEventListener("DOMContentLoaded", () => {
    
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee"), 
        dateInput: getEl("date"),
        fetchButton: getEl("btnFetch"),
        tableBody: getEl("rowsArea"),
        fetchMsg: getEl("fetchMsg"),
        btnFinal: getEl("btnFinal"),
        form: getEl("eveningForm"),
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
    
    // Live Clock
    setInterval(() => {
        const now = new Date();
        const el = getEl('liveClock');
        if(el) el.textContent = now.toLocaleTimeString();
    }, 1000);

    // Flatpickr
    flatpickr("#date", { dateFormat: "d-m-Y", defaultDate: "today", allowInput: true });

    // Employee Photo
    if(ui.employeeSelect) {
        ui.employeeSelect.addEventListener('change', function() {
            const opt = this.options[this.selectedIndex];
            const img = opt.getAttribute('data-img');
            const photo = getEl('empPhoto');
            if(img && img !== "") photo.src = img;
            else photo.src = "/static/img/default-user.png";
        });
    }

    // --- FETCH LOGIC ---
    async function fetchMorningAllocation() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;

        if (!empId) { alert("Please select an employee"); return; }
        
        ui.fetchMsg.classList.remove("d-none");
        ui.tableBody.innerHTML = ""; // Clear current

        try {
            const res = await fetch(`/api/fetch_evening_data?employee_id=${empId}&date=${dateVal}`);
            const data = await res.json();
            
            if (data.status === "final") {
                ui.tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-danger fw-bold fs-5">
                    <i class="fa-solid fa-lock me-2"></i> ${data.message}
                </td></tr>`;
                ui.btnFinal.disabled = true;
            } else {
                ui.btnFinal.disabled = false;
                
                if (data.status === "success" && data.items.length > 0) {
                    data.items.forEach(item => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td>
                                <div class="d-flex align-items-center">
                                    <img src="${item.image}" class="rounded border me-2 shadow-sm" width="40" height="40">
                                    <div>
                                        <div class="fw-bold text-dark">${item.name}</div>
                                        <small class="text-muted">₹${item.price}</small>
                                    </div>
                                </div>
                                <input type="hidden" name="product_id[]" value="${item.product_id}">
                                <input type="hidden" name="price[]" class="price" value="${item.price}">
                            </td>
                            <td class="text-center">
                                <input type="number" name="total_qty[]" class="form-control text-center fw-bold bg-light total-qty" value="${item.total_qty}" readonly>
                            </td>
                            <td>
                                <input type="number" name="sold_qty[]" class="form-control text-center text-success fw-bold sold" min="0" placeholder="0">
                            </td>
                            <td>
                                <input type="number" name="return_qty[]" class="form-control text-center text-danger fw-bold return" min="0" placeholder="0">
                            </td>
                            <td class="text-center">
                                 <span class="badge bg-primary fs-6 remaining shadow-sm">0</span>
                            </td>
                        `;
                        ui.tableBody.appendChild(tr);
                    });
                    recalculateTotals();
                } else {
                    ui.tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-muted">No products found for this Employee (Check Morning Allocation).</td></tr>`;
                }
            }
        } catch (err) {
            console.error(err);
        } finally {
            ui.fetchMsg.classList.add("d-none");
        }
    }

    // --- CALCULATION LOGIC ---
    function recalculateTotals() {
        let tTotal = 0, tSold = 0, tReturn = 0, tRemain = 0, tAmount = 0;

        ui.tableBody.querySelectorAll("tr").forEach(row => {
            if(!row.querySelector(".total-qty")) return;

            const total = parseInt(row.querySelector(".total-qty").value) || 0;
            const soldInput = row.querySelector(".sold");
            const returnInput = row.querySelector(".return");
            const price = parseFloat(row.querySelector(".price").value) || 0;

            let sold = parseInt(soldInput.value) || 0;
            let ret = parseInt(returnInput.value) || 0;

            // Auto-calculate Remaining
            let remain = total - sold - ret;
            if(remain < 0) remain = 0;

            row.querySelector(".remaining").textContent = remain;

            tTotal += total;
            tSold += sold;
            tReturn += ret;
            tRemain += remain;
            tAmount += (sold * price);
        });

        ui.footer.total.textContent = tTotal;
        ui.footer.sold.textContent = tSold;
        ui.footer.return.textContent = tReturn;
        ui.footer.remain.textContent = tRemain;
        ui.footer.amount.textContent = tAmount.toFixed(2);
        
        ui.payment.totalAmount.value = tAmount.toFixed(2);
        ui.payment.amount.textContent = tAmount.toFixed(2);
        
        calculateDue();
    }

    function calculateDue() {
        const total = parseFloat(ui.payment.totalAmount.value) || 0;
        const disc = parseFloat(ui.payment.discount.value) || 0;
        const cash = parseFloat(ui.payment.cash.value) || 0;
        const online = parseFloat(ui.payment.online.value) || 0;

        const due = total - disc - cash - online;
        ui.payment.due.textContent = due.toFixed(2);
    }

    // --- EVENTS ---
    ui.fetchButton.addEventListener("click", (e) => {
        e.preventDefault();
        fetchMorningAllocation();
    });

    ui.tableBody.addEventListener("input", (e) => {
        if(e.target.matches(".sold, .return")) recalculateTotals();
    });

    [ui.payment.discount, ui.payment.cash, ui.payment.online].forEach(el => {
        if(el) el.addEventListener("input", calculateDue);
    });

    // --- ONE CLICK SUBMIT ---
    if(ui.btnFinal) {
        ui.btnFinal.addEventListener("click", function() {
            // Sweet Alert Confirmation
            Swal.fire({
                title: 'Confirm Final Submission?',
                text: "Stock will be added back (Returns) and Financials saved.",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#198754',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Yes, Submit!'
            }).then((result) => {
                if (result.isConfirmed) {
                    const hiddenStatus = document.createElement("input");
                    hiddenStatus.type = "hidden";
                    hiddenStatus.name = "status";
                    hiddenStatus.value = "final";
                    ui.form.appendChild(hiddenStatus);
                    ui.form.submit();
                }
            });
        });
    }
});
