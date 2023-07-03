from copy import deepcopy
from datetime import date, timedelta

import pytest
from django.core import mail
from django.utils import translation
from django.utils.timezone import localtime
from freezegun import freeze_time
from rest_framework import status

from events.models import Event, Language
from events.tests.utils import versioned_reverse as reverse
from registrations.models import MandatoryFields, SeatReservationCode, SignUp

# === util methods ===


def create_signups(api_client, signups_data):
    create_url = reverse("signup-list")
    response = api_client.post(create_url, signups_data, format="json")

    return response


def assert_create_signups(api_client, signups_data):
    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_201_CREATED

    return response


# === tests ===


@pytest.mark.django_db
def test_successful_signup(api_client, languages, registration):
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "name": "Michael Jackson",
                "date_of_birth": "2011-04-07",
                "email": "test@test.com",
                "phone_number": "0441111111",
                "notifications": "sms",
                "service_language": "fi",
                "native_language": "fi",
                "street_address": "my street",
                "zipcode": "myzip1",
            }
        ],
    }

    assert_create_signups(api_client, signups_data)
    assert SignUp.objects.count() == 1

    signup = SignUp.objects.first()
    assert signup.attendee_status == SignUp.AttendeeStatus.ATTENDING
    assert signup.name == signups_data["signups"][0]["name"]
    assert signup.date_of_birth == date(2011, 4, 7)
    assert signup.email == signups_data["signups"][0]["email"]
    assert signup.phone_number == signups_data["signups"][0]["phone_number"]
    assert signup.notifications == SignUp.NotificationType.SMS
    assert signup.native_language.pk == "fi"
    assert signup.service_language.pk == "fi"
    assert signup.street_address == signups_data["signups"][0]["street_address"]
    assert signup.zipcode == signups_data["signups"][0]["zipcode"]


@pytest.mark.django_db
def test_cannot_signup_if_enrolment_is_not_opened(api_client, event, registration):
    registration.enrolment_start_time = localtime() + timedelta(days=1)
    registration.enrolment_end_time = localtime() + timedelta(days=2)
    registration.save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["detail"] == "Enrolment is not yet open."


@pytest.mark.django_db
def test_cannot_signup_if_enrolment_is_closed(api_client, event, registration):
    registration.enrolment_start_time = localtime() - timedelta(days=2)
    registration.enrolment_end_time = localtime() - timedelta(days=1)
    registration.save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["detail"] == "Enrolment is already closed."


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_missing(api_client, registration):
    signups_payload = {
        "registration": registration.id,
        "signups": [],
    }

    response = create_signups(api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0].code == "required"


@pytest.mark.django_db
def test_amount_if_signups_cannot_be_greater_than_maximum_group_size(
    api_client, event, registration
):
    registration.audience_min_age = None
    registration.audience_max_age = None
    registration.maximum_attendee_capacity = None
    registration.maximum_group_size = 2
    registration.save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=3)
    code = reservation.code
    signup_payload = {
        "name": "Mickey Mouse",
        "email": "test3@test.com",
    }
    signups_payload = {
        "registration": registration.id,
        "reservation_code": code,
        "signups": [signup_payload, signup_payload, signup_payload],
    }
    response = create_signups(api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["signups"][0].code == "max_group_size"


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_invalid(api_client, registration):
    signups_payload = {
        "registration": registration.id,
        "reservation_code": "c5e7d3ba-e48d-447c-b24d-c779950b2acb",
        "signups": [],
    }

    response = create_signups(api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code doesn't exist."


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_for_different_registration(
    api_client, registration, registration2
):
    reservation = SeatReservationCode.objects.create(
        registration=registration2, seats=2
    )
    code = reservation.code
    signups_payload = {
        "registration": registration.id,
        "reservation_code": code,
        "signups": [],
    }

    response = create_signups(api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code doesn't exist."


@pytest.mark.django_db
def test_cannot_signup_if_number_of_signups_exceeds_number_reserved_seats(
    api_client, registration
):
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)

    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "name": "Mickey Mouse",
                "email": "test3@test.com",
            },
            {
                "name": "Minney Mouse",
                "email": "test2@test.com",
            },
        ],
    }
    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["signups"][0]
        == "Number of signups exceeds the number of requested seats"
    )


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_expired(api_client, registration):
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    reservation.timestamp = reservation.timestamp - timedelta(days=1)
    reservation.save()

    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "name": "Mickey Mouse",
                "date_of_birth": "2011-04-07",
                "email": "test3@test.com",
            },
        ],
    }
    response = create_signups(api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code has expired."


@pytest.mark.django_db
def test_can_signup_twice_with_same_phone_or_email(api_client, registration):
    reservation = SeatReservationCode.objects.create(registration=registration, seats=3)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
        "date_of_birth": "2011-04-07",
    }
    signup_data_same_email = deepcopy(signup_data)
    signup_data_same_email["phone_number"] = "0442222222"
    signup_data_same_phone = deepcopy(signup_data)
    signup_data_same_phone["email"] = "another@email.com"
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data, signup_data_same_email, signup_data_same_phone],
    }

    # Create a signups
    assert_create_signups(api_client, signups_data)


