# accounts/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    # 建立与 User 模型的一对一关联
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    purchased_modules = models.JSONField(default=dict, blank=True)

    # 定义会员等级的选项
    MEMBER_CHOICES = (
        ('general', '一般會員'),
        ('paid', '付費會員'),
    )
    membership_type = models.CharField(
        max_length=10,
        choices=MEMBER_CHOICES,
        default='general'
    )

    def __str__(self):
        return self.user.username

    purchased_apps = models.TextField(blank=True, null=True, help_text="以逗號分隔的已購買 APP 名稱")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="聯絡電話")
    elementary_school = models.CharField(max_length=100, blank=True, null=True, verbose_name="畢業國小")

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()