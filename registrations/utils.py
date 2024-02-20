from decimal import Decimal

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.utils import translation
from icalendar import Calendar
from icalendar import Event as CalendarEvent
from icalendar import vText


def code_validity_duration(seats):
    return settings.SEAT_RESERVATION_DURATION + seats


def get_language_pk_or_default(language, supported_languages):
    if language is not None and language.pk in supported_languages:
        return language.pk
    else:
        return "fi"


def get_ui_locales(language):
    linked_events_ui_locale = get_language_pk_or_default(language, ["fi", "en"])
    linked_registrations_ui_locale = get_language_pk_or_default(
        language, ["fi", "sv", "en"]
    )

    return [linked_events_ui_locale, linked_registrations_ui_locale]


def get_signup_create_url(registration, language):
    return (
        f"{settings.LINKED_REGISTRATIONS_UI_URL}/{language}/"
        f"registration/{registration.id}/signup-group/create"
    )


def get_signup_edit_url(
    contact_person, linked_registrations_ui_locale, access_code=None
):
    signup_edit_url = (
        f"{settings.LINKED_REGISTRATIONS_UI_URL}/{linked_registrations_ui_locale}/"
        f"registration/{contact_person.registration.id}/"
    )

    if contact_person.signup_group_id:
        signup_edit_url += f"signup-group/{contact_person.signup_group_id}/edit"
    else:
        signup_edit_url += f"signup/{contact_person.signup_id}/edit"

    if access_code:
        signup_edit_url += f"?access_code={access_code}"

    return signup_edit_url


def send_mass_html_mail(
    datatuple,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
):
    """
    django.core.mail.send_mass_mail doesn't support sending html mails.
    """
    num_messages = 0

    for subject, message, html_message, from_email, recipient_list in datatuple:
        num_messages += send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=fail_silently,
            auth_user=auth_user,
            auth_password=auth_password,
            connection=connection,
            html_message=html_message,
        )

    return num_messages


def get_email_noreply_address():
    return (
        settings.DEFAULT_FROM_EMAIL or "noreply@%s" % Site.objects.get_current().domain
    )


def has_allowed_substitute_user_email_domain(email_address):
    return email_address and any(
        [
            email_address.endswith(domain)
            for domain in settings.SUBSTITUTE_USER_ALLOWED_EMAIL_DOMAINS
        ]
    )


def create_event_ics_file_content(event, language="fi"):
    cal = Calendar()
    # Some properties are required to be compliant
    cal.add("prodid", "-//linkedevents.hel.fi//NONSGML API//EN")
    cal.add("version", "2.0")

    with translation.override(language):
        calendar_event = CalendarEvent()

        if (start_time := event.start_time) and (name := event.name):
            calendar_event.add("dtstart", start_time)
            calendar_event.add("summary", name)
        else:
            raise ValueError(
                "Event doesn't have start_time or name. Ics file cannot be created."
            )

        calendar_event.add("dtend", event.end_time if event.end_time else start_time)

        if description := event.short_description:
            calendar_event.add("description", description)
        if location := event.location:
            location_parts = [
                location.name,
                location.street_address,
                location.address_locality,
            ]
            location_text = ", ".join([i for i in location_parts if i])
            calendar_event["location"] = vText(location_text)

        cal.add_component(calendar_event)

    filename = f"event_{event.id}.ics"

    return filename, cal.to_ical()


def strip_trailing_zeroes_from_decimal(value: Decimal):
    if value == value.to_integral():
        return value.quantize(Decimal(1))

    return value.normalize()
