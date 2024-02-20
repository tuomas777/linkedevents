# Generated by Django 3.2.23 on 2024-01-30 08:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import registrations.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registrations", "0035_contact_person_access_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignUpPayment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "last_modified_time",
                    models.DateTimeField(auto_now=True, verbose_name="Modified at"),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=19)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("paid", "Paid"),
                            ("cancelled", "Cancelled"),
                            ("refunded", "Refunded"),
                            ("expired", "Expired"),
                        ],
                        default="created",
                        max_length=25,
                        verbose_name="Payment status",
                    ),
                ),
                (
                    "external_order_id",
                    models.CharField(
                        blank=True, default=None, max_length=64, null=True
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        blank=True, default=None, null=True, verbose_name="Expires at"
                    ),
                ),
                ("checkout_url", models.URLField(blank=True, default=None, null=True)),
                (
                    "logged_in_checkout_url",
                    models.URLField(blank=True, default=None, null=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="signuppayment_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "last_modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="signuppayment_last_modified_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "signup",
                    models.OneToOneField(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment",
                        to="registrations.signup",
                    ),
                ),
                (
                    "signup_group",
                    models.OneToOneField(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment",
                        to="registrations.signupgroup",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(registrations.models.SignUpOrGroupDependingMixin, models.Model),
        ),
    ]