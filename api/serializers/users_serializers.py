from rest_framework import serializers
from users import models as usermodels
from django.core.validators import EmailValidator
from django.contrib.auth.password_validation import validate_password
from api.validators.email_validator import validate_unique_email
from django.db import transaction
import base64
from django.core.files.base import ContentFile

class UserSerializer(serializers.ModelSerializer):
    """
    Serializers for the User model.

    The `UserSerializer` class provides serialization and deserialization functionality for the User model. It includes the following fields:

    - `profile_picture`: An optional ImageField that represents the user's profile picture.
    - `bio`: An optional CharField that represents the user's bio.
    - `email`: An optional EmailField that represents the user's email address. It is validated for uniqueness.
    - `first_name`: An optional CharField that represents the user's first name.
    - `last_name`: An optional CharField that represents the user's last name.
    - `password`: A write-only CharField that represents the user's password. It is validated using the `validate_password` function.

    The serializer's behavior changes depending on the HTTP method used:

    - For POST requests, the `email`, `first_name`, `last_name`, and `password` fields are required.
    - For PUT and PATCH requests, the `password` field is not required, and the `bio`, `first_name`, `last_name`, `email`, and `username` fields are also not required.

    The `create` and `update` methods handle the creation and updating of the User and Profile models, respectively.

    The `to_internal_value` method is overridden to handle the conversion of base64-encoded profile picture data to a Django `ContentFile` object.
    """
    profile_picture = serializers.ImageField(source='profile.profile_picture', required=False, use_url=True, max_length=None)
    bio = serializers.CharField(source='profile.bio', max_length=100, required=False)
    email = serializers.EmailField(validators=[EmailValidator(), validate_unique_email], required=False)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context['request'].method == 'POST':
            self.fields['email'].required = True
            self.fields['first_name'].required = True
            self.fields['last_name'].required = True
            self.fields['password'].required = True
        elif self.context['request'].method in ['PUT', 'PATCH']:
            self.fields['password'].required = False
            self.fields['bio'].required = False
            self.fields['first_name'].required = False
            self.fields['last_name'].required = False
            self.fields['email'].required = False
            self.fields['username'].required = False

    class Meta:
        model = usermodels.User
        fields = ['id', 'first_name', 'last_name',
                  'username', 'email', 'profile_picture',
                  'bio', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        with transaction.atomic():
            profile_data = validated_data.pop('profile', None)
            password = validated_data.pop('password', None)
            user = usermodels.User.objects.create(**validated_data)
            user.set_password(password)
            user.save()
            profile, created = usermodels.Profile.objects.get_or_create(user=user)
            # Update the profile if profile_data is provided
            if profile_data:
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
            return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        # Update user fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)

        if password:
            instance.set_password(password)

        instance.save()

        # Ensure profile exists
        profile, created = usermodels.Profile.objects.get_or_create(user=instance)
        
        # Update profile fields
        profile.profile_picture = profile_data.get('profile_picture', profile.profile_picture)
        profile.bio = profile_data.get('bio', profile.bio)
        profile.save()

        return instance

    
    def to_internal_value(self, data):
        from django.core.files import File
        if 'profile_picture' in data:
            if isinstance(data['profile_picture'], str) and data['profile_picture']:
                if ';base64,' in data['profile_picture']:
                    format, imgstr = data['profile_picture'].split(';base64,') 
                    ext = format.split('/')[-1]
                    data['profile_picture'] = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                else:
                    raise serializers.ValidationError({"profile_picture": "Invalid image format. Must be base64 encoded."})
            elif not isinstance(data['profile_picture'], File):
                raise serializers.ValidationError({"profile_picture": "Invalid image format. Must be a file or base64 encoded string."})
        
        return super().to_internal_value(data)


class E2EEKeySerializer(serializers.Serializer):
    class Meta:
        model = usermodels.E2EEKey
        fields = ['public_key', 'private_key', 'created_at']