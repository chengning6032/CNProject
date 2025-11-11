from django.shortcuts import render, redirect
import datetime
from django.core.mail import send_mail
from django.conf import settings
from .forms import ContactForm


def homepage(request):
    now = datetime.datetime.now()  # 現在時間
    context = {'now': now}
    return render(request, 'homepage.html', context)

def CZ_homepage(request):
    now = datetime.datetime.now()  # 現在時間
    context = {'now': now}
    return render(request, 'CZ_Home.html', context)

def CZ_about(request):
    now = datetime.datetime.now()  # 現在時間
    context = {'now': now}
    return render(request, 'CZ_About.html', context)

def CZ_services(request):
    now = datetime.datetime.now()  # 現在時間
    context = {'now': now}
    return render(request, 'CZ_services.html', context)


def CZ_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # 表單數據驗證成功
            name = form.cleaned_data['name']
            from_email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # 組裝郵件內容
            full_message = f"寄件人姓名: {name}\n" \
                           f"寄件人信箱: {from_email}\n" \
                           f"主旨: {subject}\n\n" \
                           f"訊息內容:\n{message}"

            # 發送郵件
            send_mail(
                f'[官網聯絡表單] - {subject}', # 郵件標題
                full_message,                 # 郵件內容
                settings.EMAIL_HOST_USER,     # 寄件人信箱 (從 settings.py 讀取)
                [settings.ADMIN_EMAIL],       # 收件人信箱列表
                fail_silently=False,
            )
            # 重新導向到成功頁面
            return redirect('CZ_contact_success')
    else:
        # GET 請求，顯示一個空的表單
        form = ContactForm()

    return render(request, 'CZ_contact.html', {'form': form})


def CZ_contact_success(request):
    """
    顯示一個簡單的「發送成功」頁面
    """
    return render(request, 'CZ_contact_success.html')






