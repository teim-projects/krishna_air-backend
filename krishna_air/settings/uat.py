from .base import *

DEBUG = False
ALLOWED_HOSTS = [
    "dsaqua.online",
    "www.dsaqua.online",
    "backend-uat",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://dsaqua.online",
    "https://www.dsaqua.online",
    "http://dsaqua.online",
]

CORS_ALLOW_ALL_ORIGINS = False