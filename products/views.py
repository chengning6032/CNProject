# products/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

from accounts.models import Profile
from .models import Product, Order

# 從我們手動建立的 sdk 資料夾中引用 SDK
from sdk.ecpay_payment_sdk import ECPayPaymentSdk


def round_v3(num, decimal):
    str_deci = 1
    for _ in range(decimal):
        str_deci = str_deci / 10
    str_deci = str(str_deci)
    result = Decimal(str(num)).quantize(Decimal(str_deci), rounding=ROUND_HALF_UP)
    result = float(result)
    print(result)
    return result


@login_required
def product_list_view(request):
    """
    【核心修改】
    除了商品列表，還要傳遞使用者已購買的模組 ID 列表給模板。
    """
    products = Product.objects.all()

    # 獲取當前使用者的 Profile
    try:
        profile = request.user.profile
        # 獲取 purchased_modules 字典的所有鍵 (keys)，並轉換為列表
        # .keys() 返回一個視圖對象，list() 將其物化為列表
        purchased_module_ids = list(profile.purchased_modules.keys()) if isinstance(profile.purchased_modules,
                                                                                    dict) else []
    except Profile.DoesNotExist:
        purchased_module_ids = []

    context = {
        'products': products,
        'purchased_module_ids': purchased_module_ids,  # 將列表傳遞給模板
    }
    return render(request, 'products/product_list.html', context)


# 【核心新增】第一步：建立訂單，並生成導向綠界的表單
# products/views.py

@login_required
@require_POST
def ecpay_checkout_view(request):
    try:
        data = json.loads(request.body)
        cart_items = data.get('items', [])

        # 1. 如果購物車是空的，直接返回錯誤
        if not cart_items:
            return JsonResponse({'status': 'error', 'message': '購物車是空的'}, status=400)

        # 2. 【修正縮排】以下邏輯要向左縮排，與 if 對齊，代表「購物車有東西」時才執行
        # 計算商品小計 (Subtotal)
        subtotal = 0
        item_names = []
        for item in cart_items:
            product = Product.objects.get(product_id=item['id'])
            item_names.append(product.name)
            plan = item.get('plan', 'monthly')
            if plan == 'semiannually':
                price = product.prices.get('semiannually', 0)
            elif plan == 'annually':
                price = product.prices.get('annually', 0)
            else:
                price = product.prices.get('monthly', 0)

            subtotal += int(price)

        # 計算稅金與總金額
        # 建議：綠界金額必須是整數 (int)，這裡強制轉換一下比較保險
        tax_amount = int(round_v3(subtotal * 0.05, 0))

        # 總金額 = 小計 + 稅金
        total_amount = subtotal + tax_amount

        # 建立訂單
        merchant_trade_no = f"OLI{int(time.time())}"
        Order.objects.create(
            user=request.user,
            merchant_trade_no=merchant_trade_no,
            total_amount=total_amount,
            items=cart_items
        )

        # 準備要傳送給綠界的基礎參數字典
        current_ngrok_url = "https://impliably-unascertainable-shaunta.ngrok-free.dev"
        safe_redirect_url = f"{current_ngrok_url}/OLi/accounts/profile/"

        order_params = {
            'MerchantTradeNo': merchant_trade_no,  # 現在這裡一定找得到變數了
            'MerchantTradeDate': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'PaymentType': 'aio',
            'TotalAmount': total_amount,
            'TradeDesc': "OLI 工程設計模組訂閱",
            'ItemName': '#'.join(item_names),

            # 1. 這是唯一的返回路徑
            'ReturnURL': f"{current_ngrok_url}/OLi/products/ecpay-return/",

            # 2. 【關鍵修改】把這行註解掉！不要傳給綠界！
            # 'OrderResultURL': f"{current_ngrok_url}/OLi/products/ecpay-notify/",

            # 3. 輔助返回
            'ClientBackURL': safe_redirect_url,  # 建議直接回會員中心

            'ChoosePayment': 'Credit',
            'EncryptType': 1,
        }

        # debug print
        print("\n" + "=" * 30)
        print("正在建立綠界訂單...")
        print(f"前景要去 (ReturnURL):   {order_params['ReturnURL']}")
        print("=" * 30 + "\n")

        # 初始化 SDK
        sdk = ECPayPaymentSdk(
            MerchantID=settings.ECPAY_MERCHANT_ID,
            HashKey=settings.ECPAY_HASH_KEY,
            HashIV=settings.ECPAY_HASH_IV
        )

        final_order_params = sdk.create_order(order_params)
        action_url = settings.ECPAY_API_URL
        final_html_form = sdk.gen_html_post_form(action_url, final_order_params)

        return HttpResponse(final_html_form)

    except Exception as e:
        import traceback
        print("An error occurred in ecpay_checkout_view:")
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'伺服器發生未預期的錯誤: {e}'}, status=500)


