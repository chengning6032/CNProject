# accounts/migrations/0006_check_superuser.py

from django.db import migrations
from django.contrib.auth import get_user_model
import os


def check_superuser(apps, schema_editor):
    User = get_user_model()

    # 讀取我們設定的管理員使用者名稱
    SUPERUSER_USERNAME = os.environ.get('ADMIN_USER', 'admin')

    print("\n--- Checking for superuser ---")  # 加上標記，方便在日誌中尋找

    try:
        # 嘗試尋找該使用者
        user = User.objects.get(username=SUPERUSER_USERNAME)

        print(f"SUCCESS: User '{user.username}' found in the database.")
        print(f"Is staff: {user.is_staff}")
        print(f"Is superuser: {user.is_superuser}")

    except User.DoesNotExist:
        # 如果找不到
        print(f"ERROR: User '{SUPERUSER_USERNAME}' was NOT found in the database!")

    except Exception as e:
        # 如果發生其他錯誤
        print(f"An unexpected error occurred: {e}")

    print("--- Check finished ---\n")


class Migration(migrations.Migration):
    dependencies = [
        # 這裡很重要，它的依賴是我們上一個建立 superuser 的遷移檔
        ('accounts', '0005_create_superuser'),
    ]

    operations = [
        migrations.RunPython(check_superuser),
    ]