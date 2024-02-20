# Generated by Django 3.2.23 on 2024-02-13 08:03
from datetime import timedelta
from typing import Optional

from django.db import migrations, models, transaction
from django.db.models import ExpressionWrapper, F, DateTimeField, Sum
from django.utils.timezone import localtime

from registrations.models import SignUp
from registrations.utils import code_validity_duration


def current_attendee_count(registration) -> int:
    return registration.signups.filter(
        attendee_status=SignUp.AttendeeStatus.ATTENDING
    ).count()


def current_waiting_list_count(registration) -> int:
    return registration.signups.filter(
        attendee_status=SignUp.AttendeeStatus.WAITING_LIST
    ).count()


def reserved_seats_amount(registration) -> int:
    return (
        # Calculate expiration time for each reservation
        registration.reservations.annotate(
            expiration=ExpressionWrapper(
                F("timestamp")
                + timedelta(minutes=1) * code_validity_duration(F("seats")),
                output_field=DateTimeField(),
            )
        )
        # Filter to get all not expired reservations
        .filter(expiration__gte=localtime())
        # Sum  seats of not expired reservation
        .aggregate(seats_sum=Sum("seats", output_field=models.IntegerField()))[
            "seats_sum"
        ]
        or 0
    )


def calculate_remaining_attendee_capacity(registration) -> Optional[int]:
    maximum_attendee_capacity = registration.maximum_attendee_capacity

    if maximum_attendee_capacity is None:
        return None

    attendee_count = current_attendee_count(registration)
    reserved_seats_count = reserved_seats_amount(registration)

    return max(maximum_attendee_capacity - attendee_count - reserved_seats_count, 0)


def calculate_remaining_waiting_list_capacity(registration) -> Optional[int]:
    waiting_list_capacity = registration.waiting_list_capacity

    if waiting_list_capacity is None:
        return None

    maximum_attendee_capacity = registration.maximum_attendee_capacity
    reserved_seats_count = reserved_seats_amount(registration)

    if maximum_attendee_capacity is not None:
        # Calculate the amount of reserved seats that are used for actual seats
        # and reduce it from reserved_seats_amount to get amount of reserved seats
        # in the waiting list
        attendee_count = current_attendee_count(registration)
        reserved_seats_count = max(
            reserved_seats_count - max(maximum_attendee_capacity - attendee_count, 0),
            0,
        )

    waiting_list_count = current_waiting_list_count(registration)

    return max(waiting_list_capacity - waiting_list_count - reserved_seats_count, 0)


def calculate_and_set_current_capacities(apps, schema_editor):
    registration_model = apps.get_model("registrations", "Registration")

    registrations = registration_model.objects.select_for_update().all()
    with transaction.atomic():
        for registration in registrations:
            registration.remaining_attendee_capacity = (
                calculate_remaining_attendee_capacity(registration)
            )
            registration.remaining_waiting_list_capacity = (
                calculate_remaining_waiting_list_capacity(registration)
            )
            registration.save(
                update_fields=[
                    "remaining_attendee_capacity",
                    "remaining_waiting_list_capacity",
                ]
            )


class Migration(migrations.Migration):
    dependencies = [
        ("registrations", "0036_signuppayment"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="remaining_attendee_capacity",
            field=models.PositiveSmallIntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="registration",
            name="remaining_waiting_list_capacity",
            field=models.PositiveSmallIntegerField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(
            calculate_and_set_current_capacities, migrations.RunPython.noop
        ),
    ]
