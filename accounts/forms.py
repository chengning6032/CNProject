# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, help_text='請輸入有效的電子郵件地址，將用於接收驗證碼。')
    verification_code = forms.CharField(max_length=6, required=False, help_text='請輸入您收到的 6 位數驗證碼。')
    phone_number = forms.CharField(max_length=20, required=True, help_text='格式：0912-345-678')
    elementary_school = forms.CharField(max_length=100, required=True, help_text='請輸入您的國小全名')

    class Meta(UserCreationForm.Meta):
        model = User
        # 【核心修改】將新欄位加入 fields，但注意它們不屬於 User 模型
        fields = ('username', 'email')