document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchProduct');
    const categoryFilter = document.getElementById('filterCategory');

    // This selector targets the wrapping column for each card
    const cards = document.querySelectorAll('.product-card-filter');
    const noResultsMessage = document.getElementById('noResultsMessage');

    function runFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const category = categoryFilter.value;

        let resultsFound = 0;

        cards.forEach(card => {
            const nameMatch = card.dataset.name.includes(searchTerm);
            const categoryMatch = (category === 'all' || card.dataset.category === category);

            if (nameMatch && categoryMatch) {
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
    if (categoryFilter) categoryFilter.addEventListener('change', runFilters);
});
