"""Add Bootstrap CSS classes to all form widgets automatically."""

from django import forms


def add_bootstrap_classes(form):
    """Apply Bootstrap classes to all form fields."""
    for field_name, field in form.fields.items():
        widget = field.widget
        css = widget.attrs.get('class', '')
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs['class'] = (css + ' form-check-input').strip()
        elif isinstance(widget, forms.Select):
            widget.attrs['class'] = (css + ' form-select').strip()
        elif isinstance(widget, forms.Textarea):
            widget.attrs['class'] = (css + ' form-control').strip()
        else:
            widget.attrs['class'] = (css + ' form-control').strip()
    return form
