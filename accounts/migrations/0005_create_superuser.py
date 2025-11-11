# accounts/migrations/0005_create_superuser.py

from django.db import migrations
import os
from django.contrib.auth import get_user_model # <-- 引入 get_user_model


def create_superuser(apps, schema_editor):
    # 使用 get_user_model() 來取得活躍的使用者模型，這比 apps.get_model('auth', 'User') 更可靠
    User = get_user_model()

    DJANGO_SUPERUSER_USERNAME = os.environ.get('ADMIN_USER', 'admin')
    DJANGO_SUPERUSER_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'defaultpassword')
    DJANGO_SUPERUSER_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

    if not User.objects.filter(username=DJANGO_SUPERUSER_USERNAME).exists():
        # 改用 create_user，並手動設定 is_staff 和 is_superuser
        user = User.objects.create_user(
            username=DJANGO_SUPERUSER_USERNAME,
            password=DJANGO_SUPERUSER_PASSWORD,
            email=DJANGO_SUPERUSER_EMAIL,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()  # <-- 儲存變更
        print(f"Superuser '{DJANGO_SUPERUSER_USERNAME}' created with staff and superuser status.")

class Migration(migrations.Migration):

    dependencies = [
        # 這個依賴關係很重要，確保 auth app 的資料表已經建立好了
        ('auth', '0012_alter_user_first_name_max_length'),
        ('accounts', '0004_alter_profile_purchased_modules'), # 這裡要改成你這個 app 的上一個遷移檔名
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]