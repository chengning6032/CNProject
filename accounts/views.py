# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from datetime import datetime # 【核心新增】匯入 datetime 模組
from django.utils import timezone # 【核心】匯入 Django 的 timezone 工具
from .forms import SignUpForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
import json
import random
from .models import Profile # 確保匯入了 Profile
from django.contrib import messages # 【核心新增】匯入 Django 的 messages 框架


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        code_from_user = form.data.get('verification_code')
        code_in_session = request.session.get('verification_code')
        email_in_session = request.session.get('verification_email')

        if not code_in_session or form.data.get('email') != email_in_session:
            form.add_error(None, '請先發送並驗證您的電子郵件。')
        elif code_from_user != code_in_session:
            form.add_error('verification_code', '驗證碼不正確。')
        else:
            if form.is_valid():
                user = form.save()

                # 【核心新增】儲存額外資訊到 Profile
                user.profile.phone_number = form.cleaned_data.get('phone_number')
                user.profile.elementary_school = form.cleaned_data.get('elementary_school')
                user.profile.save()

                del request.session['verification_code']
                del request.session['verification_email']
                login(request, user)
                return redirect('homepage')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


# 【核心新增】一个专门用于发送验证码的 API 视图
def send_verification_code_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')

            if not email:
                return JsonResponse({'status': 'error', 'message': '未提供電子郵件地址。'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': '此電子郵件已被註冊。'}, status=400)

            # 生成验证码并存储在 session 中
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            request.session['verification_code'] = code
            request.session['verification_email'] = email
            request.session.set_expiry(300)  # 验证码 5 分钟后过期

            # 发送邮件 (在开发模式下会打印到控制台)
            send_mail(
                '您的 OLI 帳號驗證碼',
                f'您好，感謝您註冊 OLI。您的驗證碼是： {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            print(f"--- 驗證碼 {code} 已發送到 {email} (開發模式) ---")

            return JsonResponse({'status': 'success', 'message': f'驗證碼已發送到 {email}，請在5分鐘內輸入。'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '無效的請求格式。'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'伺服器內部錯誤: {str(e)}'}, status=500)

    return JsonResponse({'status': 'error', 'message': '僅接受 POST 請求。'}, status=405)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('homepage') # 登入成功後，跳轉回首頁
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('homepage') # 登出後，跳轉回首頁


@login_required
@login_required
def profile_view(request):
    """
    【核心修正】
    在將日期傳遞給模板前，先將其轉換為伺服器設定的本地時間 (Asia/Taipei)。
    """
    profile = request.user.profile

    processed_modules = {}

    if isinstance(profile.purchased_modules, dict):
        for module_id, data in profile.purchased_modules.items():
            processed_data = data.copy()

            # 【核心修正】將 UTC 時間轉換為本地時間後再格式化
            try:
                # 1. 從 ISO 字串解析為帶有時區的 datetime 物件
                purchase_dt_utc = datetime.fromisoformat(data['purchase_date'].replace('Z', '+00:00'))
                # 2. 使用 timezone.localtime() 將其轉換為本地時間
                purchase_dt_local = timezone.localtime(purchase_dt_utc)
                # 3. 格式化本地時間
                processed_data['purchase_date_str'] = purchase_dt_local.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError, KeyError):
                processed_data['purchase_date_str'] = "日期無效"

            try:
                expiration_dt_utc = datetime.fromisoformat(data['expiration_date'].replace('Z', '+00:00'))
                expiration_dt_local = timezone.localtime(expiration_dt_utc)
                processed_data['expiration_date_str'] = expiration_dt_local.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError, KeyError):
                processed_data['expiration_date_str'] = "日期無效"

            processed_modules[module_id] = processed_data

    context = {
        'user': request.user,
        'profile': profile,
        'processed_modules': processed_modules,
    }

    return render(request, 'accounts/profile.html', context)


def verify_email_view(request):
    # 这是一个占位视图，未来可以用来处理点击邮件链接验证的功能
    return redirect('homepage')

# 【核心新增】忘記帳號視圖
def forgot_username_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        elementary_school = request.POST.get('elementary_school')

        # 進行輸入驗證
        if not all([email, phone_number, elementary_school]):
            messages.error(request, '所有欄位都必須填寫！')
            return redirect('forgot_username')

        try:
            # 1. 根據 email 找到 User
            # 2. 透過 user.profile 進行關聯查詢，比對 phone_number 和 elementary_school
            user = User.objects.get(
                email=email,
                profile__phone_number=phone_number,
                profile__elementary_school=elementary_school
            )

            # 如果程式能執行到這裡，代表找到了匹配的使用者
            # 3. 發送郵件
            send_mail(
                'OLI 平台 - 您的帳號資訊',
                f'您好，\n\n您在 OLI 平台的使用者名稱是： {user.username}\n\n請妥善保管您的帳號資訊。\n\nOLI 平台團隊 敬上',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # 4. 創建成功訊息
            messages.success(request, f'帳號資訊已成功發送到您的信箱 {email}，請前往查看。')
            return redirect('login')  # 成功後，引導使用者去登入頁面

        except User.DoesNotExist:
            # 【核心功能】如果 User.objects.get() 找不到任何匹配項，會拋出此異常
            # 5. 創建錯誤訊息
            messages.error(request, '您輸入的資料不正確或不存在，請確認後再試一次。')
            return redirect('forgot_username')  # 失敗後，停留在當前頁面以顯示錯誤訊息
        except Exception as e:
            # 處理其他可能的錯誤，例如郵件發送失敗
            messages.error(request, f'發生未知錯誤，請稍後再試。錯誤詳情: {e}')
            return redirect('forgot_username')

    return render(request, 'accounts/forgot_username.html')

# 【核心新增】忘記密碼視圖
def forgot_password_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        elementary_school = request.POST.get('elementary_school')

        if not all([username, phone_number, elementary_school]):
            messages.error(request, '所有欄位都必須填寫！')
            return redirect('forgot_password')

        try:
            user = User.objects.get(
                username=username,
                profile__phone_number=phone_number,
                profile__elementary_school=elementary_school
            )

            # TODO: 實現發送密碼重設連結的邏輯
            # (這部分較複雜，涉及 token 生成，我們可以在下一步完成)
            # 這裡我們先模擬成功的情況

            messages.success(request, f'身份驗證成功！密碼重設連結已發送到您的註冊信箱 {user.email}。')
            return redirect('login')

        except User.DoesNotExist:
            # 【核心功能】同樣的，如果找不到用戶，就顯示錯誤訊息
            messages.error(request, '您輸入的資料不正確或不存在，請確認後再試一次。')
            return redirect('forgot_password')
        except Exception as e:
            messages.error(request, f'發生未知錯誤，請稍後再試。')
            return redirect('forgot_password')

    return render(request, 'accounts/forgot_password.html')