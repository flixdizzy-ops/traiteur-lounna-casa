document.addEventListener('DOMContentLoaded', () => {
  const cartCount = document.getElementById('cartCount');
  const orderForm = document.querySelector('[data-order-form]');

  function updateCartBadge(count) {
    if (cartCount) cartCount.textContent = count;
    sessionStorage.setItem('lounna_cart_count', String(count));
  }

  function fetchCart() {
    return fetch('/api/cart')
      .then((response) => response.json())
      .then((data) => data)
      .catch(() => ({ items: [], total: 0 }));
  }

  function syncOrderForm(items, total) {
    if (!orderForm) return;
    const itemsField = orderForm.querySelector('input[name="items"]');
    const totalField = orderForm.querySelector('input[name="total"]');
    if (itemsField) itemsField.value = JSON.stringify(items);
    if (totalField) totalField.value = String(total || 0);
    const totalLabel = document.querySelector('[data-cart-total]');
    const totalFinal = document.querySelector('[data-cart-total-final]');
    if (totalLabel) totalLabel.textContent = `${Number(total || 0).toFixed(2)} MAD`;
    if (totalFinal) totalFinal.textContent = `${Number(total || 0).toFixed(2)} MAD`;
  }

  function renderCartOnPage(items, total) {
    const cartList = document.querySelector('[data-cart-list]');
    if (!cartList) return;

    if (!items.length) {
      cartList.innerHTML = '<div class="empty-state">Votre panier est vide.</div>';
      updateCartBadge(0);
      syncOrderForm([], 0);
      return;
    }

    cartList.innerHTML = items.map((item) => `
      <div class="cart-item">
        <img src="${item.image}" alt="${item.name}">
        <div>
          <div class="item-title">${item.name}</div>
          <div class="item-qty">Quantité: ${item.quantity}</div>
        </div>
        <div class="item-price">${Number(item.subtotal).toFixed(2)} MAD</div>
      </div>
    `).join('');

    const count = items.reduce((sum, item) => sum + item.quantity, 0);
    updateCartBadge(count);
    syncOrderForm(items, total);
  }

  const addButtons = document.querySelectorAll('[data-add-to-cart]');
  addButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const productId = button.dataset.productId;
      const quantity = Number(button.dataset.quantity || document.querySelector('[data-product-qty]')?.value || 1);
      fetch('/api/cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item: { id: productId, quantity } })
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            updateCartBadge(data.cart_count);
            fetchCart().then((cart) => renderCartOnPage(cart.items, cart.total));
          }
        });
    });
  });

  if (orderForm) {
    orderForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const form = new FormData(orderForm);
      const itemsValue = form.get('items') || '[]';
      const preferredDate = form.get('preferred_date') || '';
      const preferredTime = form.get('preferred_time') || '';
      const payload = {
        customer_name: form.get('customer_name'),
        phone: form.get('phone'),
        city: form.get('city'),
        delivery_address: form.get('delivery_address'),
        preferred_datetime: `${preferredDate} ${preferredTime}`.trim(),
        notes: form.get('notes'),
        items: JSON.parse(itemsValue),
        total: Number(form.get('total') || 0)
      };

      if (!payload.customer_name || !payload.phone || !payload.city || !payload.delivery_address || !preferredDate || !preferredTime || !payload.items.length) {
        alert('Veuillez remplir vos informations, la date et l’heure, puis ajouter au moins un produit.');
        return;
      }

      const lines = payload.items.map((item) => `- ${item.name} × ${item.quantity} — ${Number(item.price).toFixed(2)} DH`);
      const message = [
        'Bonjour TRAITEUR LOUNNA CASA,',
        '',
        'Nouvelle commande :',
        '',
        `Nom : ${payload.customer_name}`,
        `Téléphone : ${payload.phone}`,
        `Ville : ${payload.city}`,
        `Adresse : ${payload.delivery_address}`,
        `Date souhaitée : ${preferredDate}`,
        `Heure : ${preferredTime}`,
        '',
        'Commande :',
        '',
        ...lines,
        `Total : ${Number(payload.total).toFixed(2)} DH`,
        '',
        'Notes :',
        payload.notes || 'Aucune note supplémentaire.',
        '',
        'Merci.'
      ].join('\n');

      fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            const whatsappUrl = `https://wa.me/212713915287?text=${encodeURIComponent(message)}`;
            updateCartBadge(0);
            window.location.assign(whatsappUrl);
          } else {
            alert(data.message || 'Erreur.');
          }
        })
        .catch(() => alert('Une erreur est survenue.'));
    });
  }

  fetchCart().then((cart) => renderCartOnPage(cart.items, cart.total));
});
