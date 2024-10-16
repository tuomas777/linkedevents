# Generated by Django 3.2.23 on 2024-01-26 13:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registrations", "0034_registrationuseraccess_is_substitute_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="signupcontactperson",
            name="access_code",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=128,
                null=True,
                verbose_name="Access code",
            ),
        ),
        migrations.AddField(
            model_name="signupcontactperson",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contact_persons",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
