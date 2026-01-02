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
        settledMsg: getEl("settledMsg"),
        actionButtons: getEl("actionButtons"),
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
            p.stock = (p.stock === null || p.stock === undefined) ? 0 : parseInt(p.stock);
            productsMap.set(String(p.id), p);
            productOptionsHtml += `<option value="${p.id}">${p.name} (Stock: ${p.stock})</option>`;
        });
    }

    // --- FETCH LOGIC ---
    async function fetchStockData() {
        const empId = ui.employeeSelect.value;
        const dateVal = ui.dateInput.value;

        if (!empId || !dateVal) return;

        ui.fetchMsg.classList.remove("d-none");
        ui.tableBody.innerHTML = "";
        
        // Reset UI
        if(ui.settledMsg) ui.settledMsg.classList.add("d-none");
        if(ui.actionButtons) ui.actionButtons.classList.remove("d-none");

        try {
            const res = await fetch(`/api/fetch_stock?employee_id=${empId}&date=${dateVal}`);
            const data = await res.json();

            if (data.status === "success") {
                // Logic: If Settled, show message and hide buttons
                if (data.is_settled) {
                    if(ui.settledMsg) ui.settledMsg.classList.remove("d-none");
                    if(ui.actionButtons) ui.actionButtons.classList.add("d-none");
                }

                if (data.items && data.items.length > 0) {
                    data.items.forEach(item => {
                        addFetchedRow(item, data.source);
                    });
                }
                isRestockMode = (data.source === "restock");
                recalculateTotals();
            }
        } catch (err) {
            console.error(err);
        } finally {
            ui.fetchMsg.classList.add("d-none");
        }
    }

    function addFetchedRow(item, source) {
        const tr = document.createElement("tr");
        tr.className = "fade-in";
        
        // If Restock: opening_qty is existing opening, given_qty is existing given.
        // If New: opening_qty is Previous Remaining.
        
        let opQty = item.opening_qty || 0;
        let givenQty = item.given_qty || 0;
        let price = item.price || 0;
        let img = item.image || DEFAULT_IMG;

        // If restock mode, we show what was ALREADY given.
        // If new mode, we start with 0 given.
        
        // Check if settled to disable inputs
        const isSettled = ui.settledMsg && !ui.settledMsg.classList.contains("d-none");
        const disabledAttr = isSettled ? "disabled" : "";

        tr.innerHTML = `
            <td class="text-center fw-bold text-muted row-index"></td>
            <td><img src="${img}" class="rounded shadow-sm border" width="40" height="40"></td>
            <td>
                <input type="hidden" name="product_id[]" value="${item.product_id || item.id}">
                <span class="fw-bold text-dark">${item.name}</span>
            </td>
            <td><input type="number" name="price[]" class="form-control form-control-sm border-0 bg-transparent fw-bold price" value="${price}" readonly></td>
            <td><input type="number" name="opening[]" class="form-control form-control-sm text-center opening" value="${opQty}" readonly></td>
            <td><input type="number" name="given[]" class="form-control form-control-sm text-center fw-bold text-primary given" value="${source === 'restock' ? givenQty : 0}" ${disabledAttr}></td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold border-0 bg-light total" value="${opQty + (source === 'restock' ? givenQty : 0)}" readonly></td>
            <td>
                ${!isSettled && source !== 'restock' ? '<button type="button" class="btn btn-link text-danger btn-remove-row p-0"><i class="fa-solid fa-trash"></i></button>' : ''}
            </td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function createRow() {
        const tr = document.createElement("tr");
        tr.className = "fade-in";
        tr.innerHTML = `
            <td class="text-center fw-bold text-muted row-index"></td>
            <td><img src="${DEFAULT_IMG}" class="rounded shadow-sm border product-thumb" width="40" height="40"></td>
            <td>
                <select name="product_id[]" class="form-select form-select-sm product-dropdown fw-bold border-0 bg-light">
                    ${productOptionsHtml}
                </select>
            </td>
            <td><input type="number" name="price[]" class="form-control form-control-sm border-0 bg-transparent fw-bold price" readonly></td>
            <td><input type="number" name="opening[]" class="form-control form-control-sm text-center opening" value="0" readonly></td>
            <td><input type="number" name="given[]" class="form-control form-control-sm text-center fw-bold text-primary given" value="0"></td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold border-0 bg-light total" value="0" readonly></td>
            <td><button type="button" class="btn btn-link text-danger btn-remove-row p-0"><i class="fa-solid fa-trash"></i></button></td>
        `;
        ui.tableBody.appendChild(tr);
        updateRowIndexes();
    }

    function updateRowData(tr, productId) {
        const product = productsMap.get(productId);
        const imgEl = tr.querySelector(".product-thumb");
        const priceEl = tr.querySelector(".price");
        
        if (product) {
            imgEl.src = (product.image && !product.image.includes("via.placeholder")) ? product.image : DEFAULT_IMG;
            priceEl.value = product.price;
        } else {
            imgEl.src = DEFAULT_IMG;
            priceEl.value = "";
        }
        recalculateRow(tr);
    }

    function recalculateRow(tr) {
        const op = parseInt(tr.querySelector(".opening").value) || 0;
        const giv = parseInt(tr.querySelector(".given").value) || 0;
        tr.querySelector(".total").value = op + giv;
        recalculateTotals();
    }

    function recalculateTotals() {
        let tOp = 0, tGiv = 0, tAll = 0, tGrand = 0;
        
        ui.tableBody.querySelectorAll("tr").forEach(tr => {
            const op = parseInt(tr.querySelector(".opening").value) || 0;
            const giv = parseInt(tr.querySelector(".given").value) || 0;
            const price = parseFloat(tr.querySelector(".price").value) || 0;
            const tot = op + giv;
            
            tOp += op;
            tGiv += giv;
            tAll += tot;
            tGrand += (tot * price);
        });

        if(ui.totals.opening) ui.totals.opening.textContent = tOp;
        if(ui.totals.given) ui.totals.given.textContent = tGiv;
        if(ui.totals.all) ui.totals.all.textContent = tAll;
        if(ui.totals.grand) ui.totals.grand.textContent = tGrand.toFixed(2);
    }

    function updateRowIndexes() {
        ui.tableBody.querySelectorAll("tr").forEach((tr, i) => {
            tr.querySelector(".row-index").textContent = i + 1;
        });
    }

    // --- EVENTS ---
    if(ui.addRowBtn) ui.addRowBtn.addEventListener("click", (e) => { e.preventDefault(); createRow(); });
    if(ui.employeeSelect) ui.employeeSelect.addEventListener("change", fetchStockData);
    if(ui.dateInput) ui.dateInput.addEventListener("change", fetchStockData);

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
    
    // Clock
    setInterval(() => {
        const now = new Date();
        if(ui.clockDisplay) ui.clockDisplay.textContent = now.toLocaleTimeString();
        if(ui.timestampInput) ui.timestampInput.value = now.toISOString();
    }, 1000);
});
