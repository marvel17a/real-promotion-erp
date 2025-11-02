// static/js/main.js

// === Sidebar or Navbar Active Link Indicator ===
document.addEventListener('DOMContentLoaded', function () {
  const links = document.querySelectorAll('.navbar a');
  const currentURL = window.location.href;

  links.forEach(link => {
    if (currentURL.includes(link.getAttribute('href'))) {
      link.classList.add('active');
    }
  });
});

// === Button Hover Effect ===
document.querySelectorAll(".btn, .submit-btn, .add-btn").forEach(button => {
  button.addEventListener("mouseover", () => {
    button.style.transform = "scale(1.05)";
    button.style.transition = "transform 0.2s ease";
  });

  button.addEventListener("mouseout", () => {
    button.style.transform = "scale(1)";
  });
});

// === Animate Section Entry ===
const animatedSections = document.querySelectorAll(".animated-section");
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("fade-in");
      observer.unobserve(entry.target);
    }
  });
}, {
  threshold: 0.3
});

animatedSections.forEach(section => {
  observer.observe(section);
});

// === Table Row Hover ===
document.querySelectorAll("table.modern-table tr").forEach(row => {
  row.addEventListener("mouseenter", () => {
    row.style.backgroundColor = "#f1f1f1";
  });
  row.addEventListener("mouseleave", () => {
    row.style.backgroundColor = "";
  });
});

// === Smooth Scroll to Top (Optional) ===
const scrollToTopBtn = document.getElementById("scrollToTop");
if (scrollToTopBtn) {
  scrollToTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}
