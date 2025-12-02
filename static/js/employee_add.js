document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("employeeForm");

    form.addEventListener("submit", function (e) {
        let valid = true;
        let messages = [];

        // Full Name validation
        const name = form.name.value.trim();
        if (name.length < 3) {
            valid = false;
            messages.push("Full Name must be at least 3 characters.");
        }

        // Phone validation (only 10 digits)
        const phone = form.phone.value.trim();
        const phoneRegex = /^[0-9]{10}$/;
        if (!phoneRegex.test(phone)) {
            valid = false;
            messages.push("Phone number must be exactly 10 digits.");
        }

        // Email validation (if entered)
        const email = form.email.value.trim();
        if (email !== "") {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                valid = false;
                messages.push("Please enter a valid email address.");
            }
        }

        // Position validation
        if (form.position_id.value === "") {
            valid = false;
            messages.push("Please select a Position.");
        }

        // Department validation
        if (form.department_id.value === "") {
            valid = false;
            messages.push("Please select a Department.");
        }

        // Date of Birth validation (must not be future date)
        const dob = form.dob.value;
        if (dob) {
            const dobDate = new Date(dob);
            const today = new Date();
            if (dobDate > today) {
                valid = false;
                messages.push("Date of Birth cannot be in the future.");
            }
        }

        // Joining Date validation (must not be before DOB)
        const joiningDate = form.joining_date.value;
        if (dob && joiningDate) {
            const dobDate = new Date(dob);
            const joinDate = new Date(joiningDate);
            if (joinDate < dobDate) {
                valid = false;
                messages.push("Joining Date cannot be before Date of Birth.");
            }
        }

        // Emergency Contact validation (10 digits)
        const emergencyContact = form.emergency_contact.value.trim();
        if (emergencyContact && !/^[0-9]{10}$/.test(emergencyContact)) {
            valid = false;
            messages.push("Emergency Contact must be exactly 10 digits.");
        }

        // Aadhar validation (12 digits)
        const aadhar = form.aadhar_no.value.trim();
        if (aadhar && !/^[0-9]{12}$/.test(aadhar)) {
            valid = false;
            messages.push("Aadhar number must be exactly 12 digits.");
        }

        // Photo validation (only image files)
        const image = form.image.files[0];
        if (image) {
            const allowedTypes = ["image/jpeg", "image/png", "image/jpg"];
            if (!allowedTypes.includes(image.type)) {
                valid = false;
                messages.push("Photo must be a JPG or PNG image.");
            }
        }

        // Show errors if invalid
        if (!valid) {
            e.preventDefault();
            alert(messages.join("\n"));
        }
    });

    // Prevent typing more than 10 digits in phone & emergency contact
    form.phone.addEventListener("input", function () {
        this.value = this.value.replace(/\D/g, "").slice(0, 10);
    });
    form.emergency_contact.addEventListener("input", function () {
        this.value = this.value.replace(/\D/g, "").slice(0, 10);
    });
    form.aadhar_no.addEventListener("input", function () {
        this.value = this.value.replace(/\D/g, "").slice(0, 12);
    });
});
