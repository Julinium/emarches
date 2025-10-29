import os, django.conf.locale
from pathlib import Path
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

SECRET_KEY = os.getenv("SECRET_KEY")
# DEBUG = ENVIRONMENT != 'production'
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', '0.0.0.0', os.getenv("DOMAIN_NAME"), os.getenv("IP_ADDRESS")]

# CSRF_TRUSTED_ORIGINS = [
#     # f"http://{ os.getenv("IP_ADDRESS") }",
#     'http://94.72.98.224',

#     "http://emarches.com",
#     "http://localhost:8000",  # for dev
#     "http://127.0.0.1:8000",
# ]

# SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SECURE = False


SITE_ID = 1

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'emarches',
    'base',
    'authy',
    'nas',
    'portal',

    # 'private_storage',
    'django_cleanup',
    'debug_toolbar',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.openid_connect',
    'allauth.socialaccount.providers.telegram',
    # 'allauth.socialaccount.providers.apple',
    # 'allauth.socialaccount.providers.facebook',
    # 'allauth.socialaccount.providers.github',
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
    'django.middleware.locale.LocaleMiddleware',

    'allauth.account.middleware.AccountMiddleware',

    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'emarches.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "templates",
        ],
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

if ENVIRONMENT == 'production':
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'HOST':     os.getenv("DB_HOST"),
            'PORT':     os.getenv("DB_PORT"),
            'NAME':     os.getenv("DB_NAME"),
            'USER':     os.getenv("DB_USER"),
            'PASSWORD': os.getenv("DB_PASS"),
        }
    }

    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = True
    EMAIL_HOST          = os.getenv("EMAIL_HOST")
    EMAIL_PORT          = os.getenv("EMAIL_PORT")
    EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    DEFAULT_FROM_EMAIL  = os.getenv("DEFAULT_FROM_EMAIL")

    AUTH_PASSWORD_VALIDATORS = [
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
        {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
        {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
    ]
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    AUTH_PASSWORD_VALIDATORS = []

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# AUTH_PASSWORD_VALIDATORS = [
#     {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
# ]


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
    ("fr", _("French")),
    ("ar", _("Arabic")),
    ("zg", _("Amazigh")),
    ("es", _("Spanish")),
    ("de", _("German")),
    ]

LOCALE_PATHS = [BASE_DIR / "locale", ]
USE_THOUSAND_SEPARATOR = True


STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# PRIVATE_STORAGE_ROOT = BASE_DIR / 'media/private'
# PRIVATE_STORAGE_AUTH_FUNCTION = 'private_storage.permissions.allow_authenticated'
# PRIVATE_STORAGE_AUTH_FUNCTION = 'nas.permissions.allow_profile_owner'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]


SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": os.getenv("ALLAUTH_GOOGLE_CLIENT_ID"),
                "secret": os.getenv("ALLAUTH_GOOGLE_SECRET"),
            },
        ],
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "VERIFIED_EMAIL": True,
        'EMAIL_AUTHENTICATION': True
    },

    # "apple": {
    #     "APPS": [
    #         {
    #             "client_id": os.getenv("ALLAUTH_APPLE_CLIENT_ID"),
    #             "secret": os.getenv("ALLAUTH_APPLE_SECRET"),
    #         },
    #     ],
    #     "SCOPE": [
    #         "profile",
    #         "email",
    #     ],
    #     "AUTH_PARAMS": {
    #         "access_type": "online",
    #     },
    #     "VERIFIED_EMAIL": True,
    #     'EMAIL_AUTHENTICATION': True
    # },

    'telegram': {
        'APP': {
                "client_id": os.getenv("ALLAUTH_TELEGRAM_ID"),
                "secret": os.getenv("ALLAUTH_TELEGRAM_KEY"),
        },
    },

    'openid_connect': {
        'APPS': [
            {
                'provider_id': 'linkedin',  # This is the OIDC issuer identifier for LinkedIn
                'name': 'LinkedIn',
                'client_id': os.getenv("ALLAUTH_LINKEDIN_CLIENT_ID"),  # From Step 1
                'secret': os.getenv("ALLAUTH_LINKEDIN_SECRET"),  # From Step 1
                'settings': {
                    'server_url': 'https://www.linkedin.com/oauth',
                },
            },
        ],
    },
}

LOGIN_REDIRECT_URL = 'nas_profile_view'
LOGOUT_REDIRECT_URL = 'account_login'

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

ACCOUNT_ADAPTER = "authy.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "authy.adapters.SocialAccountAdapter"
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # Requires email verification before login
ACCOUNT_LOGIN_METHODS = {'email', 'username'}




MESSAGE_TAGS = {
        messages.DEBUG: 'secondary',
        messages.ERROR: 'danger',
 }

env_scraper_path = BASE_DIR / 'scraper/.env'
load_dotenv(dotenv_path=env_scraper_path)
DCE_MEDIA_ROOT = os.getenv("MEDIA_ROOT")


TENDER_FULL_PROGRESS_DAYS = 30
TENDERS_ITEMS_PER_PAGE = 10


INTERNAL_IPS = [
    '127.0.0.1',
]