document.addEventListener('DOMContentLoaded', () => {
    // Note: This JS is for the card-based layout
    const searchInput = document.getElementById('searchName');
    const positionFilter = document.getElementById('filterPosition');
    const cityFilter = document.getElementById('filterCity');
    const statusFilter = document.getElementById('filterStatus');

    // Update selector to target cards
    const cards = document.querySelectorAll('.employee-card');
    const noResultsMessage = document.getElementById('noResultsMessage');

    function runFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const position = positionFilter.value;
        const city = cityFilter.value;
        const status = statusFilter.value;

        let resultsFound = 0;

        cards.forEach(card => {
            const nameMatch = card.dataset.name.includes(searchTerm);
            const positionMatch = (position === 'all' || card.dataset.position === position);
            const cityMatch = (city === 'all' || card.dataset.city === city);
            const statusMatch = (status === 'all' || card.dataset.status === status);

            if (nameMatch && positionMatch && cityMatch && statusMatch) {
                card.style.display = ''; // Show card
                resultsFound++;
            } else {
                card.style.display = 'none'; // Hide card
            }
        });

        // Toggle 'no results' message
        if (noResultsMessage) {
            noResultsMessage.style.display = (resultsFound === 0) ? 'block' : 'none';
        }
    }

    // Attach Listeners
    if (searchInput) searchInput.addEventListener('input', runFilters);
    if (positionFilter) positionFilter.addEventListener('change', runFilters);
    if (cityFilter) cityFilter.addEventListener('change', runFilters);
    if (statusFilter) statusFilter.addEventListener('change', runFilters);
});
