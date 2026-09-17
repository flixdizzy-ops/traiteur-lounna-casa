document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');

  if (navToggle && nav) {
    navToggle.addEventListener('click', () => {
      nav.classList.toggle('open');
    });
  }

  const cartCount = document.getElementById('cartCount');
  if (cartCount) {
    const stored = sessionStorage.getItem('lounna_cart_count');
    if (stored) {
      cartCount.textContent = stored;
    }
  }
});