# 【核心新增】第二步：使用者付款後，綠界將其瀏覽器導回此處 (前景)
@csrf_exempt
# products/views.py

# ... (記得要把原本 ecpay_notify_view 用到的 import 都補齊) ...

@csrf_exempt
def ecpay_return_view(request):
    # 2. 【新增】如果是 GET 請求 (例如按了上一頁，或直接輸入網址)，直接轉走
    if request.method == 'GET':
        return redirect('profile')  # 導向會員中心

    # 1. 取得資料
    post_data = request.POST.dict()

    # 2. 驗證 CheckMacValue (安全性檢查，不能省！)
    if 'CheckMacValue' not in post_data:
        # 如果沒有參數，可能是使用者直接輸入網址，導回首頁或顯示錯誤
        return redirect('profile')

    received_mac_value = post_data.pop('CheckMacValue')

    sdk = ECPayPaymentSdk(
        MerchantID=settings.ECPAY_MERCHANT_ID,
        HashKey=settings.ECPAY_HASH_KEY,
        HashIV=settings.ECPAY_HASH_IV
    )

    generated_mac_value = sdk.generate_check_value(post_data)

    if received_mac_value != generated_mac_value:
        return HttpResponse('MAC verification failed', status=400)

    # 3. 處理訂單邏輯 (複製 notify 的邏輯)
    merchant_trade_no = post_data.get('MerchantTradeNo')
    rtn_code = post_data.get('RtnCode')

    if rtn_code == '1':
        try:
            # 使用 transaction 確保資料一致性
            from django.db import transaction

            # 這裡稍微改一下，不要用 select_for_update，因為前景只有一次請求
            # 先檢查訂單是否已經處理過 (避免使用者重新整理頁面重複加值)
            order = Order.objects.get(merchant_trade_no=merchant_trade_no)

            if order.is_paid:
                # 如果已經付過了，直接顯示成功頁面
                return render(request, 'products/payment_success.html')

            with transaction.atomic():
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()

                profile_to_update = order.user.profile
                purchased = profile_to_update.purchased_modules if isinstance(profile_to_update.purchased_modules,
                                                                              dict) else {}
                today = timezone.now()

                for item in order.items:
                    module_id = item.get('id')
                    plan = item.get('plan')

                    try:
                        product = Product.objects.get(product_id=module_id)
                        product_name = product.name
                    except Product.DoesNotExist:
                        product_name = "Unknown Product"

                    if plan == PLAN_MONTHLY:
                        delta = relativedelta(months=1)
                    elif plan == PLAN_SEMIANNUALLY:
                        delta = relativedelta(months=6)
                    elif plan == PLAN_ANNUALLY:
                        delta = relativedelta(years=1)
                    else:
                        continue

                    # 續訂邏輯
                    if module_id in purchased and 'expiration_date' in purchased[module_id]:
                        try:
                            current_expiration_str = purchased[module_id]['expiration_date']
                            current_expiration = datetime.fromisoformat(current_expiration_str.replace('Z', '+00:00'))
                            base_date = max(current_expiration, today)
                        except (ValueError, TypeError):
                            base_date = today
                    else:
                        base_date = today

                    new_expiration_date = base_date + delta

                    purchased[module_id] = {
                        'name': product_name,
                        'plan': plan,
                        'purchase_date': today.isoformat(),
                        'expiration_date': new_expiration_date.isoformat(),
                    }

                profile_to_update.purchased_modules = purchased
                profile_to_update.save()

            # 【成功！】這時候回傳 HTML 頁面給使用者看
            return render(request, 'products/payment_success.html')

        except Exception as e:
            print(f"Error: {e}")
            return HttpResponse('Error processing order', status=500)

    # 失敗的話
    return HttpResponse('Payment failed', status=400)