@pytest.mark.parametrize("min_age", [None, 0, 10])
@pytest.mark.parametrize("max_age", [None, 0, 100])
@pytest.mark.parametrize("date_of_birth", [None, "1980-12-30"])
@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_date_of_birth_is_mandatory_if_audience_min_or_max_age_specified(
    api_client, date_of_birth, min_age, max_age, registration, user
):
    falsy_values = ("", None)

    # Update registration
    registration.maximum_attendee_capacity = 1
    registration.audience_min_age = None
    registration.audience_max_age = None
    registration.enrolment_start_time = localtime()
    registration.enrolment_end_time = localtime() + timedelta(days=10)

    if min_age not in falsy_values:
        registration.audience_min_age = min_age
    if max_age not in falsy_values:
        registration.audience_max_age = max_age
    registration.save()

    if (
        min_age not in falsy_values or max_age not in falsy_values
    ) and not date_of_birth:
        expected_status = status.HTTP_400_BAD_REQUEST
        expected_error = "This field must be specified."
    else:
        expected_status = status.HTTP_201_CREATED
        expected_error = None

    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
        "notifications": "sms",
    }
    if date_of_birth:
        signup_data["date_of_birth"] = date_of_birth

    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(api_client, signups_data)
    assert response.status_code == expected_status

    if expected_error:
        assert response.data["signups"][0]["date_of_birth"][0] == expected_error


@pytest.mark.parametrize(
    "date_of_birth,expected_status,expected_error",
    [
        ("2011-04-07", status.HTTP_400_BAD_REQUEST, "The participant is too young."),
        ("1879-03-14", status.HTTP_400_BAD_REQUEST, "The participant is too old."),
        ("2000-02-29", status.HTTP_201_CREATED, None),
    ],
)
@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_signup_age_has_to_match_the_audience_min_max_age(
    api_client, date_of_birth, expected_error, expected_status, registration
):
    registration.audience_max_age = 40
    registration.audience_min_age = 20
    registration.enrolment_start_time = localtime()
    registration.enrolment_end_time = localtime() + timedelta(days=10)
    registration.maximum_attendee_capacity = 1
    registration.save()

    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
        "notifications": "sms",
        "date_of_birth": date_of_birth,
    }
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = create_signups(api_client, signups_data)

    assert response.status_code == expected_status
    if expected_error:
        assert response.data["signups"][0]["date_of_birth"][0] == expected_error


@pytest.mark.parametrize(
    "mandatory_field_id",
    [
        MandatoryFields.CITY,
        MandatoryFields.NAME,
        MandatoryFields.PHONE_NUMBER,
        MandatoryFields.STREET_ADDRESS,
        MandatoryFields.ZIPCODE,
    ],
)
@pytest.mark.django_db
def test_signup_mandatory_fields_has_to_be_filled(
    api_client, mandatory_field_id, registration
):
    registration.mandatory_fields = [mandatory_field_id]
    registration.save()

    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "phone_number": "0441111111",
        "street_address": "Street address",
        "city": "Helsinki",
        "zipcode": "00100",
        "notifications": "sms",
    }
    signup_data[mandatory_field_id] = ""
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["signups"][0][mandatory_field_id][0]
        == "This field must be specified."
    )


