document.addEventListener("DOMContentLoaded", () => {
    const getEl = (id) => document.getElementById(id);
    const ui = {
        employeeSelect: getEl("employee_id"),
        dateInput: getEl("date"),
        timestampInput: getEl("timestampInput"),
        clockDisplay: getEl("liveClock"),
        tableBody: document.querySelector("#productTable tbody"),
        addRowBtn: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        historyList: getEl("historyList"),
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    if (!ui.employeeSelect || !ui.tableBody) return;

    let isRestockMode = false;
    const productsData = window.productsData || [];
    const productsMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/50?text=Img";

    let productOptionsHtml = '<option value="">-- Select --</option>';
    if (Array.isArray(productsData)) {
        productsData.forEach(p => {
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}">${p.name}</option>`;
        });
    }

    // --- 1. DIGITAL CLOCK ---
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        if(ui.clockDisplay) ui.clockDisplay.textContent = timeString;
        
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        if(ui.timestampInput) ui.timestampInput.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- 2. FETCH STOCK ---
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;
        
        if (!empId || !dateVal) return;

        ui.fetchMsg.classList.remove('d-none', 'alert-danger', 'alert-success');
        ui.fetchMsg.classList.add('alert-info');
        ui.fetchMsg.textContent = "Fetching data...";
        
        // Clear table except if manual rows added? No, usually clear all.
        ui.tableBody.innerHTML = ''; 

        try {
            const formData = new FormData();
            formData.append('employee_id', empId);
            formData.append('date', dateVal);

            const response = await fetch('/api/fetch_morning_allocation', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.status === 'success') {
                const stockMap = data.opening_stock || {};
                
                // If we have opening stock, pre-fill rows
                if (Object.keys(stockMap).length > 0) {
                    ui.fetchMsg.textContent = "Loaded previous closing stock.";
                    ui.fetchMsg.classList.replace('alert-info', 'alert-success');
                    
                    for (const [pid, qty] of Object.entries(stockMap)) {
                        createRow(pid, qty); 
                    }
                } else {
                    ui.fetchMsg.textContent = "No previous stock found. Start fresh.";
                    ui.fetchMsg.classList.replace('alert-info', 'alert-warning');
                    // Add one empty row to start
                    createRow();
                }
            } else {
                ui.fetchMsg.textContent = data.message;
                ui.fetchMsg.classList.replace('alert-info', 'alert-danger');
            }
        } catch (err) {
            console.error(err);
            ui.fetchMsg.textContent = "Error fetching data.";
        }
    }

    // --- 3. ROW MANAGEMENT ---
    function createRow(preSelectedPid = null, openingQty = 0) {
        const tr = document.createElement("tr");
        
        let imgUrl = DEFAULT_IMG;
        let selectedHtml = productOptionsHtml;
        
        if (preSelectedPid) {
            const p = productsMap.get(String(preSelectedPid));
            if (p) {
                imgUrl = p.image || DEFAULT_IMG;
                // We select the option in HTML string
                selectedHtml = selectedHtml.replace(`value="${preSelectedPid}"`, `value="${preSelectedPid}" selected`);
            }
        }

        // VALIDATION: Given Stock limited to 2 digits, not required
        tr.innerHTML = `
            <td class="ps-4 text-muted row-index"></td>
            <td>
                <div class="img-box-small">
                    <img src="${imgUrl}" class="img-fixed-size product-img">
                </div>
            </td>
            <td>
                <select name="product_id[]" class="form-select border-0 shadow-sm fw-bold product-dropdown" required>
                    ${selectedHtml}
                </select>
            </td>
            <td>
                <input type="number" name="opening_stock[]" class="table-input opening" value="${openingQty}" readonly>
            </td>
            <td>
                <input type="number" name="given_stock[]" class="table-input given" placeholder="0" min="0" max="99" 
                       oninput="if(this.value.length > 2) this.value = this.value.slice(0, 2); recalculateRow(this.closest('tr'))">
            </td>
            <td>
                <input type="number" name="total_stock[]" class="table-input total" value="${openingQty}" readonly>
            </td>
            <td class="text-center">
                <button type="button" class="btn-remove-row">
                    <i class="fa-solid fa-times"></i>
                </button>
            </td>
        `;
        
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
        recalculateTotals();
    }

    // --- 4. CALCULATIONS ---
    window.recalculateRow = function(tr) {
        const open = parseInt(tr.querySelector(".opening").value) || 0;
        const given = parseInt(tr.querySelector(".given").value) || 0;
        const totalInput = tr.querySelector(".total");
        
        totalInput.value = open + given;
        recalculateTotals();
    };

    function updateRowData(tr, productId) {
        const img = tr.querySelector(".product-img");
        if (!productId) {
            img.src = DEFAULT_IMG;
            return;
        }
        const p = productsMap.get(String(productId));
        if (p) {
            img.src = p.image || DEFAULT_IMG;
        }
    }

    function recalculateTotals() {
        let tOpen = 0, tGiven = 0, tAll = 0;
        
        ui.tableBody.querySelectorAll("tr").forEach(tr => {
            tOpen += parseInt(tr.querySelector(".opening")?.value) || 0;
            tGiven += parseInt(tr.querySelector(".given")?.value) || 0;
            tAll += parseInt(tr.querySelector(".total")?.value) || 0;
        });

        if(ui.totals.opening) ui.totals.opening.textContent = tOpen;
        if(ui.totals.given) ui.totals.given.textContent = tGiven;
        if(ui.totals.all) ui.totals.all.textContent = tAll;
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }

    ui.addRowBtn.addEventListener("click", (e) => {
        e.preventDefault();
        createRow();
    });

    ui.employeeSelect.addEventListener("change", fetchStockData);
    ui.dateInput.addEventListener("change", fetchStockData);

    ui.tableBody.addEventListener("click", e => {
        if (e.target.closest(".btn-remove-row")) {
            if(confirm("Remove row?")) {
                e.target.closest("tr").remove();
                updateRowIndexes();
                recalculateTotals();
            }
        }
    });

    ui.tableBody.addEventListener("change", e => {
        if (e.target.matches(".product-dropdown")) {
            updateRowData(e.target.closest("tr"), e.target.value);
        }
    });

    ui.tableBody.addEventListener("input", e => {
        if (e.target.matches(".given")) {
            recalculateRow(e.target.closest("tr"));
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && e.target.tagName !== "BUTTON") {
            e.preventDefault();
        }
    });
});
