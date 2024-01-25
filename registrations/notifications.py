from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from events.models import Event
from registrations.utils import get_signup_edit_url, get_ui_locales


class NotificationType:
    NO_NOTIFICATION = "none"
    SMS = "sms"
    EMAIL = "email"
    SMS_EMAIL = "sms and email"


NOTIFICATION_TYPES = (
    (NotificationType.NO_NOTIFICATION, _("No Notification")),
    (NotificationType.SMS, _("SMS")),
    (NotificationType.EMAIL, _("E-Mail")),
    (NotificationType.SMS_EMAIL, _("Both SMS and email.")),
)


class SignUpNotificationType:
    EVENT_CANCELLATION = "event_cancellation"
    CANCELLATION = "cancellation"
    CONFIRMATION = "confirmation"
    CONFIRMATION_TO_WAITING_LIST = "confirmation_to_waiting_list"
    TRANSFERRED_AS_PARTICIPANT = "transferred_as_participant"


signup_notification_subjects = {
    SignUpNotificationType.EVENT_CANCELLATION: _("Event cancelled - %(event_name)s"),
    SignUpNotificationType.CANCELLATION: _("Registration cancelled - %(event_name)s"),
    SignUpNotificationType.CONFIRMATION: _(
        "Registration confirmation - %(event_name)s"
    ),
    SignUpNotificationType.CONFIRMATION_TO_WAITING_LIST: _(
        "Waiting list seat reserved - %(event_name)s"
    ),
    SignUpNotificationType.TRANSFERRED_AS_PARTICIPANT: _(
        "Registration confirmation - %(event_name)s"
    ),
}


signup_email_texts = {
    SignUpNotificationType.EVENT_CANCELLATION: {
        "heading": _("Event %(event_name)s has been cancelled"),
        "text": _("Thank you for your interest in the event."),
    },
    SignUpNotificationType.CANCELLATION: {
        "heading": _("Registration cancelled"),
        "secondary_heading": {
            Event.TypeId.GENERAL: _(
                "%(username)s, registration to the event %(event_name)s has been cancelled."
            ),
            Event.TypeId.COURSE: _(
                "%(username)s, registration to the course %(event_name)s has been cancelled."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "%(username)s, registration to the volunteering %(event_name)s has been cancelled."
            ),
        },
        "secondary_heading_without_username": {
            Event.TypeId.GENERAL: _(
                "Registration to the event %(event_name)s has been cancelled."
            ),
            Event.TypeId.COURSE: _(
                "Registration to the course %(event_name)s has been cancelled."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "Registration to the volunteering %(event_name)s has been cancelled."
            ),
        },
        "text": {
            Event.TypeId.GENERAL: _(
                "You have successfully cancelled your registration to the event <strong>%(event_name)s</strong>."
            ),
            Event.TypeId.COURSE: _(
                "You have successfully cancelled your registration to the course <strong>%(event_name)s</strong>."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "You have successfully cancelled your registration to the volunteering <strong>%(event_name)s</strong>."
            ),
        },
    },
    SignUpNotificationType.CONFIRMATION: {
        "heading": _("Welcome %(username)s"),
        "heading_without_username": _("Welcome"),
        "secondary_heading": {
            Event.TypeId.GENERAL: _(
                "Registration to the event %(event_name)s has been saved."
            ),
            Event.TypeId.COURSE: _(
                "Registration to the course %(event_name)s has been saved."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "Registration to the volunteering %(event_name)s has been saved."
            ),
        },
        "text": {
            Event.TypeId.GENERAL: _(
                "Congratulations! Your registration has been confirmed for the event <strong>%(event_name)s</strong>."
            ),
            Event.TypeId.COURSE: _(
                "Congratulations! Your registration has been confirmed for the course <strong>%(event_name)s</strong>."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "Congratulations! Your registration has been confirmed for the volunteering <strong>%(event_name)s</strong>."  # noqa E501
            ),
        },
        "group": {
            "heading": _("Welcome"),
            "secondary_heading": {
                Event.TypeId.GENERAL: _(
                    "Group registration to the event %(event_name)s has been saved."
                ),
                Event.TypeId.COURSE: _(
                    "Group registration to the course %(event_name)s has been saved."
                ),
                Event.TypeId.VOLUNTEERING: _(
                    "Group registration to the volunteering %(event_name)s has been saved."
                ),
            },
        },
    },
    SignUpNotificationType.CONFIRMATION_TO_WAITING_LIST: {
        "heading": _("Thank you for signing up for the waiting list"),
        "text": {
            Event.TypeId.GENERAL: _(
                "You have successfully registered for the event <strong>%(event_name)s</strong> waiting list."
            ),
            Event.TypeId.COURSE: _(
                "You have successfully registered for the course <strong>%(event_name)s</strong> waiting list."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "You have successfully registered for the volunteering <strong>%(event_name)s</strong> waiting list."
            ),
        },
        "secondary_text": {
            Event.TypeId.GENERAL: _(
                "You will be automatically transferred as an event participant if a seat becomes available."
            ),
            Event.TypeId.COURSE: _(
                "You will be automatically transferred as a course participant if a seat becomes available."
            ),
            Event.TypeId.VOLUNTEERING: _(
                "You will be automatically transferred as a volunteering participant if a seat becomes available."
            ),
        },
        "group": {
            "text": {
                Event.TypeId.GENERAL: _(
                    "The registration for the event <strong>%(event_name)s</strong> waiting list was successful."
                ),
                Event.TypeId.COURSE: _(
                    "The registration for the course <strong>%(event_name)s</strong> waiting list was successful."
                ),
                Event.TypeId.VOLUNTEERING: _(
                    "The registration for the volunteering <strong>%(event_name)s</strong> waiting list was successful."
                ),
            },
            "secondary_text": {
                Event.TypeId.GENERAL: _(
                    "You will be automatically transferred from the waiting list to become a participant in the event if a place becomes available."  # noqa E501
                ),
                Event.TypeId.COURSE: _(
                    "You will be automatically transferred from the waiting list to become a participant in the course if a place becomes available."  # noqa E501
                ),
                Event.TypeId.VOLUNTEERING: _(
                    "You will be automatically transferred from the waiting list to become a participant in the volunteering if a place becomes available."  # noqa E501
                ),
            },
        },
    },
    SignUpNotificationType.TRANSFERRED_AS_PARTICIPANT: {
        "heading": _("Welcome %(username)s"),
        "heading_without_username": _("Welcome"),
        "text": {
            Event.TypeId.GENERAL: _(
                "You have been moved from the waiting list of the event <strong>%(event_name)s</strong> to a participant."  # noqa E501
            ),
            Event.TypeId.COURSE: _(
                "You have been moved from the waiting list of the course <strong>%(event_name)s</strong> to a participant."  # noqa E501
            ),
            Event.TypeId.VOLUNTEERING: _(
                "You have been moved from the waiting list of the volunteering <strong>%(event_name)s</strong> to a participant."  # noqa E501
            ),
        },
    },
}


