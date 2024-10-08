# Generated by Django 5.1.1 on 2024-09-09 15:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0005_message_is_deleted'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='message',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='chats.message'),
        ),
    ]
