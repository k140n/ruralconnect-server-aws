"""Forms for account registration and login."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, SellerProfile, BuyerProfile, DeliveryAddress
from marketplace.form_utils import add_bootstrap_classes


class BuyerRegistrationForm(forms.ModelForm):
    """Registration form for buyers/shoppers."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'At least 8 characters'}),
        min_length=8,
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}),
        label='Confirm password'
    )
    terms = forms.BooleanField(required=True, label='I accept the terms and conditions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields['full_name'].widget.attrs.update({'placeholder': 'e.g. Priya Sharma'})
        self.fields['email'].widget.attrs.update({'placeholder': 'name@example.com'})
        self.fields['phone'].widget.attrs.update({'placeholder': '10-digit mobile number (optional)'})
        self.fields['phone'].required = False

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone']
        labels = {
            'full_name': 'Full name',
            'email': 'Email address',
            'phone': 'Phone number (optional)',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords must match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_BUYER
        if commit:
            user.save()
        return user


class SellerRegistrationForm(forms.ModelForm):
    """Registration form matching register.html fields."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'At least 8 characters'}),
        min_length=8,
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}),
        label='Confirm password'
    )
    business_name = forms.CharField(
        max_length=200,
        label='Business or seller name',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Kerala Heritage Crafts'})
    )
    location = forms.CharField(
        max_length=300,
        label='Location (village, district, state)',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Aranmula, Pathanamthitta, Kerala'})
    )
    terms = forms.BooleanField(required=True, label='I accept the terms and conditions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields['full_name'].widget.attrs.update({'placeholder': 'e.g. Rajesh Kumar'})
        self.fields['email'].widget.attrs.update({'placeholder': 'artisan@example.com'})
        self.fields['phone'].widget.attrs.update({'placeholder': '10-digit mobile number'})

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone']
        labels = {
            'full_name': 'Full name',
            'email': 'Email address',
            'phone': 'Phone number',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and (not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789'):
            raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords must match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_SELLER
        if commit:
            user.save()
            SellerProfile.objects.create(
                user=user,
                business_name=self.cleaned_data['business_name'],
                location=self.cleaned_data['location'],
            )
        return user



class EmailLoginForm(AuthenticationForm):
    """Standard login form using email instead of username."""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': 'name@example.com',
            'class': 'form-control',
            'autocomplete': 'email'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Enter your password',
            'class': 'form-control',
            'autocomplete': 'current-password'
        })

    class Meta:
        fields = ['username', 'password']


INDIAN_STATES = [
    ('Kerala', 'Kerala'),
    ('Tamil Nadu', 'Tamil Nadu'),
    ('Karnataka', 'Karnataka'),
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Telangana', 'Telangana'),
    ('Maharashtra', 'Maharashtra'),
    ('Delhi', 'Delhi (NCT)'),
    ('Gujarat', 'Gujarat'),
    ('Rajasthan', 'Rajasthan'),
    ('Uttar Pradesh', 'Uttar Pradesh'),
    ('West Bengal', 'West Bengal'),
    ('Punjab', 'Punjab'),
    ('Haryana', 'Haryana'),
    ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Bihar', 'Bihar'),
    ('Odisha', 'Odisha'),
    ('Assam', 'Assam'),
    ('Goa', 'Goa'),
    ('Himachal Pradesh', 'Himachal Pradesh'),
    ('Uttarakhand', 'Uttarakhand'),
    ('Jharkhand', 'Jharkhand'),
    ('Chhattisgarh', 'Chhattisgarh'),
    ('Jammu and Kashmir', 'Jammu and Kashmir'),
    ('Other', 'Other State / UT'),
]


class BuyerProfileForm(forms.ModelForm):
    """Form for buyers to update profile details and default delivery address."""
    full_name = forms.CharField(max_length=150, required=True, label='Full Name')
    phone = forms.CharField(max_length=15, required=False, label='Primary Mobile Number')
    state = forms.ChoiceField(choices=INDIAN_STATES, required=True, initial='Kerala', label='State')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.user = user
            self.fields['full_name'].initial = user.full_name
            self.fields['phone'].initial = user.phone
        
        add_bootstrap_classes(self)

        self.fields['shipping_address'].widget = forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Flat / House No., Building Name, Street / Locality'
        })
        self.fields['full_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g. Kiran Medowa'
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '10-digit mobile number',
            'maxlength': '10',
            'inputmode': 'numeric'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g. Thiruvalla'
        })
        self.fields['state'].widget.attrs.update({
            'class': 'form-select'
        })
        self.fields['postal_code'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '689102',
            'maxlength': '6',
            'inputmode': 'numeric'
        })
        self.fields['landmark'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g. Near Kurishumoode Junction, Behind Temple'
        })
        self.fields['alt_phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Alternative 10-digit mobile',
            'maxlength': '10',
            'inputmode': 'numeric'
        })

    class Meta:
        model = BuyerProfile
        fields = ['shipping_address', 'city', 'state', 'postal_code', 'landmark', 'alt_phone']
        labels = {
            'shipping_address': 'Flat / House No. & Street Address',
            'city': 'City / Town',
            'state': 'State',
            'postal_code': 'PIN Code',
            'landmark': 'Landmark (Optional)',
            'alt_phone': 'Alternate Phone (Optional)',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean_alt_phone(self):
        phone = self.cleaned_data.get('alt_phone', '').strip()
        if phone:
            if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean_postal_code(self):
        code = self.cleaned_data.get('postal_code', '').strip()
        if code and (not code.isdigit() or len(code) != 6):
            raise forms.ValidationError('PIN code must be a 6-digit number.')
        return code

    def save(self, commit=True):
        profile = super().save(commit=False)
        if hasattr(self, 'user') and self.user:
            self.user.full_name = self.cleaned_data.get('full_name', '').strip()
            self.user.phone = self.cleaned_data.get('phone', '').strip()
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class PersonalDetailsForm(forms.ModelForm):
    """Form to edit ONLY personal account details (Name and Phone)."""
    full_name = forms.CharField(
        max_length=150,
        required=True,
        label='Full Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kiran Medowa'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        label='Primary Mobile Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10-digit mobile number',
            'maxlength': '10',
            'inputmode': 'numeric'
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'phone']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone


class DeliveryAddressForm(forms.ModelForm):
    """Form to add or edit a specific delivery address."""
    state = forms.ChoiceField(choices=INDIAN_STATES, required=True, initial='Kerala', label='State')

    class Meta:
        model = DeliveryAddress
        fields = [
            'address_type', 'full_name', 'phone', 'street_address',
            'city', 'state', 'postal_code', 'landmark', 'alt_phone', 'is_default'
        ]
        labels = {
            'address_type': 'Address Type',
            'full_name': 'Recipient Full Name',
            'phone': 'Delivery Contact Phone',
            'street_address': 'Flat / House No. & Street Address',
            'city': 'City / Town',
            'state': 'State',
            'postal_code': 'PIN Code',
            'landmark': 'Landmark (Optional)',
            'alt_phone': 'Alternate Phone (Optional)',
            'is_default': 'Set as my default delivery address',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields['address_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['full_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'e.g. Kiran Medow'})
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '10-digit delivery mobile number',
            'maxlength': '10',
            'inputmode': 'numeric'
        })
        self.fields['street_address'].widget = forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Flat/House No., Building Name, Street / Locality'
        })
        self.fields['city'].widget.attrs.update({'class': 'form-control', 'placeholder': 'e.g. Thiruvalla'})
        self.fields['state'].widget.attrs.update({'class': 'form-select'})
        self.fields['postal_code'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '689102',
            'maxlength': '6',
            'inputmode': 'numeric'
        })
        self.fields['landmark'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g. Near Kurishumoode Junction, Behind Temple'
        })
        self.fields['alt_phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Optional backup 10-digit mobile',
            'maxlength': '10',
            'inputmode': 'numeric'
        })
        self.fields['is_default'].widget.attrs.update({'class': 'form-check-input'})

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError('Delivery contact phone number is required.')
        if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
            raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean_alt_phone(self):
        phone = self.cleaned_data.get('alt_phone', '').strip()
        if phone:
            if not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')
        return phone

    def clean_postal_code(self):
        code = self.cleaned_data.get('postal_code', '').strip()
        if not code or not code.isdigit() or len(code) != 6:
            raise forms.ValidationError('PIN code must be a 6-digit number.')
        return code

