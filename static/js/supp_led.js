// supplier_ledger.js
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("paymentForm");
  if (form) {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  }
});