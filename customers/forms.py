from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(
        label='',
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Search any Field',
                'class': 'form-control',
                'style': 'height: 50px; width: 300px; text-align: center;'
            }
        )
    )

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField()