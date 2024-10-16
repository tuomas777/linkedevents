# Generated by Django 3.2.23 on 2023-12-22 08:13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_default_price_groups(apps, schema_editor):
    price_group_model = apps.get_model("registrations", "PriceGroup")

    default_price_groups = []

    for price_group_kwargs in [
        {
            "description_en": "Adult",
            "description_fi": "Aikuinen",
            "description_sv": "Vuxen",
        },
        {
            "description_en": "Child (7-17 years)",
            "description_fi": "Lapsi (7-17 vuotta)",
            "description_sv": "Barn (7-17 år)",
        },
        {
            "description_en": "Child (under 7 years)",
            "description_fi": "Lapsi (alle 7 vuotta)",
            "description_sv": "Barn (under 7 år)",
            "is_free": True,
        },
        {
            "description_en": "Student",
            "description_fi": "Opiskelija",
            "description_sv": "Studerande",
        },
        {
            "description_en": "Pensioner",
            "description_fi": "Eläkeläinen",
            "description_sv": "Pensionär",
        },
        {
            "description_en": "War veteran or member of Lotta Svärd",
            "description_fi": "Sotaveteraani tai lotta",
            "description_sv": "Krigsveteranen eller medlem av Lotta Svärd",
            "is_free": True,
        },
        {
            "description_en": "Conscript or subject to civil service",
            "description_fi": "Ase- tai siviilipalvelusvelvollinen",
            "description_sv": "Beväring eller civiltjänstgörare",
        },
        {
            "description_en": "Unemployed",
            "description_fi": "Työtön",
            "description_sv": "Arbetslös",
        },
    ]:
        default_price_groups.append(
            price_group_model(publisher=None, **price_group_kwargs)
        )

    price_group_model.objects.bulk_create(default_price_groups)


class Migration(migrations.Migration):
    dependencies = [
        ("django_orghierarchy", "0011_alter_datasource_user_editable_organizations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registrations", "0030_restore_phone_number_to_mandatory_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PriceGroup",
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
                ("description", models.CharField(max_length=255)),
                ("description_fi", models.CharField(max_length=255, null=True)),
                ("description_sv", models.CharField(max_length=255, null=True)),
                ("description_en", models.CharField(max_length=255, null=True)),
                ("description_zh_hans", models.CharField(max_length=255, null=True)),
                ("description_ru", models.CharField(max_length=255, null=True)),
                ("description_ar", models.CharField(max_length=255, null=True)),
                ("is_free", models.BooleanField(default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "last_modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_last_modified_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "publisher",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_price_groups",
                        to="django_orghierarchy.organization",
                        verbose_name="Publisher",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="RegistrationPriceGroup",
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
                ("price", models.DecimalField(decimal_places=4, max_digits=19)),
                (
                    "price_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registration_price_groups",
                        to="registrations.pricegroup",
                    ),
                ),
                (
                    "registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_price_groups",
                        to="registrations.registration",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SignUpPriceGroup",
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
                ("description", models.CharField(max_length=255)),
                ("description_fi", models.CharField(max_length=255, null=True)),
                ("description_sv", models.CharField(max_length=255, null=True)),
                ("description_en", models.CharField(max_length=255, null=True)),
                ("description_zh_hans", models.CharField(max_length=255, null=True)),
                ("description_ru", models.CharField(max_length=255, null=True)),
                ("description_ar", models.CharField(max_length=255, null=True)),
                ("price", models.DecimalField(decimal_places=4, max_digits=19)),
                (
                    "registration_price_group",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="signup_price_group",
                        to="registrations.registrationpricegroup",
                    ),
                ),
                (
                    "signup",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_group",
                        to="registrations.signup",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="registration",
            name="price_groups",
            field=models.ManyToManyField(
                blank=True,
                related_name="registrations",
                through="registrations.RegistrationPriceGroup",
                to="registrations.PriceGroup",
            ),
        ),
        migrations.AddConstraint(
            model_name="registrationpricegroup",
            constraint=models.UniqueConstraint(
                fields=("registration", "price_group"),
                name="unique_registration_price_group",
            ),
        ),
        migrations.RunPython(create_default_price_groups, migrations.RunPython.noop),
    ]
