// ---------------------------------------
// Live warning when stock <= threshold
// ---------------------------------------

document.addEventListener('DOMContentLoaded', function () {

    const stockInput = document.querySelector('input[name="stock"]');
    const thresholdInput = document.querySelector('input[name="low_stock_threshold"]');

    if (!stockInput || !thresholdInput) return;

    function checkWarning() {
        const stock = Number(stockInput.value || 0);
        const threshold = Number(thresholdInput.value || 0);

        let warn = document.getElementById('lowStockWarn');
        if (!warn) {
            warn = document.createElement('div');
            warn.id = 'lowStockWarn';
            warn.style.marginTop = "6px";
            warn.style.fontWeight = "700";
            thresholdInput.parentNode.appendChild(warn);
        }

        if (stock <= threshold) {
            warn.style.color = "#c70039";
            warn.textContent = `⚠ Warning: Stock (${stock}) is at or below threshold (${threshold}).`;
        } else {
            warn.textContent = "";
        }
    }

    stockInput.addEventListener('input', checkWarning);
    thresholdInput.addEventListener('input', checkWarning);

    // Run once on page load
    checkWarning();

});
