# Generated by Django 5.1.1 on 2024-09-11 00:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0012_alter_notification_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='type',
            new_name='action',
        ),
    ]
