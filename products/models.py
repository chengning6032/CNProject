from django.db import models

class Product(models.Model):
    # 商品的唯一識別 ID，例如 "steel_bp_anchor"
    product_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=100, verbose_name="商品名稱")
    description = models.TextField(verbose_name="商品描述")

    # 我們將價格儲存為整數（以分為單位，避免浮點數誤差），或者直接用 DecimalField
    # 這裡為了簡單起見，我們先儲存不同方案的價格字典
    # 結構: {"monthly": 400, "semi-annually": 2150, "annually": 3850}
    prices = models.JSONField(default=dict, verbose_name="價格方案 (NT$)")

    def __str__(self):
        return self.name