# 【核心修正】統一方案名稱變數，避免打錯字
PLAN_MONTHLY = 'monthly'
PLAN_SEMIANNUALLY = 'semiannually'  # 請確認前端 value 是否也為 semiannually (無底線)
PLAN_ANNUALLY = 'annually'


# 【核心新增】第三步：綠界伺服器在背景發送通知到此處，進行真正的訂單更新 (後景)
@csrf_exempt
@require_POST
def ecpay_notify_view(request):
    # 1. 從綠界 POST 回來的資料中，取得所有參數
    post_data = request.POST.dict()

    # 2. 驗證 CheckMacValue
    if 'CheckMacValue' not in post_data:
        return HttpResponse('Invalid request: CheckMacValue not found', status=400)

    received_mac_value = post_data.pop('CheckMacValue')

    sdk = ECPayPaymentSdk(
        MerchantID=settings.ECPAY_MERCHANT_ID,
        HashKey=settings.ECPAY_HASH_KEY,
        HashIV=settings.ECPAY_HASH_IV
    )

    generated_mac_value = sdk.generate_check_value(post_data)

    if received_mac_value != generated_mac_value:
        return HttpResponse('MAC verification failed', status=400)

    # 3. 處理訂單邏輯
    merchant_trade_no = post_data.get('MerchantTradeNo', f"OLI{int(time.time())}TEST")
    rtn_code = post_data.get('RtnCode')

    # RtnCode 為 '1' 代表付款成功
    if rtn_code == '1':
        try:
            # 建議：使用 select_for_update 鎖定資料列，避免並發問題
            from django.db import transaction

            with transaction.atomic():
                # 尋找尚未標記為已付款的訂單
                try:
                    order = Order.objects.select_for_update().get(
                        merchant_trade_no=merchant_trade_no,
                        is_paid=False
                    )
                except Order.DoesNotExist:
                    # 如果訂單已付款 (綠界重發通知)，直接回傳 OK
                    if Order.objects.filter(merchant_trade_no=merchant_trade_no, is_paid=True).exists():
                        return HttpResponse('1|OK')
                    return HttpResponse('Order not found', status=404)

                # 更新訂單狀態
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()

                # 更新使用者 Profile
                profile_to_update = order.user.profile
                purchased = profile_to_update.purchased_modules if isinstance(profile_to_update.purchased_modules,
                                                                              dict) else {}

                today = timezone.now()

                for item in order.items:
                    module_id = item.get('id')
                    plan = item.get('plan')

                    # 取得產品名稱 (防止產品被刪除導致報錯)
                    try:
                        product = Product.objects.get(product_id=module_id)
                        product_name = product.name
                    except Product.DoesNotExist:
                        product_name = "Unknown Product"

                    # 計算時間增量 (統一變數名稱)
                    if plan == PLAN_MONTHLY:
                        delta = relativedelta(months=1)
                    elif plan == PLAN_SEMIANNUALLY:  # 這裡要跟前端一致
                        delta = relativedelta(months=6)
                    elif plan == PLAN_ANNUALLY:
                        delta = relativedelta(years=1)
                    else:
                        continue  # 未知方案跳過

                    # ===== 核心修正：續訂邏輯 (與 simulate_checkout_view 保持一致) =====
                    # 檢查使用者是否已經擁有該模組且尚未過期
                    if module_id in purchased and 'expiration_date' in purchased[module_id]:
                        try:
                            current_expiration_str = purchased[module_id]['expiration_date']
                            # 解析 ISO 格式日期 (處理可能出現的 'Z')
                            current_expiration = datetime.fromisoformat(current_expiration_str.replace('Z', '+00:00'))

                            # 如果目前期限比今天晚，就從目前期限往後加 (續訂)
                            # 如果目前期限已經過期，就從今天往後加 (重新訂閱)
                            base_date = max(current_expiration, today)
                        except (ValueError, TypeError):
                            base_date = today
                    else:
                        # 首次購買
                        base_date = today

                    new_expiration_date = base_date + delta
                    # ==========================================================

                    purchased[module_id] = {
                        'name': product_name,
                        'plan': plan,
                        'purchase_date': today.isoformat(),
                        'expiration_date': new_expiration_date.isoformat(),
                    }

                profile_to_update.purchased_modules = purchased
                profile_to_update.save()

            return HttpResponse('1|OK')

        except Exception as e:
            print(f"Error processing notification for order {merchant_trade_no}: {e}")
            # 這裡回傳 500，綠界會嘗試重送
            return HttpResponse('Internal server error', status=500)

    return HttpResponse('Payment not successful')