registration_user_access_invitation_subjects = {
    "registration_user_access": _(
        "Rights granted to the participant list - %(event_name)s"
    ),
    "registration_substitute_user": _(
        "Rights granted to the registration - %(event_name)s"
    ),
}


registration_user_access_invitation_texts = {
    "registration_user_access": {
        "text": {
            Event.TypeId.GENERAL: _(
                "The e-mail address <strong>%(email)s</strong> has been granted the rights to read the participant list of the event <strong>%(event_name)s</strong>."  # noqa E501
            ),
            Event.TypeId.COURSE: _(
                "The e-mail address <strong>%(email)s</strong> has been granted the rights to read the participant list of the course <strong>%(event_name)s</strong>."  # noqa E501
            ),
            Event.TypeId.VOLUNTEERING: _(
                "The e-mail address <strong>%(email)s</strong> has been granted the rights to read the participant list of the volunteering <strong>%(event_name)s</strong>."  # noqa E501
            ),
        }
    },
    "registration_substitute_user": {
        "text": {
            Event.TypeId.GENERAL: _(
                "The e-mail address <strong>%(email)s</strong> has been granted substitute user rights to the registration of the event <strong>%(event_name)s</strong>."  # noqa E501
            ),
            Event.TypeId.COURSE: _(
                "The e-mail address <strong>%(email)s</strong> has been granted substitute user rights to the registration of the course <strong>%(event_name)s</strong>."  # noqa E501
            ),
            Event.TypeId.VOLUNTEERING: _(
                "The e-mail address <strong>%(email)s</strong> has been granted substitute user rights to the registration of the volunteering <strong>%(event_name)s</strong>."  # noqa E501
            ),
        }
    },
}


def _get_notification_texts(
    notification_type, text_options, event_type_id, event_name, username
):
    if notification_type == SignUpNotificationType.EVENT_CANCELLATION:
        return {
            "heading": text_options["heading"] % {"event_name": event_name},
            "text": text_options["text"],
        }

    if username:
        texts = {
            "heading": text_options["heading"] % {"username": username},
            "text": text_options["text"][event_type_id] % {"event_name": event_name},
        }
    else:
        texts = {
            "heading": text_options.get(
                "heading_without_username", text_options["heading"]
            ),
            "text": text_options["text"][event_type_id] % {"event_name": event_name},
        }

    return texts


def _format_confirmation_message_texts(texts, confirmation_message):
    if confirmation_message:
        texts["confirmation_message"] = confirmation_message


def _format_cancellation_texts(
    texts, text_options, event_type_id, event_name, username
):
    if username:
        texts["secondary_heading"] = text_options["secondary_heading"][
            event_type_id
        ] % {
            "event_name": event_name,
            "username": username,
        }
    else:
        texts["secondary_heading"] = text_options["secondary_heading_without_username"][
            event_type_id
        ] % {"event_name": event_name}


def _format_confirmation_texts(
    texts, text_options, event_type_id, event_name, contact_person
):
    if contact_person.signup_group_id:
        # Override default confirmation message heading
        texts["heading"] = text_options["group"]["heading"]
        texts["secondary_heading"] = text_options["group"]["secondary_heading"][
            event_type_id
        ] % {"event_name": event_name}
    else:
        texts["secondary_heading"] = text_options["secondary_heading"][
            event_type_id
        ] % {"event_name": event_name}


