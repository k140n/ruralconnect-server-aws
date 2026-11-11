/* Listing filters + detail page. Demo: client-side over RC.PRODUCTS. Django: server-side query params. */
document.addEventListener('DOMContentLoaded',()=>{
 const grid=document.getElementById('grid');
 if(grid){
  const q=new URLSearchParams(location.search), f={q:q.get('q')||'',cat:q.get('cat')||'',min:'',max:'',loc:'',sort:'relevance'}; let shown=6;
  const $=id=>document.getElementById(id);
  $('fq').value=f.q; $('fcat').value=f.cat;
  $('floc').innerHTML='<option value="">All locations</option>'+RC.LOCATIONS.map(l=>`<option>${l}</option>`).join('');
  const render=()=>{ f.q=$('fq').value.trim().toLowerCase(); f.cat=$('fcat').value; f.min=+$('fmin').value||0; f.max=+$('fmax').value||Infinity; f.loc=$('floc').value; f.sort=$('fsort').value;
   let l=RC.approved().filter(p=>(!f.q||(p.name+p.seller+p.desc).toLowerCase().includes(f.q))&&(!f.cat||p.cat===f.cat)&&RC.price(p)>=f.min&&RC.price(p)<=f.max&&(!f.loc||p.loc===f.loc));
   const s={'price-asc':(a,b)=>RC.price(a)-RC.price(b),'price-desc':(a,b)=>RC.price(b)-RC.price(a),newest:(a,b)=>b.added.localeCompare(a.added),rating:(a,b)=>b.rating-a.rating,relevance:(a,b)=>b.promoted-a.promoted}[f.sort]; l.sort(s);
   $('count').textContent=l.length+' product'+(l.length===1?'':'s'); grid.innerHTML=l.slice(0,shown).map(p=>`<div class="col-6 col-xl-4">${RC.card(p)}</div>`).join('');
   $('empty').classList.toggle('d-none',l.length>0); $('more').classList.toggle('d-none',l.length<=shown); };
  document.querySelectorAll('#filters input,#filters select').forEach(e=>e.addEventListener('input',()=>{shown=6;render();}));
  $('more').addEventListener('click',()=>{shown+=6;render();}); $('reset').addEventListener('click',()=>{$('filters').reset();shown=6;render();}); $('filters').addEventListener('submit',e=>e.preventDefault());
  render();
 }
 const det=document.getElementById('detail');
 if(det){
  const id=+new URLSearchParams(location.search).get('id')||1; const p=RC.approved().find(x=>x.id===id);
  if(!p){det.innerHTML='<div class="alert alert-warning">This product is not available. Only approved products are shown publicly.</div>';return;}
  const d=RC.bestDisc(p), cat=RC.CATEGORIES.find(c=>c.slug===p.cat);
  document.title=p.name+' | RuralConnect'; document.getElementById('crumb').innerHTML=`<li class="breadcrumb-item"><a href="index.html">Home</a></li><li class="breadcrumb-item"><a href="products.html?cat=${cat.slug}">${cat.name}</a></li><li class="breadcrumb-item active" aria-current="page">${p.name}</li>`;
  const thumbs=[0,1,2].map(i=>({...p,hue:p.hue+i*25}));
  const phone='919876543210';
  det.innerHTML=`<div class="row g-4"><div class="col-lg-6"><div class="gallery-main"><img id="mainImg" src="${RC.img(p)}" alt="${p.name}"></div><div class="d-flex gap-2 mt-2">${thumbs.map((t,i)=>`<button class="thumb ${i?'':'active'}" data-src="${RC.img(t)}" aria-label="Show image ${i+1}"><img src="${RC.img(t)}" alt=""></button>`).join('')}</div></div>
  <div class="col-lg-6">${p.promoted?'<span class="badge-spons static">Sponsored</span>':''}<h1 class="h2 mt-1 pname">${p.name}</h1><div>${RC.stars(p.rating)} <a href="#reviews" class="small">${p.reviews} ratings</a></div><p class="text-muted mt-2">Category: ${cat.name}</p>
  <div class="d-flex align-items-baseline gap-3"><span class="display-6 fw-bold">${RC.inr(RC.price(p))}</span>${d?`<s class="text-muted">${RC.inr(p.price)}</s><span class="badge text-bg-warning">${d}% off</span>`:''}</div>
  ${d?`<div class="small text-muted">Best eligible discount applied (seller ${p.sellerDisc}% / campaign ${p.campDisc}%, not stacked).</div>`:''}
  <p class="mt-3">${p.desc}</p><p class="${p.stock>0?'text-success':'text-danger'} fw-semibold">${p.stock>0?(p.stock<20?'Only '+p.stock+' left':'In stock ('+p.stock+' available)'):'Out of stock'}</p>
  <div class="seller-box"><div class="fw-semibold"><i class="bi bi-shop"></i> ${p.seller}</div><div class="small text-muted"><i class="bi bi-geo-alt"></i> ${p.loc} · <i class="bi bi-telephone"></i> +91 98765 43210 (sample)</div></div>
  <div class="d-flex gap-2 mt-3 flex-wrap"><button class="btn btn-outline-rc btn-lg" data-add="${p.id}" ${p.stock?'':'disabled'}><i class="bi bi-cart-plus"></i> Add to cart</button><button class="btn btn-rc btn-lg" data-buy="${p.id}" ${p.stock?'':'disabled'}><i class="bi bi-lightning-charge"></i> Buy now</button><button class="btn btn-light btn-lg border" data-share="1"><i class="bi bi-share"></i> Share</button></div></div></div>
  <section id="reviews" class="mt-5"><h2 class="h4">Customer reviews</h2>${RC.REVIEWS.map(r=>`<div class="review"><div>${RC.stars(r.rating)} <strong>${r.name}</strong> <span class="small text-muted">${r.date}</span></div><p class="mb-0">${r.text}</p></div>`).join('')}<p class="small text-muted mt-2">Sellers cannot review their own products (enforced by Django).</p></section>
  <section class="mt-5"><h2 class="h4">Related products</h2><div class="row g-3">${RC.approved().filter(x=>x.cat===p.cat&&x.id!==p.id||x.promoted&&x.id!==p.id).slice(0,4).map(x=>`<div class="col-6 col-lg-3">${RC.card(x)}</div>`).join('')}</div></section>`;
  det.querySelectorAll('.thumb').forEach(b=>b.addEventListener('click',()=>{document.getElementById('mainImg').src=b.dataset.src;det.querySelectorAll('.thumb').forEach(t=>t.classList.toggle('active',t===b));}));
 }
});
