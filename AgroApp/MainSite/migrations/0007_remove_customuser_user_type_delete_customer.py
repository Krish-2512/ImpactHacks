# Generated by Django 5.1.6 on 2025-03-05 01:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0006_customuser_user_type_customer'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='user_type',
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
    ]
