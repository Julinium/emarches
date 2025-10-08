# import os
# from pathlib import Path
# from dotenv import load_dotenv
import os, django.conf.locale
from pathlib import Path
# from django.conf import global_settings
# from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = ['127.0.0.1', '0.0.0.0', '94.72.98.224']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'emarches',
    'base',

    'allauth',
    'allauth.account',

    # 'allauth.socialaccount.providers.apple',
    # 'allauth.socialaccount.providers.discord',
    # 'allauth.socialaccount.providers.facebook',
    # 'allauth.socialaccount.providers.github',
    # 'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.linkedin',
    # 'allauth.socialaccount.providers.microsoft',
    # 'allauth.socialaccount.providers.telegram',
    # 'allauth.socialaccount.providers.twitter',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'emarches.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'emarches.wsgi.application'


DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # }
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'HOST':     os.getenv("DB_HOST"),
        'PORT':     os.getenv("DB_PORT"),
        'NAME':     os.getenv("DB_NAME"),
        'USER':     os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASS"),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Add support for non-standardized language
EXTRA_LANG_INFO = {
    'zg': {
        'bidi': False, # right-to-left ?
        'code': 'zg',
        'name': 'Tamazight',
        'name_local': 'ⵜⴰⵎⴰⵣⵉⵖⵜ', #unicode codepoints
    },
}

LANG_INFO = {**django.conf.locale.LANG_INFO, **EXTRA_LANG_INFO}
django.conf.locale.LANG_INFO = LANG_INFO

LANGUAGES = [
    ("en", _("English")),
    ("zg", _("Amazigh")),
    ("ar", _("Arabic")),
    ("fr", _("French")),
    ("es", _("Spanish")),
    ("de", _("German")),
    ]

LOCALE_PATHS = [BASE_DIR / "locale", ]
USE_THOUSAND_SEPARATOR = True




STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

env_scraper_path = BASE_DIR / 'scraper/.env'
load_dotenv(dotenv_path=env_scraper_path)

MEDIA_ROOT = os.getenv("MEDIA_ROOT")


# Email backend parameters
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_SSL = False
EMAIL_USE_TLS = True
EMAIL_HOST          = os.getenv("EMAIL_HOST")
EMAIL_PORT          = os.getenv("EMAIL_PORT")
EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL  = os.getenv("DEFAULT_FROM_EMAIL")

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
