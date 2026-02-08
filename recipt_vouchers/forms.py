from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(
        label='',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search Vehicle Number, Owner',
            'class': 'form-control',  # Bootstrap class for consistent styling
            'style': 'width: 250px; height: 50px; margin-top: 10px; margin-left: 70px; text-align: center;'
        })
    )