// ===========================
// Product Sales Charts Script
// ===========================

// Ensure salesData exists
if (typeof salesData !== "undefined" && Array.isArray(salesData)) {

    // -----------------------------
    // BAR CHART — Quantity Sold
    // -----------------------------
    const qtyLabels = salesData.map(item => item.product_name);
    const qtyValues = salesData.map(item => item.total_sold_qty);

    new Chart(document.getElementById('qtyChart'), {
        type: 'bar',
        data: {
            labels: qtyLabels,
            datasets: [{
                label: 'Total Quantity Sold',
                data: qtyValues,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        }
    });


    // -----------------------------
    // LINE CHART — Revenue Trend
    // -----------------------------
    const revenueValues = salesData.map(item => item.total_revenue);

    new Chart(document.getElementById('revenueChart'), {
        type: 'line',
        data: {
            labels: qtyLabels,
            datasets: [{
                label: 'Revenue (₹)',
                data: revenueValues,
                fill: false,
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }]
        }
    });


    // -----------------------------
    // PIE CHART — Category-wise Sold Qty
    // -----------------------------
    const categoryTotals = {};

    salesData.forEach(item => {
        const cat = item.category_name || "Uncategorized";
        if (!categoryTotals[cat]) categoryTotals[cat] = 0;
        categoryTotals[cat] += item.total_sold_qty;
    });

    new Chart(document.getElementById('categoryChart'), {
        type: 'pie',
        data: {
            labels: Object.keys(categoryTotals),
            datasets: [{
                data: Object.values(categoryTotals),
                backgroundColor: [
                    '#007bff', '#6610f2', '#6f42c1',
                    '#e83e8c', '#fd7e14', '#ffc107',
                    '#20c997', '#17a2b8', '#dc3545'
                ]
            }]
        }
    });
}
