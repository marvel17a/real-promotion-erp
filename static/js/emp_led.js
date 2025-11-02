// This code runs when the page is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // --- CONFIGURATION ---
    // Get the employee ID from the URL, e.g., ledger.html?id=5
    const urlParams = new URLSearchParams(window.location.search);
    const employeeId = urlParams.get('id');

    if (!employeeId) {
        document.body.innerHTML = '<h1>Error: No Employee ID provided in URL.</h1>';
        return;
    }

    // Store form elements in variables for easy access
    const transactionForm = document.getElementById('transaction-form');
    const employeeIdInput = document.getElementById('employee-id-input');
    employeeIdInput.value = employeeId; // Set the hidden input value

    // --- INITIAL DATA FETCH ---
    fetchLedgerData(employeeId);


    // --- EVENT LISTENERS ---
    transactionForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Prevent default form submission

        const formData = {
            employee_id: parseInt(employeeId),
            transaction_type: document.getElementById('transaction-type').value,
            amount: parseFloat(document.getElementById('transaction-amount').value),
            description: document.getElementById('transaction-description').value
        };

        try {
            const response = await fetch('/api/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                transactionForm.reset(); // Clear the form
                fetchLedgerData(employeeId); // Refresh the transaction lists
            } else {
                alert('Failed to add transaction.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred.');
        }
    });
});


// --- CORE FUNCTIONS ---

/**
 * Fetches all ledger data from the API and updates the UI
 * @param {string} employeeId - The ID of the employee
 */
async function fetchLedgerData(employeeId) {
    try {
        const response = await fetch(`/api/employee/${employeeId}/ledger`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        updateUI(data);

    } catch (error) {
        console.error('Failed to fetch ledger data:', error);
        document.getElementById('employee-name').innerText = 'Failed to load data.';
    }
}

/**
 * Updates the entire page with new data from the API
 * @param {object} data - The complete ledger data object from the API
 */
function updateUI(data) {
    // 1. Update Employee Header
    const employeeInfo = data.employee_info;
    document.getElementById('employee-image').src = `/static/images/${employeeInfo.image}`; // Assuming images are in a static folder
    document.getElementById('employee-name').innerText = employeeInfo.name;
    document.getElementById('employee-position').innerText = employeeInfo.position;
    document.getElementById('balance-amount').innerText = `₹${data.summary.balance.toFixed(2)}`;
    
    // Change balance color based on value
    const balanceEl = document.getElementById('balance-amount');
    balanceEl.style.color = data.summary.balance > 0 ? 'red' : 'green';


    // 2. Update Transaction Lists
    const debitsList = document.getElementById('debits-ul');
    const creditsList = document.getElementById('credits-ul');
    debitsList.innerHTML = ''; // Clear existing items
    creditsList.innerHTML = ''; // Clear existing items

    data.transactions.forEach(tx => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <span>${tx.description}</span>
            <strong>₹${tx.amount.toFixed(2)}</strong>
            <small>${new Date(tx.transaction_date).toLocaleDateString()}</small>
            <button class="delete-btn" onclick="deleteTransaction(${tx.transaction_id}, ${employeeInfo.id})">X</button>
        `;

        if (tx.transaction_type === 'debit') {
            debitsList.appendChild(listItem);
        } else {
            creditsList.appendChild(listItem);
        }
    });
}

/**
 * Deletes a transaction and refreshes the ledger
 * @param {number} transactionId - The ID of the transaction to delete
 * @param {number} employeeId - The employee ID, needed to refresh the data
 */
async function deleteTransaction(transactionId, employeeId) {
    if (!confirm('Are you sure you want to delete this transaction?')) {
        return;
    }

    try {
        const response = await fetch(`/api/transaction/${transactionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            fetchLedgerData(employeeId); // Refresh the ledger view
        } else {
            alert('Failed to delete transaction.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while deleting.');
    }
}