# RuralConnect Frontend

Static HTML5 + CSS3 + vanilla JS + Bootstrap 5 (CDN). No build step.

## Run locally
`python3 -m http.server 8000` in this folder, then open http://localhost:8000
(Internet needed for Bootstrap, Bootstrap Icons and Google Fonts CDNs.)

## Structure
- Public: index, products, product-details (`?id=`), login, register
- `seller/`: dashboard, my-products, add-product, edit-product, promotions, reviews, profile
- `platform-admin/`: dashboard, pending-products, manage-products, manage-categories, banners, campaigns, boost-plans
- `assets/css`: style (tokens, shared), marketplace, dashboard, responsive
- `assets/js`: data (sample data), main (shared helpers, pricing), products, seller, admin
- `build.py`: regenerates every page from one shared layout (header, footer, sidebars). Edit it, run `python3 build.py`.

## Django conversion
- `build.py` layouts map to three base templates: `base_public.html`, `base_seller.html`, `base_admin.html`. Page bodies become `{% block content %}`.
- Replace `RC.PRODUCTS` (assets/js/data.js) with context data; the `RC.card` markup becomes `{% include "partials/product_card.html" %}`.
- Replace `data-slot` rails and the `*Table` bodies with `{% for %}` loops. Use `{% url %}` for links.
- Form field names (`full_name`, `business_name`, `discount`, `main_image`, ...) are meant to match Django forms.

## Backend requirements (not built here)
1. Auth, roles, sessions, password hashing, "remember me", seller vs admin permissions.
2. Products default to Pending; only Approved are public; sellers edit only their own; important edits to approved products trigger re-approval; sellers cannot approve or review own products.
3. Authoritative price: `final = base * (1 - max(seller_discount, campaign_discount)/100)`. `RC.finalPrice` is a demo only.
4. Image uploads/storage, categories, banners (admin only), campaigns, reviews, seller contact.
5. Boost plans, payments, activation and expiry. Boost buttons here are demos; no payment happens.
6. Server-side validation of every form (client validation is convenience only).
7. Pagination/search/filter/sort in queries (the demo filters in the browser).

## Limitations
- Reference was screenshots only (no live site). Adopted: soft grey rounded cards, pill buttons, serif-italic + sans headings, large-radius footer with pill links. Palette changed to forest green and marigold for RuralConnect.
- Product images are generated emoji placeholders; swap for real photos.
- Only localStorage-free demo state; nothing persists on reload.
- Not browser-tested here (no network/browser in this environment); please click through each page.
