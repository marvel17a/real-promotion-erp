document.addEventListener("DOMContentLoaded", () => {

    const getEl = id => document.getElementById(id);

    const ui = {
        employee: getEl("employee_id"),
        date: getEl("date"),
        body: document.querySelector("#productTable tbody"),
        addRow: getEl("addRow"),
        fetchMsg: getEl("fetchMsg"),
        totals: {
            opening: getEl("totalOpening"),
            given: getEl("totalGiven"),
            all: getEl("totalAll"),
            grand: getEl("grandTotal")
        }
    };

    if (!ui.employee || !ui.body) return;

    const products = Array.isArray(window.productsData) ? window.productsData : [];
    const productMap = new Map();
    const DEFAULT_IMG = "https://via.placeholder.com/55";

    let productOptions = `<option value="">-- Select --</option>`;
    products.forEach(p => {
        productMap.set(String(p.id), p);
        productOptions += `<option value="${p.id}">${p.name}</option>`;
    });

    let currentStock = {};

    async function fetchStock() {
        if (!ui.employee.value || !ui.date.value) return;

        ui.fetchMsg.innerHTML = "Loading...";

        try {
            const res = await fetch(`/api/fetch_stock?employee_id=${ui.employee.value}&date=${ui.date.value}`);
            const data = await res.json();
            currentStock = data || {};
            ui.fetchMsg.innerHTML = "Stock loaded";
            updateAllRows();
        } catch {
            ui.fetchMsg.innerHTML = "Error loading stock";
        }
    }

    function createRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="row-index"></td>
            <td><img src="${DEFAULT_IMG}" width="45"></td>
            <td>
                <select class="form-select product">
                    ${productOptions}
                </select>
            </td>
            <td><input class="form-control opening" readonly value="0"></td>
            <td><input class="form-control given" type="number" min="0"></td>
            <td><input class="form-control total" readonly value="0"></td>
            <td><input class="form-control price" readonly value="0.00"></td>
            <td><input class="form-control amount" readonly value="0.00"></td>
            <td><button type="button" class="btn btn-sm btn-danger remove">X</button></td>
        `;
        ui.body.appendChild(tr);
        indexRows();
    }

    function updateRow(row) {
        const pid = row.querySelector(".product").value;
        if (!pid) return;

        const product = productMap.get(pid);
        const opening = currentStock[pid]?.remaining || 0;
        const price = currentStock[pid]?.price || product?.price || 0;

        row.querySelector(".opening").value = opening;
        row.querySelector(".price").value = price;

        recalcRow(row);
    }

    function recalcRow(row) {
        const opening = +row.querySelector(".opening").value || 0;
        const given = +row.querySelector(".given").value || 0;
        const price = +row.querySelector(".price").value || 0;

        const total = opening + given;
        const amount = total * price;

        row.querySelector(".total").value = total;
        row.querySelector(".amount").value = amount.toFixed(2);

        recalcTotals();
    }

    function recalcTotals() {
        let o = 0, g = 0, t = 0, a = 0;
        ui.body.querySelectorAll("tr").forEach(r => {
            o += +r.querySelector(".opening").value || 0;
            g += +r.querySelector(".given").value || 0;
            t += +r.querySelector(".total").value || 0;
            a += +r.querySelector(".amount").value || 0;
        });
        ui.totals.opening.textContent = o;
        ui.totals.given.textContent = g;
        ui.totals.all.textContent = t;
        ui.totals.grand.textContent = a.toFixed(2);
    }

    function updateAllRows() {
        ui.body.querySelectorAll("tr").forEach(updateRow);
    }

    function indexRows() {
        ui.body.querySelectorAll(".row-index").forEach((c, i) => c.textContent = i + 1);
    }

    ui.addRow.onclick = createRow;
    ui.employee.onchange = fetchStock;
    ui.date.onchange = fetchStock;

    ui.body.addEventListener("input", e => {
        if (e.target.classList.contains("given")) {
            recalcRow(e.target.closest("tr"));
        }
    });

    ui.body.addEventListener("change", e => {
        if (e.target.classList.contains("product")) {
            updateRow(e.target.closest("tr"));
        }
    });

    ui.body.addEventListener("click", e => {
        if (e.target.classList.contains("remove")) {
            e.target.closest("tr").remove();
            indexRows();
            recalcTotals();
        }
    });

});
