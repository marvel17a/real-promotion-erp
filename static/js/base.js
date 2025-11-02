
  // Optional: highlight active nav link by path
  const links = document.querySelectorAll(".navbar .nav-link");
  links.forEach(link => {
    if (link.getAttribute("href") === window.location.pathname) {
      link.classList.add("active");
    }
  });
document.addEventListener('DOMContentLoaded', () => {
  // Highlight active link
  const current = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === current) {
      link.classList.add('active');
    }
  });
});
