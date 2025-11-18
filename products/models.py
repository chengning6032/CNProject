from django.db import models
from django.contrib.auth.models import User


# 【核心新增】建立 Order 模型，用來記錄每一筆訂單
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    merchant_trade_no = models.CharField(max_length=50, unique=True, verbose_name="綠界訂單號")
    total_amount = models.IntegerField(verbose_name="總金額")
    items = models.JSONField(verbose_name="商品項目")
    is_paid = models.BooleanField(default=False, verbose_name="是否已付款")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="付款時間")

    def __str__(self):
        return f"訂單 {self.merchant_trade_no} by {self.user.username}"

class Product(models.Model):
    # 商品的唯一識別 ID，例如 "steel_bp_anchor"
    product_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=100, verbose_name="商品名稱")
    description = models.TextField(verbose_name="商品描述")

    # 我們將價格儲存為整數（以分為單位，避免浮點數誤差），或者直接用 DecimalField
    # 這裡為了簡單起見，我們先儲存不同方案的價格字典
    # 結構: {"monthly": 400, "semiannually": 2150, "annually": 3850}
    prices = models.JSONField(default=dict, verbose_name="價格方案 (NT$)")

    def __str__(self):
        return self.name