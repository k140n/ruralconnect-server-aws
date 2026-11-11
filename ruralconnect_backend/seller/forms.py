"""Forms for the seller portal."""

from django import forms
from marketplace.models import Product, Category
from accounts.models import SellerProfile


class ProductForm(forms.ModelForm):
    """Add/edit product form matching add-product.html fields."""

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price',
            'seller_discount', 'stock', 'location', 'main_image',
        ]
        labels = {
            'name': 'Product name',
            'category': 'Category',
            'description': 'Description',
            'price': 'Price (₹)',
            'seller_discount': 'Your discount (%)',
            'stock': 'Quantity in stock',
            'location': 'Location',
            'main_image': 'Main image',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Hand-Carved Sheesham Wood Mirror',
                'id': 'id_name',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'minlength': '20',
                'placeholder': 'Tell the story of this product, craftsmanship, materials used, dimensions, and care instructions (min 20 characters)...',
                'id': 'id_description',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': 'e.g. 1299',
                'id': 'price',
            }),
            'seller_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '90',
                'placeholder': '0',
                'id': 'discount',
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'e.g. 15',
                'id': 'id_stock',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Madhubani, Bihar or Jaipur, Rajasthan',
                'id': 'id_location',
            }),
            'main_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_main_image',
            }),
        }

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        if len(desc) < 20:
            raise forms.ValidationError('Description must be at least 20 characters.')
        return desc

    def clean_seller_discount(self):
        d = self.cleaned_data.get('seller_discount', 0)
        if d and (d < 0 or d > 90):
            raise forms.ValidationError('Discount must be between 0 and 90.')
        return d


from marketplace.form_utils import add_bootstrap_classes


class SellerProfileForm(forms.ModelForm):
    """Edit seller profile fields with user contact details."""
    full_name = forms.CharField(
        max_length=150,
        label='Full name / Primary contact',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Meena Devi',
            'class': 'form-control',
        })
    )
    phone = forms.CharField(
        max_length=15,
        label='Phone number',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 9847012345',
            'class': 'form-control',
        })
    )

    class Meta:
        model = SellerProfile
        fields = ['business_name', 'location', 'bio']
        labels = {
            'business_name': 'Business / seller name',
            'location': 'Workshop / store location',
            'bio': 'About your shop & craft story',
        }
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Meena Devi Antiques',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Thiruvananthapuram, Kerala',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share the story behind your craft, heritage materials, techniques, and workshop origins...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['phone'].initial = self.instance.user.phone
        add_bootstrap_classes(self)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            digits = ''.join(c for c in phone if c.isdigit())
            if len(digits) == 10 and digits[0] in '6789':
                return digits
            if len(digits) > 10 and digits.startswith('91') and len(digits) == 12:
                return digits[-10:]
            raise forms.ValidationError('Please enter a valid 10-digit Indian mobile number.')
        return phone

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if hasattr(profile, 'user') and profile.user:
            profile.user.full_name = self.cleaned_data.get('full_name', profile.user.full_name)
            profile.user.phone = self.cleaned_data.get('phone', profile.user.phone)
            profile.user.save()
        return profile


class SellerVerificationForm(forms.ModelForm):
    """KYC / Artisan identity verification submission form."""
    class Meta:
        model = SellerProfile
        fields = ['verification_doc_type', 'verification_id_number', 'verification_document']
        labels = {
            'verification_doc_type': 'Artisan ID / Document Type',
            'verification_id_number': 'ID Card / Certificate Number',
            'verification_document': 'Upload Document Proof (PDF or Image)',
        }
        widgets = {
            'verification_doc_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'verification_id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. PHC-KL-2023-8941, Udyam No., or Aadhaar last 4 digits',
            }),
            'verification_document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.webp',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['verification_doc_type'].required = True
        self.fields['verification_id_number'].required = True
        # If document already exists, user can keep it without re-uploading every time
        if not (self.instance and self.instance.verification_document):
            self.fields['verification_document'].required = True
        else:
            self.fields['verification_document'].required = False
        add_bootstrap_classes(self)

    def clean_verification_document(self):
        doc = self.cleaned_data.get('verification_document')
        if doc and hasattr(doc, 'size'):
            if doc.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 5MB. Please upload a compressed PDF or image.')
            ext = doc.name.split('.')[-1].lower() if '.' in doc.name else ''
            if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
                raise forms.ValidationError('Unsupported file format. Please upload a PDF, JPG, PNG, or WEBP.')
        return doc


