from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(
        label='',
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Search any Field',
                'class': 'form-control search-input',
                'style': 'height: 50px; text-align: center;'
            }
        )
    )