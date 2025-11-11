# products/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from accounts.models import Profile
from .models import Product


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
