document.addEventListener('DOMContentLoaded', () => {
    const viewGridBtn = document.getElementById('viewGrid');
    const viewListBtn = document.getElementById('viewList');
    const displayArea = document.getElementById('employeeDisplayArea');
    const gridView = document.querySelector('.employee-grid');
    const listView = document.querySelector('.employee-list');

    const searchInput = document.getElementById('searchName');
    const positionFilter = document.getElementById('filterPosition');
    const cityFilter = document.getElementById('filterCity');
    const statusFilter = document.getElementById('filterStatus');

    const cards = document.querySelectorAll('.employee-card');
    const rows = document.querySelectorAll('.employee-row');
    const noResultsMessage = document.getElementById('noResultsMessage');

    // 1. View Toggler
    viewGridBtn.addEventListener('click', () => {
        displayArea.classList.remove('view-list');
        displayArea.classList.add('view-grid');
        viewGridBtn.classList.add('active');
        viewListBtn.classList.remove('active');
    });

    viewListBtn.addEventListener('click', () => {
        displayArea.classList.remove('view-grid');
        displayArea.classList.add('view-list');
        viewListBtn.classList.add('active');
        viewGridBtn.classList.remove('active');
    });

    // 2. Filter Function
    function runFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const position = positionFilter.value;
        const city = cityFilter.value;
        const status = statusFilter.value;

        let resultsFound = 0;

        // Filter both cards and rows simultaneously
        const itemsToFilter = [
            ...cards,
            ...rows
        ];

        itemsToFilter.forEach(item => {
            const nameMatch = item.dataset.name.includes(searchTerm);
            const positionMatch = (position === 'all' || item.dataset.position === position);
            const cityMatch = (city === 'all' || item.dataset.city === city);
            const statusMatch = (status === 'all' || item.dataset.status === status);

            if (nameMatch && positionMatch && cityMatch && statusMatch) {
                item.style.display = ''; // Show item
                // Only count results once (e.g., based on cards)
                if (item.classList.contains('employee-card')) {
                    resultsFound++;
                }
            } else {
                item.style.display = 'none'; // Hide item
            }
        });

        // Show 'No Results' message if applicable
        if (noResultsMessage) {
            noResultsMessage.style.display = (resultsFound === 0) ? 'block' : 'none';
        }
    }

    // 3. Attach Listeners
    searchInput.addEventListener('input', runFilters);
    positionFilter.addEventListener('change', runFilters);
    cityFilter.addEventListener('change', runFilters);
    statusFilter.addEventListener('change', runFilters);
});
