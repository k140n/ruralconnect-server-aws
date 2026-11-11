from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, SellerProfile
from marketplace.models import Category, Product, CartItem
from marketplace import cart_services


class UserCartTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.seller_user = User.objects.create_user(
            email='seller@test.com',
            password='password123',
            full_name='Seller User',
            role=User.ROLE_SELLER
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name='Artisan Shop',
            phone='9876543210',
            state='Kerala',
            craft_type='Handicrafts'
        )
        self.product1 = Product.objects.create(
            name='Clay Vase',
            description='Handmade clay vase',
            category=self.category,
            seller=self.seller_profile,
            price=500.00,
            stock=10,
            status=Product.STATUS_APPROVED
        )
        self.product2 = Product.objects.create(
            name='Brass Lamp',
            description='Traditional brass lamp',
            category=self.category,
            seller=self.seller_profile,
            price=1200.00,
            stock=5,
            status=Product.STATUS_APPROVED
        )

        self.user_a = User.objects.create_user(
            email='usera@test.com',
            password='password123',
            full_name='User A',
            role=User.ROLE_BUYER
        )
        self.user_b = User.objects.create_user(
            email='userb@test.com',
            password='password123',
            full_name='User B',
            role=User.ROLE_BUYER
        )

    def test_anonymous_and_user_cart_flow(self):
        client = Client()

        # 1. Initially signed out: cart count is 0
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['cart_count'], 0)

        # 2. Add product1 to cart as guest
        resp = client.post(
            reverse('marketplace:cart_add_api'),
            data={'product_id': self.product1.id, 'quantity': 2},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['cart_count'], 2)

        # 3. Log in as user A -> guest cart should merge into user A's cart
        resp = client.post(reverse('accounts:login'), {
            'username': 'usera@test.com',
            'password': 'password123',
        })
        self.assertRedirects(resp, reverse('marketplace:home'))

        # Home page for User A should show cart_count 2
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['cart_count'], 2)

        # In DB, CartItem belongs to User A
        self.assertEqual(CartItem.objects.filter(user=self.user_a).count(), 1)
        self.assertEqual(CartItem.objects.filter(user=self.user_a).first().quantity, 2)

        # 4. User A adds another product
        resp = client.post(
            reverse('marketplace:cart_add_api'),
            data={'product_id': self.product2.id, 'quantity': 1},
            content_type='application/json'
        )
        self.assertEqual(resp.json()['cart_count'], 3)
        self.assertEqual(CartItem.objects.filter(user=self.user_a).count(), 2)

        # 5. User A logs out
        client.get(reverse('accounts:logout'))

        # When logged out, cart count must be 0
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['cart_count'], 0)

        # Cart API for logged out user should return empty items
        resp = client.get(reverse('marketplace:cart_items_api'))
        self.assertEqual(resp.json()['items'], [])
        self.assertEqual(resp.json()['cart_count'], 0)

        # BUT User A's items are still in the database!
        self.assertEqual(CartItem.objects.filter(user=self.user_a).count(), 2)

        # 6. User B logs in -> User B's cart count should be 0
        client.post(reverse('accounts:login'), {
            'username': 'userb@test.com',
            'password': 'password123',
        })
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['cart_count'], 0)
        resp = client.get(reverse('marketplace:cart_items_api'))
        self.assertEqual(resp.json()['items'], [])

        # User B logs out
        client.get(reverse('accounts:logout'))

        # 7. User A logs back in -> User A's products should all still be there!
        client.post(reverse('accounts:login'), {
            'username': 'usera@test.com',
            'password': 'password123',
        })
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['cart_count'], 3)

        resp = client.get(reverse('marketplace:cart_items_api'))
        data = resp.json()
        self.assertEqual(data['cart_count'], 3)
        self.assertEqual(len(data['items']), 2)
        item_ids = [item['id'] for item in data['items']]
        self.assertIn(self.product1.id, item_ids)
        self.assertIn(self.product2.id, item_ids)

    def test_buyer_registration_flow(self):
        client = Client()
        resp = client.get(reverse('accounts:register'))
        self.assertEqual(resp.status_code, 200)

        # Register as buyer
        resp = client.post(reverse('accounts:register'), {
            'reg_type': 'buyer',
            'full_name': 'New Buyer Test',
            'email': 'newbuyer_test@example.com',
            'phone': '9876543210',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'terms': 'on',
        })
        self.assertEqual(resp.status_code, 302)

        created_user = User.objects.get(email='newbuyer_test@example.com')
        self.assertEqual(created_user.role, User.ROLE_BUYER)
        self.assertEqual(created_user.full_name, 'New Buyer Test')
        self.assertFalse(hasattr(created_user, 'seller_profile'))


class WishlistTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Handicrafts', slug='handicrafts')
        self.seller_user = User.objects.create_user(
            email='artisan@test.com',
            password='password123',
            full_name='Artisan Master',
            role=User.ROLE_SELLER
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name='Village Heritage Works',
            location='Kerala'
        )
        self.product = Product.objects.create(
            name='Handcarved Kathakali Mask',
            description='Authentic wooden mask',
            category=self.category,
            seller=self.seller_profile,
            price=1500.00,
            stock=4,
            status=Product.STATUS_APPROVED
        )
        self.buyer = User.objects.create_user(
            email='heritage_buyer@test.com',
            password='password123',
            full_name='Heritage Buyer',
            role=User.ROLE_BUYER
        )

    def test_guest_toggle_wishlist_unauthorized(self):
        client = Client()
        resp = client.post(reverse('marketplace:toggle_wishlist', kwargs={'product_id': self.product.id}))
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data['authenticated'])
        self.assertIn('login', data['login_url'])

    def test_authenticated_user_wishlist_toggle_and_move_to_cart(self):
        client = Client()
        client.force_login(self.buyer)

        # 1. Initially wishlist is empty
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['wishlist_count'], 0)
        self.assertEqual(len(resp.context['wishlist_product_ids']), 0)

        # 2. Toggle item -> Added
        resp = client.post(reverse('marketplace:toggle_wishlist', kwargs={'product_id': self.product.id}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['added'])
        self.assertEqual(data['wishlist_count'], 1)

        # 3. Context processor reflects change
        resp = client.get(reverse('marketplace:home'))
        self.assertEqual(resp.context['wishlist_count'], 1)
        self.assertIn(self.product.id, resp.context['wishlist_product_ids'])

        # 4. Wishlist page displays the item
        resp = client.get(reverse('marketplace:wishlist'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Handcarved Kathakali Mask')

        # 5. Move to Cart
        resp = client.post(reverse('marketplace:move_wishlist_to_cart', kwargs={'product_id': self.product.id}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 1)
        self.assertEqual(data['wishlist_count'], 0)

        # 6. Verify wishlist is now empty and cart has item
        resp = client.get(reverse('marketplace:wishlist'))
        self.assertEqual(resp.context['total_items'], 0)


