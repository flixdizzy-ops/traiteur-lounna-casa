document.addEventListener('DOMContentLoaded', () => {
  const langButtons = document.querySelectorAll('.lang-switcher a');
  langButtons.forEach((button) => {
    button.addEventListener('click', () => {
      langButtons.forEach((btn) => btn.classList.remove('active'));
      button.classList.add('active');
    });
  });
});
