# RuralConnect Backend (Django + PostgreSQL)

Full-featured marketplace backend built in Python Django with PostgreSQL as the relational database, matching the RuralConnect UI design and architecture specifications.

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+ running locally on port 5432
- Dependencies installed: `pip install django psycopg2-binary pillow`

### 2. Database Configuration
By default, the backend connects to:
- **Host**: `localhost` (port `5432`)
- **Database**: `ruralconnect`
- **User**: `ruralconnect_user`
- **Password**: `RuralConnect@123`

You can override these using environment variables:
```bash
export DB_NAME=ruralconnect
export DB_USER=ruralconnect_user
export DB_PASSWORD=RuralConnect@123
export DB_HOST=localhost
export DB_PORT=5432
```

### 3. Run Migrations & Seed Demo Data
```bash
cd ruralconnect_backend
python manage.py migrate
python manage.py seed_data
```

### 4. Start Development Server
```bash
python manage.py runserver 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## Demo Accounts

The `seed_data` command creates ready-to-test accounts:

| Role | Email | Password | Dashboard URL |
| :--- | :--- | :--- | :--- |
| **Platform Admin** | `admin@ruralconnect.in` | `Admin@123` | `/admin-panel/` |
| **Seller** | `seller@ruralconnect.in` | `Seller@123` | `/seller/` |
| **Customer / Buyer** | `anita@example.com` | `Buyer@123` | `/` |

---

## Implemented Architecture & Features

### 1. Authentication & Role-Based Access Control
- Custom `User` model (`accounts.User`) with three distinct roles: `buyer`, `seller`, `platform_admin`.
- Role-based redirect on login (Admin -> `/admin-panel/`, Seller -> `/seller/`, Buyer -> `/`).
- Dedicated decorators `@seller_required` and `@admin_required` protecting routes.
- Dual-role login UI (Buyer/Seller tab and Admin tab) matching the original HTML template.

### 2. Public Marketplace (`marketplace` app)
- **Homepage (`/`)**: Hero carousel, promotional banners, featured products (rating >= 4.6), hot deals (discount >= 15%), newest arrivals, sponsored/promoted listings, and regional local crafts.
- **Product Listing (`/products/`)**: Multi-filter sidebar (by category slug, price range, location search) and sorting (price low-to-high, high-to-low, rating, newest).
- **Product Detail (`/products/<pk>/`)**: High-res image gallery, stock display, authoritative price calculations, star reviews list, and review submission form (with protection preventing sellers from reviewing their own products or duplicate reviews).
- **Cart (`/cart/`)**: Persistent client-side cart count and management.

### 3. Seller Portal (`seller` app)
- **Dashboard (`/seller/`)**: Real-time business metrics (total products, approved, pending, rejected, active boosts, average seller rating).
- **My Products (`/seller/my-products/`)**: Catalog management with status badges and reject reason display.
- **Add Product (`/seller/add-product/`)**: Image upload, pricing, discount, stock, and location. Default status is `Pending Approval`.
- **Edit Product (`/seller/edit-product/<pk>/`)**: Full edit support with automatic re-approval trigger: changing core fields (name, description, price, category) on an approved product automatically resets status to `Pending`.
- **Promotions (`/seller/promotions/`)**: Browse and purchase boost plans for approved products to feature them on the homepage.
- **Reviews (`/seller/reviews/`)**: View all customer reviews received across all products.
- **Profile (`/seller/profile/`)**: Edit business details, location, and bio.

### 4. Platform Admin Portal (`platform_admin` app)
- **Overview Dashboard (`/admin-panel/`)**: Global platform stats: total catalog count, pending approval queue, approved live products, active promotional campaigns, and registered seller count.
- **Pending Approvals (`/admin-panel/pending-products/`)**: Review incoming products. 1-click **Approve** or **Reject** with a modal to specify feedback/reasons back to the seller.
- **Manage Products (`/admin-panel/manage-products/`)**: Catalog oversight with tab filters (`All`, `Pending`, `Approved`, `Rejected`, `Suspended`) and status toggling.
- **Category Management (`/admin-panel/manage-categories/`)**: Create and delete marketplace categories with emoji and hue icons.
- **Homepage Banners (`/admin-panel/banners/`)**: Add, toggle active state, or remove homepage promotional banners.
- **Discount Campaigns (`/admin-panel/campaigns/`)**: Schedule date-bounded platform sales campaigns and attach specific products.
- **Boost Plans (`/admin-panel/boost-plans/`)**: Create and configure promotional pricing tiers and manage active seller boosts.

### 5. Pricing Engine
Authoritative pricing formula strictly matches specification:
$$\text{Effective Discount} = \max(\text{Seller Discount}, \text{Active Campaign Discount})$$
$$\text{Final Price} = \text{Base Price} \times \left(1 - \frac{\text{Effective Discount}}{100}\right)$$
