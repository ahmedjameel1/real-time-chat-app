# Generated by Django 5.1.1 on 2024-09-11 01:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0013_rename_type_notification_action'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notification',
            name='message',
        ),
        migrations.AddField(
            model_name='notification',
            name='content_type',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='notification',
            name='object_id',
            field=models.PositiveIntegerField(default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='notification',
            name='action',
            field=models.CharField(choices=[('new_message', 'sent new message'), ('reaction', 'reacted to message'), ('user_joined_group', 'joined chat'), ('user_left_group', 'left chat'), ('notifications_update', 'notifications update')], max_length=50),
        ),
    ]
