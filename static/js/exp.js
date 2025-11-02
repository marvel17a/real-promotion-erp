document.addEventListener("DOMContentLoaded", () => {
    const notesTextarea = document.getElementById("notes");
    const categoryInput = document.getElementById("category");
    const suggestButton = document.getElementById("suggestCategoryBtn");
    const spinner = suggestButton.querySelector(".spinner-border");

    if (!suggestButton) return;

    /**
     * Calls the backend API to get a category suggestion from the Gemini LLM.
     */
    async function getCategorySuggestion() {
        const notes = notesTextarea.value.trim();
        if (!notes) {
            alert("Please enter a description in the 'Notes' field first.");
            return;
        }

        // Show loading state
        suggestButton.disabled = true;
        spinner.classList.remove("d-none");

        try {
            const response = await fetch('/api/suggest_expense_category', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notes: notes }),
            });

            if (!response.ok) {
                throw new Error('Failed to get suggestion from the server.');
            }

            const data = await response.json();
            
            if (data.category) {
                categoryInput.value = data.category;
            } else if (data.error) {
                throw new Error(data.error);
            }

        } catch (error) {
            console.error("Error fetching category suggestion:", error);
            alert(`Could not get suggestion: ${error.message}`);
        } finally {
            // Hide loading state
            suggestButton.disabled = false;
            spinner.classList.add("d-none");
        }
    }

    suggestButton.addEventListener("click", getCategorySuggestion);
});
