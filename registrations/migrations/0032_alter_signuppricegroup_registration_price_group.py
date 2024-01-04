# Generated by Django 3.2.23 on 2024-01-04 08:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registrations", "0031_registration_price_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signuppricegroup",
            name="registration_price_group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="signup_price_groups",
                to="registrations.registrationpricegroup",
            ),
        ),
        migrations.AlterField(
            model_name="registrationpricegroup",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=19),
        ),
        migrations.AlterField(
            model_name="signuppricegroup",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=19),
        ),
    ]
