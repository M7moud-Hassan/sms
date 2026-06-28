from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(
        label='',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search Vehicle Number, Owner',
            'class': 'form-control search-input',  # styled via CSS instead of inline width
            'style': 'height: 50px; margin-top: 10px; margin-left: 10px; text-align: center;'
        })
    )