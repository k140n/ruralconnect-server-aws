/* Seller dashboard demo rendering. Django: replace with {% for %} loops filtered by request.user. */
document.addEventListener('DOMContentLoaded',()=>{
 const badge=s=>({approved:'success',pending:'warning',rejected:'danger',suspended:'secondary'}[s]); RC.badge=s=>`<span class="badge text-bg-${badge(s)}">${s[0].toUpperCase()+s.slice(1)}</span>`;
 const mine=RC.PRODUCTS.filter(p=>p.seller===RC.MY_SELLER), t=document.getElementById('myProducts');
 const cnt=s=>mine.filter(p=>p.status===s).length;
 const set=(id,v)=>{const e=document.getElementById(id); if(e) e.textContent=v;};
 set('sTotal',mine.length);set('sApproved',cnt('approved'));set('sPending',cnt('pending'));set('sRejected',cnt('rejected'));set('sPromos',1);set('sRating','4.5');
 if(t) t.innerHTML=mine.map(p=>`<tr><td><img class="thumb-sm" src="${RC.img(p)}" alt=""></td><td><strong class="pname">${p.name}</strong>${p.rejectReason?`<div class="small text-danger">${p.rejectReason}</div>`:''}</td><td>${RC.CATEGORIES.find(c=>c.slug===p.cat).name}</td><td>${RC.inr(p.price)}</td><td>${p.sellerDisc}%</td><td>${RC.badge(p.status)}</td>
 <td class="text-nowrap"><a class="btn btn-sm btn-outline-rc" href="edit-product.html?id=${p.id}">Edit</a> <button class="btn btn-sm btn-outline-danger" data-confirm="Deactivate “${p.name}”? It will be hidden from the marketplace." data-confirm-done="Product deactivated (demo)" data-remove="1">Deactivate</button></td></tr>`).join('');
 const sel=document.getElementById('boostProduct'); if(sel) sel.innerHTML=mine.filter(p=>p.status==='approved').map(p=>`<option>${p.name}</option>`).join(''); // only approved can be boosted
 const ef=document.getElementById('editForm'); if(ef){const p=RC.PRODUCTS.find(x=>x.id===+new URLSearchParams(location.search).get('id'))||mine[0]; ['name','description','price','discount','quantity','location'].forEach(n=>{const e=ef.elements[n]; if(e) e.value={name:p.name,description:p.desc,price:p.price,discount:p.sellerDisc,quantity:p.stock,location:p.loc}[n];}); ef.elements.category.value=p.cat; document.getElementById('price').dispatchEvent(new Event('input'));}
 const bf=document.getElementById('boostBtns'); document.querySelectorAll('[data-boost]').forEach(b=>b.addEventListener('click',()=>RC.toast('Demo only: '+b.dataset.boost+' was not purchased. No payment has been taken.','info')));
});
