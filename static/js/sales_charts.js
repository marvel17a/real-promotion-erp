// Product Sales Charts

if (typeof salesData !== "undefined") {

    const qtyLabels = salesData.map(p => p.product_name);
    const qtyVals = salesData.map(p => p.total_sold_qty);
    const revenueVals = salesData.map(p => p.total_revenue);

    new Chart(document.getElementById("qtyChart"), {
        type: "bar",
        data: {
            labels: qtyLabels,
            datasets: [{
                label: "Sold Quantity",
                data: qtyVals,
                backgroundColor: "rgba(54,162,235,0.6)"
            }]
        }
    });

    new Chart(document.getElementById("revenueChart"), {
        type: "line",
        data: {
            labels: qtyLabels,
            datasets: [{
                label: "Revenue (₹)",
                data: revenueVals,
                borderColor: "rgb(255,99,132)",
                fill: false
            }]
        }
    });

    const catTotals = {};
    salesData.forEach(item => {
        const cat = item.category_name || "Uncategorized";
        catTotals[cat] = (catTotals[cat] || 0) + item.total_sold_qty;
    });

    new Chart(document.getElementById("categoryChart"), {
        type: "pie",
        data: {
            labels: Object.keys(catTotals),
            datasets: [{
                data: Object.values(catTotals),
                backgroundColor: ["#007bff","#6610f2","#ffc107","#dc3545","#28a745"]
            }]
        }
    });
}
