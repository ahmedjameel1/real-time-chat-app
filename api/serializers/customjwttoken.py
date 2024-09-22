import logging
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer for obtaining JWT token pairs using email instead of username.

    This serializer overrides the default `TokenObtainPairSerializer` from the
    `rest_framework_simplejwt` library to allow users to authenticate using their
    email address instead of a username.

    The serializer performs the following steps:
    1. Retrieves the email and password from the request data.
    2. Attempts to find the user with the provided email.
    3. Checks if the provided password matches the user's password.
    4. Checks if the user is active.
    5. If all checks pass, generates and returns the access and refresh tokens.

    Raises:
        serializers.ValidationError: If the email or password is invalid, or the
            user is inactive.
    """
    username_field = 'email'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token

    def validate(self, attrs):
        data = {}
        email = attrs.get('email')
        password = attrs.get('password')

        UserModel = get_user_model()

        try:
            user = UserModel.objects.get(email=email)
            print(f"Found user: {user}")
        except UserModel.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password.')

        if not user.check_password(password):
            raise serializers.ValidationError('Invalid email or password.')

        # Check if the user is active
        if not user.is_active:
            raise serializers.ValidationError('This account is inactive.')
        
        data['access'] = str(self.get_token(user).access_token)
        data['refresh'] = str(self.get_token(user))

        return data

