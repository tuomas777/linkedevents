# Generated by Django 4.2.13 on 2024-08-21 07:25

from decimal import Decimal, ROUND_HALF_UP
from django.db import migrations, models
from django.db.models import Q


def set_new_general_vat_and_recalculate_price_values(price_group):
    cents = Decimal(".01")

    price_group.vat_percentage = Decimal("25.50")

    price_group.price_without_vat = (
        price_group.price / (1 + price_group.vat_percentage / 100)
    ).quantize(cents, ROUND_HALF_UP)

    price_group.vat = (price_group.price - price_group.price_without_vat).quantize(
        cents, ROUND_HALF_UP
    )

    price_group.save(update_fields=["vat_percentage", "price_without_vat", "vat"])


def migrate_to_new_general_vat_percentage(apps, schema_editor):
    common_qs_filter = Q(vat_percentage=Decimal("24.00"))

    reg_price_group_model = apps.get_model("registrations", "RegistrationPriceGroup")
    for registration_price_group in reg_price_group_model.objects.filter(
        common_qs_filter
    ):
        set_new_general_vat_and_recalculate_price_values(registration_price_group)

    offer_price_group_model = apps.get_model("registrations", "OfferPriceGroup")
    for offer_price_group in offer_price_group_model.objects.filter(common_qs_filter):
        set_new_general_vat_and_recalculate_price_values(offer_price_group)

    signup_price_group_model = apps.get_model("registrations", "SignupPriceGroup")
    for signup_price_group in signup_price_group_model.objects.filter(common_qs_filter):
        set_new_general_vat_and_recalculate_price_values(signup_price_group)


class Migration(migrations.Migration):

    dependencies = [
        (
            "registrations",
            "0053_alter_registration_remaining_attendee_capacity_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_new_general_vat_percentage, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="offerpricegroup",
            name="vat_percentage",
            field=models.DecimalField(
                choices=[
                    (Decimal("25.50"), "25.5 %"),
                    (Decimal("14.00"), "14 %"),
                    (Decimal("10.00"), "10 %"),
                    (Decimal("0.00"), "0 %"),
                ],
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=4,
            ),
        ),
        migrations.AlterField(
            model_name="registrationpricegroup",
            name="vat_percentage",
            field=models.DecimalField(
                choices=[
                    (Decimal("25.50"), "25.5 %"),
                    (Decimal("14.00"), "14 %"),
                    (Decimal("10.00"), "10 %"),
                    (Decimal("0.00"), "0 %"),
                ],
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=4,
            ),
        ),
        migrations.AlterField(
            model_name="registrationwebstoreproductmapping",
            name="vat_code",
            field=models.CharField(
                choices=[
                    ("47", "25.5 %"),
                    ("45", "14 %"),
                    ("46", "10 %"),
                    ("4U", "0 %"),
                ],
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="signuppricegroup",
            name="vat_percentage",
            field=models.DecimalField(
                choices=[
                    (Decimal("25.50"), "25.5 %"),
                    (Decimal("14.00"), "14 %"),
                    (Decimal("10.00"), "10 %"),
                    (Decimal("0.00"), "0 %"),
                ],
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=4,
            ),
        ),
    ]