from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, SellerProfile
from marketplace.models import Product, Category, Campaign, CampaignProduct


class SellerVerificationFlowTests(TestCase):
    def setUp(self):
        # Create seller user
        self.seller_user = User.objects.create_user(
            email='artisan@example.com',
            password='TestPassword123!',
            full_name='Ramesh Mastercraft',
            role=User.ROLE_SELLER,
            is_active=True,
        )
        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            business_name='Ramesh Handlooms',
            location='Kannur, Kerala',
        )

        # Create platform admin user
        self.admin_user = User.objects.create_user(
            email='admin@ruralconnect.in',
            password='AdminPassword123!',
            full_name='Admin Lead',
            role=User.ROLE_ADMIN,
            is_active=True,
        )

        # Create category and product
        self.category = Category.objects.create(name='Handloom Sarees', slug='handloom-sarees')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Kasavu Cotton Saree',
            description='Handwoven traditional saree',
            price=2000,
            stock=15,
            status=Product.STATUS_APPROVED,
        )

        # Create campaign
        today = timezone.now().date()
        self.campaign = Campaign.objects.create(
            name='Diwali Handloom Festival',
            description='Special 20% discount on authentic textiles',
            discount_percent=20,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=10),
            is_active=True,
            allow_seller_enrollment=True,
        )

    def test_seller_kyc_submission(self):
        self.client.login(email='artisan@example.com', password='TestPassword123!')

        test_file = SimpleUploadedFile(
            'pehchan_card.pdf',
            b'%PDF-1.4 test dummy pdf content',
            content_type='application/pdf'
        )

        response = self.client.post(reverse('seller:profile'), {
            'action': 'submit_kyc',
            'verification_doc_type': SellerProfile.DOC_PEHCHAN,
            'verification_id_number': 'PHC-KL-2023-8821',
            'verification_document': test_file,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.STATUS_PENDING)
        self.assertEqual(self.seller.verification_id_number, 'PHC-KL-2023-8821')
        self.assertTrue(bool(self.seller.verification_document))
        self.assertIsNotNone(self.seller.verification_submitted_at)
        self.assertFalse(self.seller.is_verified)

    def test_admin_approve_kyc(self):
        self.seller.verification_status = SellerProfile.STATUS_PENDING
        self.seller.verification_doc_type = SellerProfile.DOC_PEHCHAN
        self.seller.verification_id_number = 'PHC-KL-2023-8821'
        self.seller.save()

        self.client.login(email='admin@ruralconnect.in', password='AdminPassword123!')

        response = self.client.post(
            reverse('platform_admin:review_seller_verification', args=[self.seller.pk]),
            {'action': 'approve'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.is_verified)
        self.assertEqual(self.seller.verification_status, SellerProfile.STATUS_VERIFIED)
        self.assertIsNotNone(self.seller.verification_reviewed_at)
        self.assertEqual(self.seller.verification_rejection_reason, '')

    def test_admin_reject_kyc(self):
        self.seller.verification_status = SellerProfile.STATUS_PENDING
        self.seller.save()

        self.client.login(email='admin@ruralconnect.in', password='AdminPassword123!')

        response = self.client.post(
            reverse('platform_admin:review_seller_verification', args=[self.seller.pk]),
            {
                'action': 'reject',
                'rejection_reason': 'The uploaded image was blurry. Please provide a clear scan.'
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.is_verified)
        self.assertEqual(self.seller.verification_status, SellerProfile.STATUS_REJECTED)
        self.assertIn('blurry', self.seller.verification_rejection_reason)

    def test_seller_enroll_product_in_campaign(self):
        self.client.login(email='artisan@example.com', password='TestPassword123!')

        response = self.client.post(reverse('seller:promotions'), {
            'action': 'enroll_campaign',
            'campaign_id': self.campaign.pk,
            'product_ids': [self.product.pk],
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        cp = CampaignProduct.objects.filter(campaign=self.campaign, product=self.product).first()
        self.assertIsNotNone(cp)
        self.assertEqual(cp.enrolled_by, CampaignProduct.ENROLLED_BY_SELLER)

        # Check effective campaign discount applies
        self.assertEqual(self.product.active_campaign_discount(), 20)
        self.assertEqual(self.product.final_price(), 1600.0)

    def test_seller_withdraw_product_from_campaign(self):
        cp = CampaignProduct.objects.create(
            campaign=self.campaign,
            product=self.product,
            enrolled_by=CampaignProduct.ENROLLED_BY_SELLER,
        )

        self.client.login(email='artisan@example.com', password='TestPassword123!')

        response = self.client.post(reverse('seller:promotions'), {
            'action': 'withdraw_campaign',
            'campaign_product_id': cp.pk,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CampaignProduct.objects.filter(pk=cp.pk).exists())
        self.assertEqual(self.product.active_campaign_discount(), 0)
        self.assertEqual(self.product.final_price(), 2000.0)


