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
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

from accounts.models import Profile
from .models import Product, Order

# 從我們手動建立的 sdk 資料夾中引用 SDK
from sdk.ecpay_payment_sdk import ECPayPaymentSdk


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
@login_required
@require_POST
def ecpay_checkout_view(request):
    try:
        data = json.loads(request.body)
        cart_items = data.get('items', [])
        if not cart_items:
            return JsonResponse({'status': 'error', 'message': '購物車是空的'}, status=400)

        total_amount = 0
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
            total_amount += int(price)

        merchant_trade_no = f"OLI{int(time.time())}"
        Order.objects.create(
            user=request.user,
            merchant_trade_no=merchant_trade_no,
            total_amount=total_amount,
            items=cart_items
        )

        # 準備要傳送給綠界的基礎參數字典
        # 【核心修正】我們將完全遵從 SDK 內部的參數檢查機制
        order_params = {
            'MerchantTradeNo': merchant_trade_no,
            'MerchantTradeDate': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'PaymentType': 'aio',
            'TotalAmount': total_amount,
            'TradeDesc': "OLI 工程設計模組訂閱",
            'ItemName': '#'.join(item_names),
            'ReturnURL': f"{settings.SITE_URL}{reverse('products:ecpay_return')}",
            'ChoosePayment': 'Credit',
            'EncryptType': 1,
            'OrderResultURL': f"{settings.SITE_URL}{reverse('products:ecpay_notify')}",
        }

        # 初始化 SDK
        sdk = ECPayPaymentSdk(
            MerchantID=settings.ECPAY_MERCHANT_ID,
            HashKey=settings.ECPAY_HASH_KEY,
            HashIV=settings.ECPAY_HASH_IV
        )

        # 產生綠界訂單所需參數
        # SDK 內部的 integrate_parameter 會自動加入 MerchantID 並產生 CheckMacValue
        final_order_params = sdk.create_order(order_params)

        # 產生 HTML 的 form 格式
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
def ecpay_return_view(request):
    return render(request, 'products/payment_success.html')


# 【核心新增】第三步：綠界伺服器在背景發送通知到此處，進行真正的訂單更新 (後景)
@csrf_exempt
@require_POST
def ecpay_notify_view(request):
    # 1. 從綠界 POST 回來的資料中，取得所有參數
    post_data = request.POST.dict()

    # 2. 【核心修正】手動進行 CheckMacValue 驗證
    # 2.1 從回傳資料中，先把官方的 CheckMacValue 取出並移除
    if 'CheckMacValue' not in post_data:
        return HttpResponse('Invalid request: CheckMacValue not found', status=400)

    received_mac_value = post_data.pop('CheckMacValue')

    # 2.2 初始化 SDK
    sdk = ECPayPaymentSdk(
        MerchantID=settings.ECPAY_MERCHANT_ID,
        HashKey=settings.ECPAY_HASH_KEY,
        HashIV=settings.ECPAY_HASH_IV
    )

    # 2.3 用剩下的資料，自己重新產生一次 CheckMacValue
    #     我們直接呼叫 SDK 中那個我們已經確認存在的 generate_check_value 函式
    generated_mac_value = sdk.generate_check_value(post_data)

    # 2.4 比對兩者是否相符
    if received_mac_value != generated_mac_value:
        # 如果不相符，代表這筆通知可能是偽造的，直接拒絕
        return HttpResponse('MAC verification failed', status=400)

    # 3. 處理訂單邏輯 (這部分和之前完全一樣)
    merchant_trade_no = post_data.get('MerchantTradeNo')
    rtn_code = post_data.get('RtnCode')

    if rtn_code == '1':
        try:
            order = Order.objects.get(merchant_trade_no=merchant_trade_no, is_paid=False)

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
                product = Product.objects.get(product_id=module_id)

                if plan == 'monthly':
                    delta = relativedelta(months=1)
                elif plan == 'semiannually':
                    delta = relativedelta(months=6)
                elif plan == 'annually':
                    delta = relativedelta(years=1)
                else:
                    continue

                new_expiration_date = today + delta

                purchased[module_id] = {
                    'name': product.name,
                    'plan': plan,
                    'purchase_date': today.isoformat(),
                    'expiration_date': new_expiration_date.isoformat(),
                }

            profile_to_update.purchased_modules = purchased
            profile_to_update.save()

            return HttpResponse('1|OK')

        except Order.DoesNotExist:
            return HttpResponse('Order not found', status=404)
        except Exception as e:
            print(f"Error processing notification for order {merchant_trade_no}: {e}")
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
            elif plan == 'semi_annually':
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
