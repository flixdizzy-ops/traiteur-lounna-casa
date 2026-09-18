(() => {
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta?.content;

  if (csrfToken) {
    window.fetch = ((originalFetch) => (input, init = {}) => {
      const requestUrl = typeof input === 'string' ? input : input?.url || '';
      if (requestUrl.startsWith('/') || requestUrl.startsWith(window.location.origin)) {
        const headers = new Headers(init.headers || {});
        if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', csrfToken);
        init.headers = headers;
      }
      return originalFetch(input, init);
    })(window.fetch.bind(window));
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!csrfToken) return;
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
      if (!form.querySelector('input[name="csrf_token"]')) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = csrfToken;
        form.appendChild(input);
      }
    });
  });
})();
