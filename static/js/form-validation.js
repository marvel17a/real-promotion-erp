function validateProductForm() {
    let name = document.getElementById('name').value.trim();
    let qty = document.getElementById('quantity').value;
    let price = document.getElementById('price').value;

    if (name === "" || qty === "" || price === "") {
        alert("Please fill all required fields!");
        return false;
    }
    if (qty < 0 || price < 0) {
        alert("Quantity and price must be positive!");
        return false;
    }
    return true;
}

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("employeeForm");

    form.addEventListener("submit", function (e) {
        let valid = true;
        let name = document.querySelector("[name='name']").value.trim();
        let designation = document.querySelector("[name='designation']").value.trim();
        let phone = document.querySelector("[name='phone']").value.trim();
        let email = document.querySelector("[name='email']").value.trim();
        let city = document.querySelector("[name='city']").value.trim();

        let photo = document.querySelector("[name='profile_photo']").files[0];
        let aadhar = document.querySelector("[name='aadhar_pdf']").files[0];
        let pan = document.querySelector("[name='pan_pdf']").files[0];
        let resume = document.querySelector("[name='resume_pdf']").files[0];

        // Name Validation
        if (!/^[A-Za-z\s]{3,}$/.test(name)) {
            alert("Name must be at least 3 characters and contain only letters and spaces.");
            valid = false;
        }

        // Designation Validation
        if (designation.length < 2) {
            alert("Designation must be at least 2 characters.");
            valid = false;
        }

        // Phone Validation
        if (!/^\d{10}$/.test(phone)) {
            alert("Phone number must be exactly 10 digits.");
            valid = false;
        }

        // Email Validation
        let emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email)) {
            alert("Please enter a valid email address.");
            valid = false;
        }

        // City Validation
        if (city.length < 2) {
            alert("City name must be at least 2 characters.");
            valid = false;
        }

        // File Validations
        if (photo && !photo.type.startsWith("image/")) {
            alert("Profile photo must be an image file.");
            valid = false;
        }
        if (aadhar && aadhar.type !== "application/pdf") {
            alert("Aadhar card must be a PDF file.");
            valid = false;
        }
        if (pan && pan.type !== "application/pdf") {
            alert("PAN card must be a PDF file.");
            valid = false;
        }
        if (resume && resume.type !== "application/pdf") {
            alert("Resume must be a PDF file.");
            valid = false;
        }

        // Stop form submission if invalid
        if (!valid) {
            e.preventDefault();
        }
    });
});
