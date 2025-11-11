from pathlib import Path
import os
import dj_database_url
import pymysql

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-6hn#)n)vpg%*q6xm1eseq##u$*wu@z23u)428$=so28+ebts5q'
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['www.chinzhu.com.tw']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
    'SteelDesign',
    'EqStaticAnalysis_TW',
    'Wind_TW',
    'accounts',
    'products'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <--- 加在這裡
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CNProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'CNProject.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
pymysql.install_as_MySQLdb()
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',  # 將引擎改為 mysql
#         'NAME': 'cndb',  # 你的資料庫名稱 (例如: cn_project_db)
#         'USER': 'root',  # 你的 MySQL 使用者名稱 (例如: root)
#         'PASSWORD': 'root',  # 你的 MySQL 密碼
#         'HOST': '127.0.0.1',  # MySQL 主機 (通常是 localhost 或 127.0.0.1)
#         'PORT': '3306',  # MySQL 埠號 (預設是 3306)
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#         },
#     }
# }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'cndb',        # 你建立的資料庫名稱
#         'USER': 'root',      # 你建立的使用者名稱
#         'PASSWORD': 'root',       # 你設定的密碼
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }
DATABASES = {
    'default': dj_database_url.config(
        # 如果 Render 提供了 DATABASE_URL，就用它
        conn_max_age=600,
        # 如果沒有，就用我們本地的設定作為備用
        default='postgres://root:root@localhost:5432/cndb'
    )
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'zh-hant'

TIME_ZONE = 'Asia/Taipei'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_URL = '/static/'
if not DEBUG:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Backend Configuration (for development)
# This will print emails to the console instead of sending them.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'chengning6032@gmail.com'  # 您的 Gmail 地址
EMAIL_HOST_PASSWORD = 'njih toze bufh ntme'  # 您的 16 位應用程式密碼
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

ADMIN_EMAIL = 'chengning6032@gmail.com'
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
