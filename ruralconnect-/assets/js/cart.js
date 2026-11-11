/* Demo cart in localStorage (non-sensitive). Django: replace with server-side cart/session + checkout. */
  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('cartApp');
    if (!app) return;

    const draw = () => {
      const items = RC.cart.get().map(l => ({ l, p: RC.PRODUCTS.find(x => x.id === l.id) })).filter(x => x.p && x.p.status === 'approved');
      if (!items.length) {
        app.innerHTML = `
        <div class="text-center py-5 my-4 bg-white rounded-4 border p-5 shadow-sm" style="max-width: 580px; margin: 0 auto; border-color: var(--line) !important;">
          <div class="d-inline-flex align-items-center justify-content-center rounded-circle mb-3" style="width: 80px; height: 80px; background: #f2f4f7;">
            <i class="bi bi-cart-x text-muted" style="font-size: 2.5rem;"></i>
          </div>
          <h2 class="h4 fw-bold text-dark mb-2">Your cart is currently empty</h2>
          <p class="text-muted mx-auto mb-4" style="max-width: 440px; font-size: 0.95rem;">
            Add handcrafted heirlooms or vintage collections to your cart and they will show up here.
          </p>
          <a class="btn rounded-pill px-4 py-2.5 fw-bold text-white shadow-sm" style="background: #102d59;" href="products.html">
            <i class="bi bi-bag-plus me-1"></i> Continue Shopping
          </a>
        </div>
      `;
        return;
      }

      const sub = items.reduce((a, x) => a + RC.price(x.p) * x.l.qty, 0);
      const mrp = items.reduce((a, x) => a + x.p.price * x.l.qty, 0);
      const n = items.reduce((a, x) => a + x.l.qty, 0);
      const ship = sub >= 999 ? 0 : 60;

      app.innerHTML = `
      <div class="row g-4">
        <div class="col-lg-8">
          <div class="bg-white rounded-4 border shadow-sm overflow-hidden mb-3" style="border-color: var(--line) !important;">
            <div class="p-3 px-4 bg-light bg-opacity-50 border-bottom d-flex justify-content-between align-items-center">
              <span class="fw-bold text-dark fs-6">Cart Items (${n})</span>
            </div>
            <div class="cart-list p-2">
              ${items.map(({ l, p }) => `
                <div class="p-3 border-bottom d-flex gap-3 align-items-start flex-wrap flex-md-nowrap">
                  <a href="${RC.href(p)}" class="flex-shrink-0" style="background: #f2f4f7; border-radius: 12px; overflow: hidden; display: flex; align-items: center; justify-content: center; width: 90px; height: 90px;">
                    <img src="${RC.img(p)}" alt="${p.name}" style="width: 100%; height: 100%; object-fit: cover;">
                  </a>
                  <div class="flex-grow-1">
                    <h3 class="h6 mb-1 fw-bold">
                      <a class="text-decoration-none text-dark" style="color: var(--ink);" href="${RC.href(p)}">${p.name}</a>
                    </h3>
                    <div class="small text-muted mb-2">
                      Sold by <span class="fw-semibold text-secondary">${p.seller}</span>
                      · <span class="${p.stock ? 'text-success' : 'text-danger'} fw-semibold">${p.stock ? 'In stock' : 'Out of stock'}</span>
                    </div>
                    <div class="d-flex align-items-center gap-3 flex-wrap">
                      <div class="qty d-inline-flex align-items-center border rounded-pill px-2 py-1 bg-light">
                        <button class="btn btn-sm p-0 border-0 text-dark" data-q="-1" data-id="${p.id}" aria-label="Decrease quantity" style="width: 26px; height: 26px;">
                          <i class="bi bi-dash"></i>
                        </button>
                        <span class="px-3 fw-bold small" aria-live="polite">${l.qty}</span>
                        <button class="btn btn-sm p-0 border-0 text-dark" data-q="1" data-id="${p.id}" aria-label="Increase quantity" ${l.qty >= p.stock ? 'disabled' : ''} style="width: 26px; height: 26px;">
                          <i class="bi bi-plus"></i>
                        </button>
                      </div>
                      <button class="btn btn-link text-danger text-decoration-none small p-0 fw-semibold" data-rm="${p.id}">
                        <i class="bi bi-trash3 me-1"></i> Remove
                      </button>
                    </div>
                  </div>
                  <div class="text-md-end flex-shrink-0 ms-auto">
                    <div class="fs-5 fw-bold" style="color: #102d59;">${RC.inr(RC.price(p) * l.qty)}</div>
                    ${RC.bestDisc(p) ? `<div class="small text-muted"><s>${RC.inr(p.price * l.qty)}</s></div>` : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <div class="col-lg-4">
          <div class="card border-0 shadow-sm rounded-4 p-4 sticky-top" style="top: 100px; background: #fff; border: 1px solid var(--line) !important;">
            <h2 class="h5 fw-bold text-dark mb-3">Order Summary</h2>
            <div class="d-flex justify-content-between mb-2">
              <span class="text-muted">Items (${n})</span>
              <span class="fw-semibold text-dark">${RC.inr(mrp)}</span>
            </div>
            <div class="d-flex justify-content-between mb-2 text-success">
              <span>Discount</span>
              <span class="fw-semibold">−${RC.inr(mrp - sub)}</span>
            </div>
            <div class="d-flex justify-content-between mb-2">
              <span class="text-muted">Delivery</span>
              <span class="fw-semibold ${ship === 0 ? 'text-success' : 'text-dark'}">${ship ? RC.inr(ship) : '<span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill">FREE</span>'}</span>
            </div>
            <hr class="my-3" style="border-color: var(--line);">
            <div class="d-flex justify-content-between align-items-center mb-4">
              <span class="fs-5 fw-bold text-dark">Total</span>
              <span class="fs-4 fw-bold" style="color: #102d59;">${RC.inr(sub + ship)}</span>
            </div>
            <button class="btn btn-lg w-100 py-3 fw-bold shadow-sm rounded-pill text-white" style="background: #102d59;" data-demo="Demo only: checkout and payment will be handled by the backend." data-type="info">
              <i class="bi bi-shield-lock-fill me-2"></i> Proceed to Checkout
            </button>
            <p class="small text-muted mt-3 mb-0 text-center">Demo cart saved in this browser. The server calculates prices at checkout.</p>
          </div>
        </div>
      </div>
    `;
    };

    app.addEventListener('click', e => {
      const q = e.target.closest('[data-q]');
      const r = e.target.closest('[data-rm]');
      const c = RC.cart.get();
      if (q) {
        const l = c.find(x => x.id === +q.dataset.id);
        l.qty += +q.dataset.q;
        RC.cart.set(l.qty < 1 ? c.filter(x => x !== l) : c);
        draw();
      }
      if (r) {
        RC.cart.set(c.filter(x => x.id !== +r.dataset.rm));
        draw();
        RC.toast('Item removed', 'secondary');
      }
    });

    draw();
  });
