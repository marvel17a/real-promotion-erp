// static/js/employee.js

// --------- Image preview (add/edit) ----------
document.addEventListener('change', function (e) {
  if (!e.target) return;
  if (e.target.id === 'imageInput') {
    const input = e.target;
    const preview = document.getElementById('imagePreview');
    const file = input.files && input.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function (ev) {
        preview.src = ev.target.result;
        preview.style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
  }
});

// --------- PINCODE lookup (India) ----------
function lookupPincode(pin) {
  if (!pin || pin.length !== 6) return;
  fetch(`/api/pincode_lookup/${pin}`)
    .then(r => r.json())
    .then(res => {
      if (res.success) {
        const cityEl = document.getElementById('city');
        const stateEl = document.getElementById('state');
        if (cityEl) cityEl.value = res.city;
        if (stateEl) stateEl.value = res.state;
      } else {
        // clear if not found
        const cityEl = document.getElementById('city');
        const stateEl = document.getElementById('state');
        if (cityEl) cityEl.value = '';
        if (stateEl) stateEl.value = '';
      }
    })
    .catch(err => console.error('Pincode lookup error', err));
}

document.addEventListener('input', function (e) {
  if (!e.target) return;
  if (e.target.id === 'pincode') {
    const val = e.target.value.replace(/\D/g,''); // remove non-digits
    e.target.value = val.slice(0, 6); // max 6 digits
    if (val.length === 6) lookupPincode(val);
  }
});

// --------- Phone numeric-only and max 10 digits ----------
document.addEventListener('input', function (e) {
  if (!e.target) return;
  if (e.target.name === 'phone' || e.target.id === 'phone') {
    const val = e.target.value.replace(/\D/g, ''); // numeric only
    e.target.value = val.slice(0, 10); // max 10 digits
  }
  if (e.target.name === 'emergency_contact' || e.target.id === 'emergency_contact') {
    const val = e.target.value.replace(/\D/g, '');
    e.target.value = val.slice(0, 10);
  }
});

// --------- Flatpickr init for DOB fields ----------
document.addEventListener('DOMContentLoaded', function () {
  if (window.flatpickr) {
    flatpickr(".dob-picker", {
      dateFormat: "d-m-Y",      // show dd-mm-yyyy
      maxDate: "today",
      allowInput: true,
    });
  }
});

// --------- Form validation (email + phone + required) ----------
function isValidEmail(email) {
  // simple RFC-like validation
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(String(email).toLowerCase());
}

function validateEmployeeForm(form) {
  const name = form.querySelector('[name="name"]');
  const email = form.querySelector('[name="email"]');
  const phone = form.querySelector('[name="phone"]');
  const pincode = form.querySelector('[name="pincode"]');

  // Name required
  if (!name || !name.value.trim()) {
    alert('Please enter employee name.');
    name && name.focus();
    return false;
  }

  // Email optional but if filled must be valid
  if (email && email.value.trim()) {
    if (!isValidEmail(email.value.trim())) {
      alert('Please enter a valid email address.');
      email.focus();
      return false;
    }
  }

  // Phone optional but if filled must be exactly 10 digits
  if (phone && phone.value.trim()) {
    if (!/^\d{10}$/.test(phone.value.trim())) {
      alert('Please enter a valid 10-digit mobile number (digits only).');
      phone.focus();
      return false;
    }
  }

  // Pincode optional but if filled it must be 6 digits
  if (pincode && pincode.value.trim()) {
    if (!/^\d{6}$/.test(pincode.value.trim())) {
      alert('Please enter a valid 6-digit Indian PIN code.');
      pincode.focus();
      return false;
    }
  }

  return true;
}

// Attach validation to all employee forms (add & edit)
document.addEventListener('submit', function (e) {
  const form = e.target;
  if (!form) return;

  if (form.matches('#addEmployeeForm') || form.matches('#editEmployeeForm')) {
    if (!validateEmployeeForm(form)) {
      e.preventDefault();
      return false;
    }
  }
});

// --------- Toggle employee status (AJAX) ----------
document.addEventListener('click', function (e) {
  const target = e.target;
  if (!target) return;

  // handle buttons inside
  const btn = target.closest('#toggleStatusBtn');
  if (btn) {
    const empId = btn.dataset.id;
    if (!empId) return;
    fetch(`/employee_toggle_status/${empId}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'}
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        // reload or update
        location.reload();
      } else {
        alert('Could not toggle status.');
      }
    })
    .catch(err => { console.error(err); alert('Error toggling status'); });
  }
});
