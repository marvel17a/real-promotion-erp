// Initialize AOS (Animate On Scroll)
document.addEventListener('DOMContentLoaded', function() {
    AOS.init({
        duration: 800,
        easing: 'ease-out-cubic',
        once: true
    });
    
    // Navbar Scroll Effect (Optional: adds transparency logic if you want later)
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('shadow');
        } else {
            navbar.classList.remove('shadow');
        }
    });
});

// Auto-hide flash messages after 5 seconds
setTimeout(function() {
    let alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        let bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    });
}, 5000);
