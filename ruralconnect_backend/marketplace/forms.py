"""Forms for marketplace: product reviews."""

from django import forms
from .models import Review
from .form_utils import add_bootstrap_classes


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(
                choices=[
                    (5, '★★★★★ (5 - Excellent)'),
                    (4, '★★★★☆ (4 - Very good)'),
                    (3, '★★★☆☆ (3 - Average)'),
                    (2, '★★☆☆☆ (2 - Poor)'),
                    (1, '★☆☆☆☆ (1 - Terrible)'),
                ]
            ),
            'text': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Share your experience with this product, its quality, packaging...',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
