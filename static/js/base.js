document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Initialize Animation Library
    AOS.init({ duration: 800, once: true });

    // 2. Theme Toggle Logic
    const themeToggleBtn = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;

    // Check saved preference
    const savedTheme = localStorage.getItem('erp_theme') || 'light';
    applyTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('erp_theme', newTheme);
    });

    function applyTheme(theme) {
        htmlElement.setAttribute('data-theme', theme);
        if (theme === 'dark') {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            themeIcon.style.color = "#FFD700"; // Yellow sun
        } else {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            themeIcon.style.color = ""; // Default color
        }
    }

    // 3. Navbar scroll effect (Glass gets stronger on scroll)
    window.addEventListener('scroll', () => {
        const nav = document.getElementById('mainNavbar');
        if (window.scrollY > 50) {
            nav.style.background = getComputedStyle(document.documentElement).getPropertyValue('--glass-bg');
            nav.style.boxShadow = "0 4px 30px rgba(0, 0, 0, 0.1)";
        }
    });
});