def _format_confirmation_to_waiting_list_texts(
    texts, text_options, event_type_id, event_name, contact_person
):
    if contact_person.signup_group_id:
        # Override default confirmation message heading
        texts["text"] = text_options["group"]["text"][event_type_id] % {
            "event_name": event_name
        }
        texts["secondary_text"] = text_options["group"]["secondary_text"][event_type_id]
    else:
        texts["secondary_text"] = text_options["secondary_text"][event_type_id]


def get_signup_notification_texts(
    contact_person, notification_type: SignUpNotificationType
):
    registration = contact_person.registration

    with translation.override(contact_person.get_service_language_pk()):
        confirmation_message = registration.confirmation_message
        event_name = registration.event.name

    event_type_id = registration.event.type_id
    username = contact_person.first_name
    text_options = signup_email_texts[notification_type]
    texts = _get_notification_texts(
        notification_type, text_options, event_type_id, event_name, username
    )

    if notification_type == SignUpNotificationType.CANCELLATION:
        _format_cancellation_texts(
            texts, text_options, event_type_id, event_name, username
        )
    elif notification_type == SignUpNotificationType.CONFIRMATION:
        _format_confirmation_texts(
            texts, text_options, event_type_id, event_name, contact_person
        )
        _format_confirmation_message_texts(texts, confirmation_message)
    elif notification_type == SignUpNotificationType.CONFIRMATION_TO_WAITING_LIST:
        _format_confirmation_to_waiting_list_texts(
            texts, text_options, event_type_id, event_name, contact_person
        )
    elif notification_type == SignUpNotificationType.TRANSFERRED_AS_PARTICIPANT:
        _format_confirmation_message_texts(texts, confirmation_message)

    return texts


def get_signup_notification_subject(contact_person, notification_type):
    registration = contact_person.registration
    linked_registrations_ui_locale = get_ui_locales(contact_person.service_language)[1]

    with translation.override(contact_person.get_service_language_pk()):
        event_name = registration.event.name

    with translation.override(linked_registrations_ui_locale):
        notification_subject = signup_notification_subjects[notification_type] % {
            "event_name": event_name
        }

    return notification_subject


def get_signup_notification_variables(contact_person):
    [linked_events_ui_locale, linked_registrations_ui_locale] = get_ui_locales(
        contact_person.service_language
    )
    signup_edit_url = get_signup_edit_url(
        contact_person, linked_registrations_ui_locale
    )
    registration = contact_person.registration

    with translation.override(contact_person.get_service_language_pk()):
        event_name = registration.event.name
        event_type_id = registration.event.type_id

        email_variables = {
            "event_name": event_name,
            "event_type_id": event_type_id,
            "linked_events_ui_locale": linked_events_ui_locale,
            "linked_events_ui_url": settings.LINKED_EVENTS_UI_URL,
            "linked_registrations_ui_locale": linked_registrations_ui_locale,
            "linked_registrations_ui_url": settings.LINKED_REGISTRATIONS_UI_URL,
            "registration_id": registration.id,
            "signup_edit_url": signup_edit_url,
            "username": contact_person.first_name,
        }

    return email_variables


def get_registration_user_access_invitation_texts(registration_user_access):
    registration = registration_user_access.registration
    language = registration_user_access.get_language_pk()
    event_type_id = registration.event.type_id

    if registration_user_access.is_substitute_user:
        text_options = registration_user_access_invitation_texts[
            "registration_substitute_user"
        ]
    else:
        text_options = registration_user_access_invitation_texts[
            "registration_user_access"
        ]

    with translation.override(language):
        event_name = registration.event.name
        texts = {
            "text": text_options["text"][event_type_id]
            % {
                "email": registration_user_access.email,
                "event_name": event_name,
            }
        }

    return texts


def get_registration_user_access_invitation_subject(registration_user_access):
    registration = registration_user_access.registration
    language = registration_user_access.get_language_pk()

    with translation.override(language):
        event_name = registration.event.name

        if registration_user_access.is_substitute_user:
            subject = registration_user_access_invitation_subjects[
                "registration_substitute_user"
            ]
        else:
            subject = registration_user_access_invitation_subjects[
                "registration_user_access"
            ]

    return subject % {"event_name": event_name}


def get_registration_user_access_invitation_variables(registration_user_access):
    registration = registration_user_access.registration
    language = registration_user_access.get_language_pk()

    if registration_user_access.is_substitute_user:
        base_url = settings.LINKED_EVENTS_UI_URL
        registration_term = "registrations"
    else:
        base_url = settings.LINKED_REGISTRATIONS_UI_URL
        registration_term = "registration"
    participant_list_url = (
        f"{base_url}/{language}/{registration_term}/{registration.pk}/attendance-list/"
    )

    email_variables = {
        "linked_events_ui_locale": language,
        "linked_events_ui_url": settings.LINKED_EVENTS_UI_URL,
        "linked_registrations_ui_url": settings.LINKED_REGISTRATIONS_UI_URL,
        "participant_list_url": participant_list_url,
    }

    return email_variables