@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_cannot_signup_with_not_allowed_service_language(
    api_client, languages, registration
):
    languages[0].service_language = False
    languages[0].save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "name": "Michael Jackson",
                "date_of_birth": "2011-04-07",
                "email": "test@test.com",
                "service_language": languages[0].pk,
            }
        ],
    }

    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["signups"][0]["service_language"][0].code == "does_not_exist"


@pytest.mark.django_db
def test_group_signup_successful_with_waitlist(api_client, registration):
    registration.maximum_attendee_capacity = 2
    registration.waiting_list_capacity = 2
    registration.save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=2)
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "name": "User 1",
                "email": "test1@test.com",
            },
            {
                "name": "User 2",
                "email": "test2@test.com",
            },
        ],
    }
    assert_create_signups(api_client, signups_payload)
    assert registration.signups.count() == 2

    reservation2 = SeatReservationCode.objects.create(
        registration=registration, seats=2
    )
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation2.code,
        "signups": [
            {
                "name": "User 3",
                "email": "test3@test.com",
            },
            {
                "name": "User 4",
                "email": "test4@test.com",
            },
        ],
    }
    assert_create_signups(api_client, signups_payload)
    assert registration.signups.count() == 4
    assert (
        registration.signups.filter(
            attendee_status=SignUp.AttendeeStatus.ATTENDING
        ).count()
        == 2
    )
    assert (
        registration.signups.filter(
            attendee_status=SignUp.AttendeeStatus.WAITING_LIST
        ).count()
        == 2
    )


@pytest.mark.parametrize(
    "service_language,expected_subject,expected_heading,expected_text",
    [
        (
            "en",
            "Registration confirmation",
            "Registration to the event Foo has been saved.",
            "Congratulations! You have successfully registered to the event <strong>Foo</strong>.",
        ),
        (
            "fi",
            "Vahvistus ilmoittautumisesta",
            "Ilmoittautuminen tapahtuman Foo jonotuslistaan on tallennettu.",
            "Onnittelut! Olet onnistuneesti ilmoittautunut tapahtumaan <strong>Foo</strong>.",
        ),
        (
            "sv",
            "Bekräftelse av registrering",
            "Anmälan till evenemanget Foo väntelista har sparats.",
            "Grattis! Du har framgångsrikt registrerat dig till evenemanget <strong>Foo</strong>.",
        ),
    ],
)
@pytest.mark.django_db
def test_email_sent_on_successful_signup(
    api_client,
    expected_heading,
    expected_subject,
    expected_text,
    languages,
    registration,
    service_language,
):
    with translation.override(service_language):
        registration.event.type_id = Event.TypeId.GENERAL
        registration.event.name = "Foo"
        registration.event.save()

        reservation = SeatReservationCode.objects.create(
            registration=registration, seats=1
        )
        signup_data = {
            "name": "Michael Jackson",
            "date_of_birth": "2011-04-07",
            "email": "test@test.com",
            "service_language": service_language,
        }
        signups_data = {
            "registration": registration.id,
            "reservation_code": reservation.code,
            "signups": [signup_data],
        }
        response = assert_create_signups(api_client, signups_data)
        assert signup_data["name"] in response.data["attending"]["people"][0]["name"]
        #  assert that the email was sent
        assert mail.outbox[0].subject.startswith(expected_subject)
        assert expected_heading in str(mail.outbox[0].alternatives[0])
        assert expected_text in str(mail.outbox[0].alternatives[0])


@pytest.mark.parametrize(
    "event_type,expected_heading,expected_text",
    [
        (
            Event.TypeId.GENERAL,
            "Registration to the event Foo has been saved.",
            "Congratulations! You have successfully registered to the event <strong>Foo</strong>.",
        ),
        (
            Event.TypeId.COURSE,
            "Registration to the course Foo has been saved.",
            "Congratulations! You have successfully registered to the course <strong>Foo</strong>.",
        ),
        (
            Event.TypeId.VOLUNTEERING,
            "Registration to the volunteering Foo has been saved.",
            "Congratulations! You have successfully registered to the volunteering <strong>Foo</strong>.",
        ),
    ],
)
@pytest.mark.django_db
def test_confirmation_template_has_correct_text_per_event_type(
    api_client, event_type, expected_heading, expected_text, languages, registration
):
    registration.event.type_id = event_type
    registration.event.name = "Foo"
    registration.event.save()
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "service_language": "en",
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = assert_create_signups(api_client, signups_data)
    assert signup_data["name"] in response.data["attending"]["people"][0]["name"]
    #  assert that the email was sent
    assert expected_heading in str(mail.outbox[0].alternatives[0])
    assert expected_text in str(mail.outbox[0].alternatives[0])


