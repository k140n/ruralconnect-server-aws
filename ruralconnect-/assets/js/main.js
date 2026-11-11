/* Shared helpers. NOTE: price logic here is DEMO only; Django must compute the authoritative price. */
(function () {
  RC.inr = n => '₹' + Math.round(n).toLocaleString('en-IN');
  RC.bestDisc = p => Math.max(+p.sellerDisc || 0, +p.campDisc || 0); // discounts do not stack
  RC.finalPrice = (base, seller, camp) => base * (1 - Math.max(+seller || 0, +camp || 0) / 100);
  RC.price = p => RC.finalPrice(p.price, p.sellerDisc, p.campDisc);
  RC.img = p => { const c = `hsl(${p.hue},45%,88%)`; const s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><rect width="400" height="400" fill="${c}"/><text x="200" y="250" font-size="170" text-anchor="middle">${p.emoji}</text></svg>`; return 'data:image/svg+xml;utf8,' + encodeURIComponent(s); };
  RC.stars = r => { let h = ''; for (let i = 1; i <= 5; i++) h += `<i class="bi bi-star${r >= i ? '-fill' : (r >= i - .5 ? '-half' : '')}"></i>`; return `<span class="stars" aria-label="${r} out of 5">${h}</span>`; };
  RC.href = p => (RC.root || '') + 'product-details.html?id=' + p.id;
  RC.card = p => {
    const d = RC.bestDisc(p); return `<article class="product-card"><a href="${RC.href(p)}" class="product-image"><img src="${RC.img(p)}" alt="${p.name}" loading="lazy">${d ? `<span class="badge-off" style="position:absolute;top:10px;left:10px;z-index:2;font-size:11px;padding:3px 8px;border-radius:999px;background:#102d59;color:#fff;font-weight:700;">${d}% off</span>` : ''}${p.promoted ? '<span class="badge-spons" style="position:absolute;bottom:10px;left:10px;z-index:2;font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(17,25,77,0.85);color:#fff;font-weight:600;">Sponsored</span>' : ''}</a>
 <a class="product-name" href="${RC.href(p)}">${p.name}</a><div class="small text-muted text-truncate mb-1" style="font-size:0.76rem;">${p.seller} · ${p.loc}</div>
 <div class="rating">${RC.stars(p.rating)} <small>(${p.reviews})</small></div>
 <div class="price">${RC.inr(RC.price(p))}${d ? `<del>${RC.inr(p.price)}</del>` : ''}</div>
 <div class="product-actions mt-auto"><button class="add-button" data-add="${p.id}" ${p.stock ? '' : 'disabled'}><i class="bi bi-cart-plus"></i> Add</button><a class="buy-now-button" href="${RC.href(p)}">Buy Now</a></div></article>`;
  };
  RC.approved = () => RC.PRODUCTS.filter(p => p.status === 'approved'); // only approved are public
  RC.toast = (msg, type = 'success') => { let w = document.getElementById('toasts'); if (!w) { w = document.createElement('div'); w.id = 'toasts'; w.className = 'toast-container position-fixed bottom-0 end-0 p-3'; document.body.appendChild(w); } const e = document.createElement('div'); e.className = `toast align-items-center text-bg-${type} border-0`; e.setAttribute('role', 'status'); e.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`; w.appendChild(e); new bootstrap.Toast(e, { delay: 3500 }).show(); };
  RC.cart = {
    get() { try { return JSON.parse(localStorage.getItem('rc_cart') || '[]') } catch (e) { return [] } }, set(c) { try { localStorage.setItem('rc_cart', JSON.stringify(c)) } catch (e) { } RC.updateCount() },
    add(id, q = 1) { const c = RC.cart.get(), l = c.find(x => x.id === id), p = RC.PRODUCTS.find(x => x.id === id); if (l) l.qty = Math.min(l.qty + q, p.stock || 1); else c.push({ id, qty: q }); RC.cart.set(c) }
  };
  RC.updateCount = () => { const n = RC.cart.get().reduce((a, x) => a + x.qty, 0); document.querySelectorAll('[data-cart-count]').forEach(e => { e.textContent = n; e.hidden = !n; }); };
  document.addEventListener('click', e => {
    const a = e.target.closest('[data-add],[data-buy],[data-share]'); if (!a) return;
    if (a.dataset.add) { RC.cart.add(+a.dataset.add); RC.toast('Added to cart. <a class="text-white fw-bold" href="' + RC.root + 'cart.html">View cart</a>'); }
    if (a.dataset.buy) { RC.cart.add(+a.dataset.buy); location.href = RC.root + 'cart.html'; }
    if (a.dataset.share) { const d = { title: document.title, url: location.href }; if (navigator.share) { navigator.share(d).catch(() => { }); } else if (navigator.clipboard) { navigator.clipboard.writeText(d.url).then(() => RC.toast('Product link copied')); } else RC.toast(d.url, 'info'); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    RC.root = document.body.dataset.root || ''; RC.updateCount();
    // render product rails: <div data-slot="featured|deals|new|sponsored|local" data-limit="4">
    document.querySelectorAll('[data-slot]').forEach(el => {
      const s = el.dataset.slot, n = +el.dataset.limit || 4; let l = RC.approved();
      if (s === 'featured') l = l.filter(p => p.rating >= 4.6); if (s === 'deals') l = l.filter(p => RC.bestDisc(p) >= 15).sort((a, b) => RC.bestDisc(b) - RC.bestDisc(a));
      if (s === 'new') l = l.sort((a, b) => b.added.localeCompare(a.added)); if (s === 'sponsored') l = l.filter(p => p.promoted); if (s === 'local') l = l.filter(p => p.loc.includes('Kerala'));
      if (s === 'trends') { el.innerHTML = RC.approved().slice(0, 4).map(p => `<a class="trend" href="${RC.href(p)}"><img src="${RC.img(p)}" alt="${p.name}"><span class="pname">${p.name.split(' ').slice(0, 2).join(' ')}</span></a>`).join(''); return; }
      if (['featured', 'deals', 'new', 'sponsored', 'local'].includes(s)) el.innerHTML = l.slice(0, n).map(p => `<div class="col-6 col-lg-3">${RC.card(p)}</div>`).join('');
    });
    const cats = document.getElementById('catTiles'); if (cats) cats.innerHTML = RC.CATEGORIES.map(c => `<div class="col-6 col-md-4 col-lg-2"><a class="cat-tile" style="--h:${c.hue}" href="${RC.root}products.html?cat=${c.slug}"><span>${c.emoji}</span>${c.name}</a></div>`).join('');
    document.querySelectorAll('select[data-cats]').forEach(s => { s.innerHTML = (s.dataset.cats === 'all' ? '<option value="">All</option>' : '<option value="">Select category</option>') + RC.CATEGORIES.map(c => `<option value="${c.slug}">${c.name}</option>`).join(''); });
    // password toggle
    document.querySelectorAll('[data-toggle-pw]').forEach(b => b.addEventListener('click', () => { const i = document.getElementById(b.dataset.togglePw); const show = i.type === 'password'; i.type = show ? 'text' : 'password'; b.querySelector('i').className = 'bi bi-eye' + (show ? '-slash' : ''); b.setAttribute('aria-label', show ? 'Hide password' : 'Show password'); }));
    // validation (client-side only; Django must re-validate)
    document.querySelectorAll('form.needs-validation').forEach(f => f.addEventListener('submit', e => {
      e.preventDefault(); const pw = f.querySelector('[name=password]'), cp = f.querySelector('[name=confirm_password]'); if (pw && cp) cp.setCustomValidity(pw.value && pw.value !== cp.value ? 'Passwords do not match' : '');
      f.classList.add('was-validated'); if (f.checkValidity()) RC.toast(f.dataset.demo || 'Demo only: nothing was saved. This form will post to Django.');
    }));
    // image preview
    document.querySelectorAll('input[data-preview]').forEach(i => i.addEventListener('change', () => { const box = document.getElementById(i.dataset.preview); box.innerHTML = '';[...i.files].slice(0, 5).forEach(f => { const im = document.createElement('img'); im.src = URL.createObjectURL(f); im.alt = 'Preview of ' + f.name; im.className = 'preview-img'; box.appendChild(im); }); }));
    // live price preview
    const pr = document.getElementById('price'), sd = document.getElementById('discount'); if (pr && sd) { const out = document.getElementById('finalPreview'), u = () => { out.textContent = pr.value ? RC.inr(RC.finalPrice(+pr.value, +sd.value, 0)) : '—'; }; pr.addEventListener('input', u); sd.addEventListener('input', u); u(); }
    // sidebar toggle
    document.querySelectorAll('[data-sidebar-toggle]').forEach(b => b.addEventListener('click', () => document.body.classList.toggle('sidebar-open')));
    // confirm modal for destructive actions: <button data-confirm="Message" data-confirm-done="Done msg">
    document.addEventListener('click', e => { const b = e.target.closest('[data-confirm]'); if (!b) return; const m = document.getElementById('confirmModal'); if (!m) return; m.querySelector('.modal-body').textContent = b.dataset.confirm; const ok = m.querySelector('[data-ok]'); const mod = bootstrap.Modal.getOrCreateInstance(m); ok.onclick = () => { const row = b.closest('tr,.pcard,.col-12'); if (b.dataset.remove && row) row.remove(); RC.toast(b.dataset.confirmDone || 'Done (demo)'); mod.hide(); }; mod.show(); });
    document.addEventListener('click', e => { const b = e.target.closest('[data-demo]'); if (b) { e.preventDefault(); RC.toast(b.dataset.demo, b.dataset.type || 'success'); const row = b.closest('tr'); if (row && b.dataset.removeRow !== undefined) row.remove(); } });
  });
})();
