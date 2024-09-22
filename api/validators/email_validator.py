from django.core.exceptions import ValidationError
from users.models import User


def validate_unique_email(value):
    if User.objects.filter(email=value).exists():
        raise ValidationError("An account with this email already exists.")