@pytest.mark.parametrize(
    "service_language,confirmation_message",
    [
        ("en", "Confirmation message"),
        ("fi", "Vahvistusviesti"),
        # Use default language if confirmation message is not defined to service language
        ("sv", "Vahvistusviesti"),
    ],
)
@pytest.mark.django_db
def test_confirmation_message_is_shown_in_service_language(
    api_client,
    confirmation_message,
    languages,
    registration,
    service_language,
):
    Language.objects.get_or_create(
        id=service_language, defaults={"name": service_language}
    )
    registration.confirmation_message_en = "Confirmation message"
    registration.confirmation_message_fi = "Vahvistusviesti"
    registration.save()

    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "service_language": service_language,
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    assert_create_signups(api_client, signups_data)
    assert confirmation_message in str(mail.outbox[0].alternatives[0])


@pytest.mark.parametrize(
    "service_language,expected_subject,expected_text",
    [
        (
            "en",
            "Waiting list seat reserved",
            "You have successfully registered for the event <strong>Foo</strong> waiting list.",
        ),
        (
            "fi",
            "Paikka jonotuslistalla varattu",
            "Olet onnistuneesti ilmoittautunut tapahtuman <strong>Foo</strong> jonotuslistalle.",
        ),
        (
            "sv",
            "Väntelista plats reserverad",
            "Du har framgångsrikt registrerat dig för evenemangets <strong>Foo</strong> väntelista.",
        ),
    ],
)
@pytest.mark.django_db
def test_different_email_sent_if_user_is_added_to_waiting_list(
    api_client,
    expected_subject,
    expected_text,
    languages,
    registration,
    service_language,
    signup,
):
    with translation.override(service_language):
        registration.event.type_id = Event.TypeId.GENERAL
        registration.event.name = "Foo"
        registration.event.save()
        registration.maximum_attendee_capacity = 1
        registration.save()
        reservation = SeatReservationCode.objects.create(
            registration=registration, seats=1
        )
        signup_data = {
            "name": "Michael Jackson",
            "email": "test@test.com",
            "service_language": service_language,
        }
        signups_data = {
            "registration": registration.id,
            "reservation_code": reservation.code,
            "signups": [signup_data],
        }
        response = assert_create_signups(api_client, signups_data)
        assert signup_data["name"] in response.data["waitlisted"]["people"][0]["name"]
        #  assert that the email was sent
        assert mail.outbox[0].subject.startswith(expected_subject)
        assert expected_text in str(mail.outbox[0].alternatives[0])


@pytest.mark.parametrize(
    "event_type,expected_text",
    [
        (
            Event.TypeId.GENERAL,
            "You have successfully registered for the event <strong>Foo</strong> waiting list.",
        ),
        (
            Event.TypeId.COURSE,
            "You have successfully registered for the course <strong>Foo</strong> waiting list.",
        ),
        (
            Event.TypeId.VOLUNTEERING,
            "You have successfully registered for the volunteering <strong>Foo</strong> waiting list.",
        ),
    ],
)
@pytest.mark.django_db
def test_confirmation_to_waiting_list_template_has_correct_text_per_event_type(
    api_client,
    event_type,
    expected_text,
    languages,
    registration,
    signup,
):
    registration.event.type_id = event_type
    registration.event.name = "Foo"
    registration.event.save()
    registration.maximum_attendee_capacity = 1
    registration.save()
    reservation = SeatReservationCode.objects.create(registration=registration, seats=1)
    signup_data = {
        "name": "Michael Jackson",
        "email": "test@test.com",
        "service_language": "en",
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = assert_create_signups(api_client, signups_data)
    assert signup_data["name"] in response.data["waitlisted"]["people"][0]["name"]
    #  assert that the email was sent
    assert expected_text in str(mail.outbox[0].alternatives[0])
