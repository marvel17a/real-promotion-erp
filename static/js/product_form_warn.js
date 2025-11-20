// ---------------------------------------------------
// Live Warning: Show alert if stock <= threshold
// ---------------------------------------------------

document.addEventListener("DOMContentLoaded", function () {

    const stock = document.querySelector('input[name="stock"]');
    const threshold = document.querySelector('input[name="low_stock_threshold"]');

    if (!stock || !threshold) return;

    function updateWarning() {
        const s = Number(stock.value || 0);
        const t = Number(threshold.value || 0);

        let warn = document.getElementById("lowStockWarn");

        if (!warn) {
            warn = document.createElement("div");
            warn.id = "lowStockWarn";
            warn.style.marginTop = "6px";
            warn.style.fontWeight = "700";
            warn.style.fontSize = "14px";
            threshold.parentNode.appendChild(warn);
        }

        if (s <= t) {
            warn.style.color = "#c70039";
            warn.textContent = `⚠ Warning: Stock (${s}) is at or below threshold (${t}).`;
        } else {
            warn.textContent = "";
        }
    }

    stock.addEventListener("input", updateWarning);
    threshold.addEventListener("input", updateWarning);

    updateWarning(); // run on load
});
