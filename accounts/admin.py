from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile
import json
from django.utils.html import format_html
from datetime import datetime  # 【核心新增】匯入 datetime 模組


# 1. 定義 Profile 的 Inline 管理器
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = '使用者資料與權限'

    # 【核心修改】將欄位重新排序和分組
    fieldsets = (
        ('基本聯絡資訊', {
            'fields': ('phone_number', 'elementary_school')
        }),
        ('模組權限管理 (進階)', {
            'classes': ('collapse',),  # 預設折疊，防止誤操作
            'fields': ('purchased_modules',),
            'description': format_html(
                """
                <div style="margin-top:10px; padding:10px; background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:4px;">
                    <h4 style="margin:0 0 10px 0;">JSON 格式說明：</h4>
                    <p>請嚴格遵循以下 JSON 字典格式進行修改。錯誤的格式將導致系統無法解析。</p>
                    <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 12px; background-color: #fff; padding: 10px; border-radius: 4px;">{{
    "product_id": {{
        "name": "商品完整名稱",
        "plan": "monthly",
        "purchase_date": "YYYY-MM-DDTHH:MM:SS.ffffff+00:00",
        "expiration_date": "YYYY-MM-DDTHH:MM:SS.ffffff+00:00"
    }}
}}</pre>
                    <p><strong>product_id:</strong> 必須與 `products` 應用中的商品 ID 一致 (例如: "base-plate")。</p>
                    <p><strong>plan:</strong> 必須是 "monthly", "semi_annually", 或 "annually"。</p>
                    <p><strong>日期:</strong> 請使用標準 ISO 格式。</p>
                    <p><strong>刪除權限:</strong> 將整個 JSON 內容清空為 <code>{{}}</code> 即可。</p>
                </div>
                """
            )
        }),
    )

    # 顯示格式化後的購買記錄，作為快速預覽
    readonly_fields = ('purchased_modules_formatted_display',)

    # 將格式化後的預覽放在最前面
    def get_fields(self, request, obj=None):
        return ('phone_number', 'elementary_school', 'purchased_modules_formatted_display')

    # 【核心修改】提供一個新的、只用於顯示的欄位
    @admin.display(description="已購買模組 (預覽)")
    def purchased_modules_formatted_display(self, instance):
        """將 JSON 數據格式化為更易讀的 HTML 顯示在後台"""
        modules = instance.purchased_modules
        if not modules or not isinstance(modules, dict):
            return "無購買記錄"

        html_str = '<ul style="margin:0; padding-left:20px;">'
        for module_id, data in modules.items():
            name = data.get('name', 'N/A')
            plan = data.get('plan', 'N/A')
            exp_date_str = data.get('expiration_date', 'N/A')

            # 【核心修正】更穩固的日期解析邏輯
            try:
                # 處理可能帶有 'Z' 或 '+00:00' 的 ISO 格式
                exp_date = datetime.fromisoformat(exp_date_str.replace('Z', '+00:00'))
                exp_date_formatted = exp_date.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                exp_date_formatted = "<b style='color:red;'>日期格式錯誤</b>"

            html_str += f"<li><b>{name}</b> ({plan}) - 到期日: {exp_date_formatted}</li>"
        html_str += "</ul>"
        return format_html(html_str)


# 2. 重新定義 User 的 Admin 管理器 (保持不變)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'has_purchases')

    @admin.display(description="有購買記錄", boolean=True)
    def has_purchases(self, obj):
        if hasattr(obj, 'profile'):
            return bool(obj.profile.purchased_modules)
        return False


# 3. 重新註冊 User 模型 (保持不變)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)