@login_required
@require_POST
def simulate_checkout_view(request):
    """
    【最終優化版】
    確保日期處理和資料庫寫入的每一個環節都無懈可擊。
    """
    try:
        data = json.loads(request.body)
        cart_items = data.get('items', [])
        if not isinstance(cart_items, list): raise ValueError("無效數據")

        profile_to_update = request.user.profile
        print(f"--- 處理使用者 '{request.user.username}' 的結帳請求 ---")

    except (json.JSONDecodeError, Profile.DoesNotExist, ValueError) as e:
        return JsonResponse({'status': 'error', 'message': f'請求無效: {e}'}, status=400)

    # 獲取現有的模組字典，如果為 None 或不是字典，則初始化為空字典
    purchased = profile_to_update.purchased_modules if isinstance(profile_to_update.purchased_modules, dict) else {}
    print(f"    - 使用者現有的模組: {purchased}")

    today = timezone.now()  # 使用帶有時區的當前時間

    try:
        for item in cart_items:
            module_id = item.get('id')
            plan = item.get('plan')
            if not all([module_id, plan]): continue

            product = Product.objects.get(product_id=module_id)

            if plan == 'monthly':
                delta = relativedelta(months=1)
            elif plan == 'semiannually':
                delta = relativedelta(months=6)
            elif plan == 'annually':
                delta = relativedelta(years=1)
            else:
                continue

            if module_id in purchased and 'expiration_date' in purchased[module_id]:
                # 續購邏輯
                current_expiration_str = purchased[module_id]['expiration_date']
                # 確保我們能正確解析帶有 'Z' 或 '+00:00' 的 ISO 格式
                current_expiration = datetime.fromisoformat(current_expiration_str.replace('Z', '+00:00'))
                base_date = max(current_expiration, today)
                new_expiration_date = base_date + delta
                print(
                    f"    - 續購模組 '{module_id}': 從 {base_date.strftime('%Y-%m-%d')} 延長至 {new_expiration_date.strftime('%Y-%m-%d')}")
            else:
                # 首次購買邏輯
                new_expiration_date = today + delta
                print(f"    - 首次購買模組 '{module_id}': 到期日為 {new_expiration_date.strftime('%Y-%m-%d')}")

            # 更新或創建該模組的詳細資訊
            purchased[module_id] = {
                'name': product.name,
                'plan': plan,
                'purchase_date': today.isoformat(),  # 儲存 ISO 格式
                'expiration_date': new_expiration_date.isoformat(),  # 儲存 ISO 格式
            }

    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'找不到商品 ID 為 "{module_id}" 的商品。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'處理購買時發生錯誤: {e}'}, status=500)

    # 將更新後的完整字典存回資料庫
    profile_to_update.purchased_modules = purchased
    profile_to_update.save()
    print(f"    - 更新後的模組已存入資料庫: {profile_to_update.purchased_modules}")

    redirect_url = reverse('profile')
    return JsonResponse({'status': 'success', 'message': '模擬購買成功！', 'redirect_url': redirect_url})
