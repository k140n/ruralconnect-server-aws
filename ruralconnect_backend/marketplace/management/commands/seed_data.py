"""
Populate database with demo data matching ruralconnect- UI mockups.
Run via: python manage.py seed_data
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, SellerProfile
from marketplace.models import (
    Category, Product, Banner, Campaign, CampaignProduct, BoostPlan, Boost, Review, HeroSlide
)


class Command(BaseCommand):
    help = 'Seeds the database with categories, demo sellers, products, reviews, banners, campaigns and boost plans.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # 1. Admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@ruralconnect.in',
            defaults={
                'full_name': 'Platform Admin',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('Admin@123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin@ruralconnect.in / Admin@123'))

        # 2. Main demo seller (Meena Devi Antiques)
        seller_user, created = User.objects.get_or_create(
            email='seller@ruralconnect.in',
            defaults={
                'full_name': 'Meena Devi',
                'phone': '+91 98470 12345',
                'role': User.ROLE_SELLER,
            }
        )
        if created:
            seller_user.set_password('Seller@123')
            seller_user.save()

        main_seller, _ = SellerProfile.objects.get_or_create(
            user=seller_user,
            defaults={
                'business_name': 'Meena Devi Antiques',
                'location': 'Thiruvananthapuram, Kerala',
                'bio': 'Curating authentic Kerala brassware, reclaimed wood artifacts and vintage electronics since 1994.',
            }
        )
        self.stdout.write(self.style.SUCCESS('Main seller: seller@ruralconnect.in / Seller@123'))

        # 3. Buyer users for reviews
        buyer1, _ = User.objects.get_or_create(
            email='anita@example.com',
            defaults={'full_name': 'Anita R.', 'role': User.ROLE_BUYER}
        )
        buyer1.set_password('Buyer@123')
        buyer1.save()

        buyer2, _ = User.objects.get_or_create(
            email='imran@example.com',
            defaults={'full_name': 'Imran S.', 'role': User.ROLE_BUYER}
        )
        buyer2.set_password('Buyer@123')
        buyer2.save()

        buyer3, _ = User.objects.get_or_create(
            email='latha@example.com',
            defaults={'full_name': 'Latha K.', 'role': User.ROLE_BUYER}
        )
        buyer3.set_password('Buyer@123')
        buyer3.save()

        # 4. Categories from data.js
        categories_data = [
            {'slug': 'vintage-electronics', 'name': 'Vintage Electronics', 'emoji': '📺', 'hue': 215, 'icon': 'bi-tv', 'order': 1},
            {'slug': 'antiques', 'name': 'Antiques', 'emoji': '🕰️', 'hue': 35, 'icon': 'bi-clock-history', 'order': 2},
            {'slug': 'handicrafts', 'name': 'Handicrafts', 'emoji': '🧸', 'hue': 20, 'icon': 'bi-brush', 'order': 3},
            {'slug': 'brass-copper', 'name': 'Brass & Copper', 'emoji': '🪔', 'hue': 42, 'icon': 'bi-fire', 'order': 4},
            {'slug': 'furniture', 'name': 'Wooden Furniture', 'emoji': '🪑', 'hue': 25, 'icon': 'bi-house-door', 'order': 5},
            {'slug': 'textiles', 'name': 'Handloom & Textiles', 'emoji': '🧣', 'hue': 330, 'icon': 'bi-palette', 'order': 6},
            {'slug': 'home-decor', 'name': 'Home Decor & Art', 'emoji': '🖼️', 'hue': 160, 'icon': 'bi-image', 'order': 7},
            {'slug': 'collectibles', 'name': 'Collectibles', 'emoji': '📷', 'hue': 270, 'icon': 'bi-camera', 'order': 8},
        ]

        cat_map = {}
        for cdata in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=cdata['slug'],
                defaults=cdata
            )
            cat_map[cdata['slug']] = cat

        self.stdout.write(f'Created/verified {len(cat_map)} categories.')

        # 5. Boost plans
        plans_data = [
            {'name': '7 Days Spotlight', 'description': 'Featured on homepage and top of category search for 7 days', 'price': 499, 'duration_days': 7},
            {'name': '14 Days Premium', 'description': 'Priority placement in search results and deals section for 14 days', 'price': 899, 'duration_days': 14},
            {'name': '30 Days Ultimate', 'description': 'Maximum visibility across all public sections for a full month', 'price': 1499, 'duration_days': 30},
        ]
        plan_objects = []
        for pdata in plans_data:
            bp, _ = BoostPlan.objects.get_or_create(name=pdata['name'], defaults=pdata)
            plan_objects.append(bp)

        # 6. Banners
        banners_data = [
            {
                'title': 'Spring Handloom & Textiles Fair',
                'subtitle': 'Discover GI-tagged handlooms directly from rural weaver cooperatives',
                'link_url': '/products/?cat=textiles',
                'css_class': 'b1',
                'icon': 'bi-palette',
                'order': 1,
            },
            {
                'title': 'Authentic Heritage Antiques',
                'subtitle': 'Restored valve radios, pendulum clocks and vintage collectibles with provenance',
                'link_url': '/products/?cat=antiques',
                'css_class': 'b2',
                'icon': 'bi-clock-history',
                'order': 2,
            },
            {
                'title': 'Support Direct Rural Artisans',
                'subtitle': '100% genuine craftsmanship with no middleman margins',
                'link_url': '/products/?cat=handicrafts',
                'css_class': 'b3',
                'icon': 'bi-heart-fill',
                'order': 3,
            },
        ]
        for bdata in banners_data:
            Banner.objects.get_or_create(title=bdata['title'], defaults=bdata)

        # 6b. Top Hero Carousel Slides
        hero_slides_data = [
            {
                'order': 1,
                'accent_text': 'Up to 20% off',
                'title': 'on vintage electronics',
                'subtitle': 'Restored valve radios, CRT televisions and rotary phones, tested and working.',
                'button_text': 'Shop vintage electronics',
                'button_link': '/products/?cat=vintage-electronics',
                'icon': 'bi-tv',
                'bg_color': '#1f3d2f',
                'is_active': True,
            },
            {
                'order': 2,
                'accent_text': '',
                'title': 'Antique crafts made by village hands',
                'subtitle': 'Dhokra brass, bell-metal lamps, carved rosewood and Madhubani art.',
                'button_text': 'Explore crafts',
                'button_link': '/products/?cat=brass-copper',
                'icon': 'bi-lamp',
                'bg_color': '#2b2b2b',
                'is_active': True,
            },
            {
                'order': 3,
                'accent_text': '',
                'title': 'Sell your heirlooms and handmade goods',
                'subtitle': 'Open a free seller account and reach buyers across India.',
                'button_text': 'Become a seller',
                'button_link': '/register/',
                'icon': 'bi-clock-history',
                'bg_color': '#3b3b38',
                'is_active': True,
            },
        ]
        for sdata in hero_slides_data:
            HeroSlide.objects.get_or_create(order=sdata['order'], defaults=sdata)

        # 7. Campaign
        today = timezone.now().date()
        campaign, _ = Campaign.objects.get_or_create(
            name='Diwali Heritage Fest',
            defaults={
                'description': 'Flat 20% off on selected vintage audio and traditional handlooms',
                'discount_percent': 20,
                'start_date': today - timedelta(days=5),
                'end_date': today + timedelta(days=25),
                'is_active': True,
            }
        )

        # 8. Sellers & Products from data.js
        sellers_info = {
            'Restored Radio Works': ('Jaipur, Rajasthan', 'radio@example.com'),
            'Retro Tube Traders': ('Kochi, Kerala', 'retrotube@example.com'),
            'Thrissur Heritage House': ('Thrissur, Kerala', 'heritage@example.com'),
            'Kuttanad Woodworks': ('Thiruvananthapuram, Kerala', 'kuttanad@example.com'),
            'Bastar Tribal Artisans': ('Bastar, Chhattisgarh', 'bastar@example.com'),
            'Ikat Weavers Guild': ('Pochampally, Telangana', 'ikat@example.com'),
            'Aranmula Metal Craft': ('Thiruvananthapuram, Kerala', 'aranmula@example.com'),
            'Channapatna Toy Makers': ('Channapatna, Karnataka', 'toys@example.com'),
            'Mithila Art Collective': ('Madhubani, Bihar', 'mithila@example.com'),
            'Deccan Numismatics': ('Thrissur, Kerala', 'coins@example.com'),
        }

        seller_profiles = {'Meena Devi Antiques': main_seller}
        for bname, (loc, email) in sellers_info.items():
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={'full_name': bname, 'role': User.ROLE_SELLER}
            )
            u.set_password('Seller@123')
            u.save()
            sp, _ = SellerProfile.objects.get_or_create(
                user=u,
                defaults={'business_name': bname, 'location': loc, 'bio': f'Authentic craftspeople from {loc}.'}
            )
            seller_profiles[bname] = sp

        # Products list from data.js
        products_data = [
            {
                'name': 'Restored Valve Radio (1960s)',
                'cat': 'vintage-electronics',
                'price': 4800,
                'seller_discount': 10,
                'seller': 'Restored Radio Works',
                'location': 'Jaipur, Rajasthan',
                'stock': 4,
                'promoted': True,
                'emoji': '📻',
                'hue': 215,
                'status': Product.STATUS_APPROVED,
                'desc': 'Fully restored tube radio, tested and working on AM/FM with Bluetooth input added discreetly.',
                'in_campaign': True,
            },
            {
                'name': 'Old Black & White CRT Television',
                'cat': 'vintage-electronics',
                'price': 6500,
                'seller_discount': 0,
                'seller': 'Retro Tube Traders',
                'location': 'Kochi, Kerala',
                'stock': 3,
                'promoted': False,
                'emoji': '📺',
                'hue': 200,
                'status': Product.STATUS_APPROVED,
                'desc': 'Working 14-inch vintage CRT TV in a teak cabinet. Ideal for collectors and film sets.',
                'in_campaign': False,
            },
            {
                'name': 'Antique Brass Wall Clock',
                'cat': 'antiques',
                'price': 3200,
                'seller_discount': 15,
                'seller': 'Thrissur Heritage House',
                'location': 'Thrissur, Kerala',
                'stock': 8,
                'promoted': False,
                'emoji': '🕰️',
                'hue': 35,
                'status': Product.STATUS_APPROVED,
                'desc': 'Hand-wound pendulum clock with a brass dial, serviced by a master clockmaker.',
                'in_campaign': False,
            },
            {
                'name': 'Hand-Carved Rosewood Chair',
                'cat': 'furniture',
                'price': 7800,
                'seller_discount': 10,
                'seller': 'Kuttanad Woodworks',
                'location': 'Thiruvananthapuram, Kerala',
                'stock': 6,
                'promoted': True,
                'emoji': '🪑',
                'hue': 25,
                'status': Product.STATUS_APPROVED,
                'desc': 'Solid rosewood armchair with traditional carved back, finished with natural lacquer.',
                'in_campaign': False,
            },
            {
                'name': 'Dhokra Brass Horse Figurine',
                'cat': 'brass-copper',
                'price': 1450,
                'seller_discount': 5,
                'seller': 'Bastar Tribal Artisans',
                'location': 'Bastar, Chhattisgarh',
                'stock': 40,
                'promoted': False,
                'emoji': '🐴',
                'hue': 42,
                'status': Product.STATUS_APPROVED,
                'desc': 'Lost-wax cast brass figure made by tribal artisans using a 4,000-year-old method.',
                'in_campaign': False,
            },
            {
                'name': 'Pochampally Ikat Dupatta',
                'cat': 'textiles',
                'price': 1200,
                'seller_discount': 10,
                'seller': 'Ikat Weavers Guild',
                'location': 'Pochampally, Telangana',
                'stock': 30,
                'promoted': False,
                'emoji': '🧣',
                'hue': 260,
                'status': Product.STATUS_APPROVED,
                'desc': 'Handwoven silk-cotton dupatta with traditional double ikat motifs.',
                'in_campaign': True,
            },
            {
                'name': 'Aranmula-style Bell Metal Lamp',
                'cat': 'brass-copper',
                'price': 2200,
                'seller_discount': 0,
                'seller': 'Aranmula Metal Craft',
                'location': 'Thiruvananthapuram, Kerala',
                'stock': 15,
                'promoted': True,
                'emoji': '🪔',
                'hue': 45,
                'status': Product.STATUS_APPROVED,
                'desc': 'Traditional nilavilakku cast in bell metal, 12 inches tall, with a mirror-bright polish.',
                'in_campaign': False,
            },
            {
                'name': 'Vintage Rotary Dial Phone',
                'cat': 'vintage-electronics',
                'price': 2600,
                'seller_discount': 12,
                'seller': 'Retro Tube Traders',
                'location': 'Kochi, Kerala',
                'stock': 9,
                'promoted': False,
                'emoji': '📞',
                'hue': 190,
                'status': Product.STATUS_APPROVED,
                'desc': 'Refurbished 1970s rotary phone, converted to work with modern landlines.',
                'in_campaign': False,
            },
            {
                'name': 'Channapatna Wooden Toy Set',
                'cat': 'handicrafts',
                'price': 650,
                'seller_discount': 0,
                'seller': 'Channapatna Toy Makers',
                'location': 'Channapatna, Karnataka',
                'stock': 60,
                'promoted': False,
                'emoji': '🧸',
                'hue': 20,
                'status': Product.STATUS_APPROVED,
                'desc': 'Lacquered wooden toys coloured with vegetable dyes. Safe for children.',
                'in_campaign': False,
            },
            {
                'name': 'Madhubani Painting on Handmade Paper',
                'cat': 'home-decor',
                'price': 1800,
                'seller_discount': 10,
                'seller': 'Mithila Art Collective',
                'location': 'Madhubani, Bihar',
                'stock': 12,
                'promoted': False,
                'emoji': '🖼️',
                'hue': 160,
                'status': Product.STATUS_APPROVED,
                'desc': 'Hand-painted fish motif in natural pigments, ready to frame, 16 x 22 inches.',
                'in_campaign': False,
            },
            {
                'name': 'Antique Coin Collection (25 pcs)',
                'cat': 'collectibles',
                'price': 2500,
                'seller_discount': 5,
                'seller': 'Deccan Numismatics',
                'location': 'Thrissur, Kerala',
                'stock': 5,
                'promoted': False,
                'emoji': '🪙',
                'hue': 270,
                'status': Product.STATUS_APPROVED,
                'desc': 'Authenticated assorted princely-state and colonial-era coins in a wooden case.',
                'in_campaign': False,
            },
            # Pending & rejected products for Meena Devi Antiques
            {
                'name': 'Vintage Film Camera (Agfa)',
                'cat': 'collectibles',
                'price': 3900,
                'seller_discount': 0,
                'seller': 'Meena Devi Antiques',
                'location': 'Thiruvananthapuram, Kerala',
                'stock': 1,
                'promoted': False,
                'emoji': '📷',
                'hue': 270,
                'status': Product.STATUS_PENDING,
                'desc': 'Folding bellows camera in working condition. Collector item.',
                'in_campaign': False,
            },
            {
                'name': 'Terracotta Wall Plate',
                'cat': 'home-decor',
                'price': 350,
                'seller_discount': 10,
                'seller': 'Meena Devi Antiques',
                'location': 'Thiruvananthapuram, Kerala',
                'stock': 50,
                'promoted': False,
                'emoji': '🏺',
                'hue': 18,
                'status': Product.STATUS_REJECTED,
                'desc': 'Hand-painted terracotta plate.',
                'reject_reason': 'Photos are unclear. Please upload a well-lit main image.',
                'in_campaign': False,
            },
            {
                'name': 'Brass Diya Set (6 pcs)',
                'cat': 'brass-copper',
                'price': 780,
                'seller_discount': 5,
                'seller': 'Meena Devi Antiques',
                'location': 'Thiruvananthapuram, Kerala',
                'stock': 75,
                'promoted': False,
                'emoji': '🪔',
                'hue': 45,
                'status': Product.STATUS_SUSPENDED,
                'desc': 'Hand-polished brass oil lamps.',
                'in_campaign': False,
            },
        ]

        sample_images = {
            'Restored Valve Radio (1960s)': 'products/main/vintage_radio.jpg',
            'Old Black & White CRT Television': 'products/main/crt_television.jpg',
            'Antique Brass Wall Clock': 'products/main/brass_wall_clock.jpg',
            'Hand-Carved Rosewood Chair': 'products/main/rosewood_chair.jpg',
            'Dhokra Brass Horse Figurine': 'products/main/dhokra_brass_horse.jpg',
            'Pochampally Ikat Dupatta': 'products/main/ikat_dupatta.jpg',
            'Aranmula-style Bell Metal Lamp': 'products/main/bell_metal_lamp.jpg',
            'Vintage Rotary Dial Phone': 'products/main/rotary_dial_phone.jpg',
            'Channapatna Wooden Toy Set': 'products/main/wooden_toys.jpg',
            'Madhubani Painting on Handmade Paper': 'products/main/madhubani_painting.jpg',
            'Antique Coin Collection (25 pcs)': 'products/main/antique_coins.jpg',
            'Vintage Film Camera (Agfa)': 'products/main/vintage_camera.jpg',
            'Terracotta Wall Plate': 'products/main/terracotta_plate.jpg',
            'Brass Diya Set (6 pcs)': 'products/main/brass_diyas.jpg',
            'aranmula kannadi': 'products/main/Aranmulakannadi-AM12614WR-02_530x2x.webp',
        }

        created_products = []
        for pdata in products_data:
            cat = cat_map[pdata['cat']]
            seller = seller_profiles[pdata['seller']]
            img_path = sample_images.get(pdata['name'])
            p, was_created = Product.objects.get_or_create(
                name=pdata['name'],
                seller=seller,
                defaults={
                    'category': cat,
                    'description': pdata['desc'],
                    'price': pdata['price'],
                    'seller_discount': pdata['seller_discount'],
                    'stock': pdata['stock'],
                    'location': pdata['location'],
                    'status': pdata['status'],
                    'reject_reason': pdata.get('reject_reason', ''),
                    'main_image': img_path if img_path else None,
                    'emoji': pdata['emoji'],
                    'hue': pdata['hue'],
                    'promoted': pdata['promoted'],
                }
            )
            if not p.main_image and img_path:
                p.main_image = img_path
                p.save(update_fields=['main_image'])
            created_products.append(p)

            # Link campaign
            if pdata.get('in_campaign'):
                CampaignProduct.objects.get_or_create(campaign=campaign, product=p)

            # Add boost if promoted
            if pdata['promoted'] and pdata['status'] == Product.STATUS_APPROVED:
                Boost.objects.get_or_create(
                    product=p,
                    plan=plan_objects[0],
                    defaults={
                        'start_date': today,
                        'end_date': today + timedelta(days=7),
                        'status': Boost.STATUS_ACTIVE,
                    }
                )

        # 9. Reviews for the first 3 products
        reviews_data = [
            (created_products[0], buyer1, 5, 'Fresh and exactly as described. Packaging was very careful.'),
            (created_products[0], buyer2, 4, 'Good quality, sound is surprisingly warm and clear!'),
            (created_products[1], buyer3, 5, 'Reminds me of my grandmother\'s house. Arrived safely.'),
            (created_products[2], buyer1, 5, 'Gorgeous pendulum clock, sounds majestic in the hallway.'),
            (created_products[3], buyer2, 5, 'Solid rosewood, very sturdy and beautiful craftsmanship.'),
        ]

        for prod, reviewer, rating, text in reviews_data:
            Review.objects.get_or_create(
                product=prod,
                reviewer=reviewer,
                defaults={'rating': rating, 'text': text, 'is_approved': True}
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated RuralConnect demo data!'))
