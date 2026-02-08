from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(label='', max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search Any Additional Field', 'style': 'width: 220px; height: 37px; margin-top: 16px; margin-left: 5px; text-align: center;'}))