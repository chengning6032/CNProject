# accounts/migrations/0005_create_superuser.py

from django.db import migrations
import os # 匯入 os 模組來讀取環境變數

def create_superuser(apps, schema_editor):
    # 取得 Django 內建的 User 模型
    User = apps.get_model('auth', 'User')

    # 從環境變數讀取管理員資訊，如果找不到就用預設值 (但線上環境一定要設定)
    DJANGO_SUPERUSER_USERNAME = os.environ.get('ADMIN_USER', 'admin')
    DJANGO_SUPERUSER_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'some_default_password')
    DJANGO_SUPERUSER_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

    # 檢查使用者是否已存在，不存在才建立
    if not User.objects.filter(username=DJANGO_SUPERUSER_USERNAME).exists():
        User.objects.create_superuser(
            username=DJANGO_SUPERUSER_USERNAME,
            password=DJANGO_SUPERUSER_PASSWORD,
            email=DJANGO_SUPERUSER_EMAIL
        )
        print(f"Superuser '{DJANGO_SUPERUSER_USERNAME}' created.")

class Migration(migrations.Migration):

    dependencies = [
        # 這個依賴關係很重要，確保 auth app 的資料表已經建立好了
        ('auth', '0012_alter_user_first_name_max_length'),
        ('accounts', '0004_alter_profile_purchased_modules'), # 這裡要改成你這個 app 的上一個遷移檔名
    ]

    operations = [
        # migrations.RunPython(create_superuser),
    ]