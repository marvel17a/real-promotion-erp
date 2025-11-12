document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchName');
    const positionFilter = document.getElementById('filterPosition');
    const cityFilter = document.getElementById('filterCity');
    const statusFilter = document.getElementById('filterStatus');

    const rows = document.querySelectorAll('.employee-row');
    const noResultsMessage = document.getElementById('noResultsMessage');
    const noResultsRow = document.getElementById('noResultsRow');

    function runFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const position = positionFilter.value;
        const city = cityFilter.value;
        const status = statusFilter.value;

        let resultsFound = 0;

        rows.forEach(row => {
            const nameMatch = row.dataset.name.includes(searchTerm);
            const positionMatch = (position === 'all' || row.dataset.position === position);
            const cityMatch = (city === 'all' || row.dataset.city === city);
            const statusMatch = (status === 'all' || row.dataset.status === status);

            if (nameMatch && positionMatch && cityMatch && statusMatch) {
                row.style.display = ''; // Show row
                resultsFound++;
            } else {
                row.style.display = 'none'; // Hide row
            }
        });

        // Toggle 'no results' message
        const showNoResults = resultsFound === 0;
        
        if (noResultsMessage) {
            noResultsMessage.style.display = showNoResults ? 'block' : 'none';
        }
        
        // Hide the "No employees found." row if we are filtering
        if (noResultsRow) {
             // Show default "empty" row only if there are 0 results AND 0 total rows to begin with
            if (rows.length > 0) {
                noResultsRow.style.display = 'none';
            }
        }
    }

    // Attach Listeners
    if (searchInput) searchInput.addEventListener('input', runFilters);
    if (positionFilter) positionFilter.addEventListener('change', runFilters);
    if (cityFilter) cityFilter.addEventListener('change', runFilters);
    if (statusFilter) statusFilter.addEventListener('change', runFilters);
});
