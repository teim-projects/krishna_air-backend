from .base import *

DEBUG = False
ALLOWED_HOSTS = [
    "krisnahvac.in",
    "www.krisnahvac.in",
    "backend-uat",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://krisnahvac.in",
    "https://www.krisnahvac.in",
    "http://krisnahvac.in",
]

CORS_ALLOWED_ORIGINS = [
    "https://krisnahvac.in",
    "https://www.krisnahvac.in",
]

CORS_ALLOW_ALL_ORIGINS = False