from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        label='您的姓名',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': ' '})
    )
    email = forms.EmailField(
        label='電子郵件',
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': ' '})
    )
    subject = forms.CharField(
        label='主旨',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': ' '})
    )
    message = forms.CharField(
        label='訊息內容',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': ' '})
    )