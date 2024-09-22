from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models


class E2EEKey(models.Model):
    public_key = models.TextField()
    private_key = models.CharField(max_length=255, help_text='This will not be the actual private key\
                                    rather a reference to what private key was used for this public key.')
    created_at = models.DateTimeField(auto_now_add=True)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='api/images/profile_pictures/')
    bio = models.TextField(max_length=100)
    status = models.CharField(max_length=7, choices=[('online', 'Online'), ('offline', 'Offline')], default='offline')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not isinstance(self.user, User):
            raise ValidationError('User must be a user instance.')

        # Check if a profile picture is provided
        if self.profile_picture:
            # Reset file pointer to the beginning
            self.profile_picture.seek(0)

            # Check file size (limit: 5MB)
            if self.profile_picture.size > 5 * 1024 * 1024:
                raise ValidationError('File size should not exceed 5MB.')

            # Validate file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
            extension = self.profile_picture.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                raise ValidationError('Only images in JPEG, GIF, PNG formats are allowed.')

    def save(self, *args, **kwargs):
        self.clean()  # Call the clean method to perform validation
        super().save(*args, **kwargs)  # Call the real save() method

    def __str__(self):
        return self.user.username
    
    def get_profile_picture(self):
        if self.profile_picture and self.profile_picture.url:
            return self.profile_picture.url  # Return the URL if profile picture exists
        return '/static/temp.jpeg'  # Fallback to default image

