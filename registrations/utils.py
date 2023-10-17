from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, get_connection


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


def get_signup_edit_url(signup, linked_registrations_ui_locale):
    signup_edit_url = (
        f"{settings.LINKED_REGISTRATIONS_UI_URL}/{linked_registrations_ui_locale}"
        f"/registration/{signup.registration_id}/"
    )
    if signup.signup_group_id:
        signup_edit_url += f"signup-group/{signup.signup_group_id}/edit"
    else:
        signup_edit_url += f"signup/{signup.id}/edit"
    return signup_edit_url


def get_signup_confirmation_template(signup):
    if signup.signup_group_id:
        return "signup_group_confirmation.html"
    else:
        return "signup_confirmation.html"


def get_signup_confirmation_to_waiting_list_template(signup):
    if signup.signup_group_id:
        return "signup_group_confirmation_to_waiting_list.html"
    else:
        return "signup_confirmation_to_waiting_list.html"


def send_mass_html_mail(
    datatuple,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
):
    """
    django.core.mail.send_mass_mail doesn't support sending html mails,

    This method duplicates send_mass_mail except requires html_message for each message
    and adds html alternative to each mail
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    messages = []
    for subject, message, html_message, from_email, recipient_list in datatuple:
        mail = EmailMultiAlternatives(
            subject, message, from_email, recipient_list, connection=connection
        )
        mail.attach_alternative(html_message, "text/html")
        messages.append(mail)

    return connection.send_messages(messages)


def get_email_noreply_address():
    return (
        settings.DEFAULT_FROM_EMAIL or "noreply@%s" % Site.objects.get_current().domain
    )
