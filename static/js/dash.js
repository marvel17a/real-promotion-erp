document.addEventListener('DOMContentLoaded', () => {

    // --- Chart Contexts ---
    const salesCtx = document.getElementById('weeklySalesChart')?.getContext('2d');
    const productsCtx = document.getElementById('topProductsChart')?.getContext('2d');

    // --- Loaders ---
    const salesLoader = document.getElementById('salesChartLoader');
    const productsLoader = document.getElementById('productsChartLoader');

    // --- Chart Objects (to be initialized later) ---
    let weeklySalesChart = null;
    let topProductsChart = null;

    /**
     * Fetches chart data from our new API endpoint.
     */
    async function fetchChartData() {
        try {
            // Show loaders
            if (salesLoader) salesLoader.style.display = 'flex';
            if (productsLoader) productsLoader.style.display = 'flex';

            const response = await fetch('/api/dashboard-charts');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Once data is fetched, create the charts
            if (salesCtx) {
                createWeeklySalesChart(data.weekly_sales);
            }
            if (productsCtx) {
                createTopProductsChart(data.top_products);
            }

        } catch (error) {
            console.error('Failed to fetch dashboard chart data:', error);
            // You could show an error message in the chart cards here
        } finally {
            // Hide loaders
            if (salesLoader) salesLoader.style.display = 'none';
            if (productsLoader) productsLoader.style.display = 'none';
        }
    }

    /**
     * Creates the Weekly Sales Line Chart
     * @param {Object} salesData - Data from the API (labels and values)
     */
    function createWeeklySalesChart(salesData) {
        if (!salesData || !salesData.labels || !salesData.data) {
            console.error('Invalid sales data for chart.');
            return;
        }

        if (weeklySalesChart) {
            weeklySalesChart.destroy();
        }
        
        weeklySalesChart = new Chart(salesCtx, {
            type: 'line',
            data: {
                labels: salesData.labels, // e.g., ['Mon', 'Tue', ...]
                datasets: [{
                    label: 'Sales (₹)',
                    data: salesData.data, // e.g., [1200, 1900, ...]
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                    pointRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Sales: ₹${context.raw.toLocaleString()}`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Creates the Top Products Doughnut Chart
     * @param {Object} productsData - Data from the API (labels and values)
     */
    function createTopProductsChart(productsData) {
        if (!productsData || !productsData.labels || !productsData.data) {
            console.error('Invalid products data for chart.');
            return;
        }

        if (topProductsChart) {
            topProductsChart.destroy();
        }

        topProductsChart = new Chart(productsCtx, {
            type: 'doughnut',
            data: {
                labels: productsData.labels, // e.g., ['Product A', 'Product B', ...]
                datasets: [{
                    label: 'Units Sold',
                    data: productsData.data, // e.g., [50, 35, ...]
                    backgroundColor: [
                        '#3b82f6',
                        '#10b981',
                        '#f97316',
                        '#ef4444',
                        '#8b5cf6',
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            boxWidth: 12,
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} units`;
                            }
                        }
                    }
                }
            }
        });
    }

    // --- Initial Load ---
    // Check if Chart.js is loaded and contexts exist
    if (typeof Chart !== 'undefined' && (salesCtx || productsCtx)) {
        fetchChartData();
    } else {
        console.warn('Chart.js not loaded or canvas elements not found.');
        if (salesLoader) salesLoader.style.display = 'none';
        if (productsLoader) productsLoader.style.display = 'none';
    }
});
