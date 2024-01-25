from copy import deepcopy
from datetime import date, timedelta

import pytest
from django.core import mail
from django.utils import translation
from django.utils.timezone import localtime
from freezegun import freeze_time
from rest_framework import status

from audit_log.models import AuditLogEntry
from events.models import Event, Language
from events.tests.factories import LanguageFactory
from events.tests.utils import versioned_reverse as reverse
from helevents.tests.factories import UserFactory
from registrations.models import (
    MandatoryFields,
    SeatReservationCode,
    SignUp,
    SignUpContactPerson,
    SignUpPriceGroup,
)
from registrations.notifications import NotificationType
from registrations.tests.factories import (
    RegistrationFactory,
    RegistrationPriceGroupFactory,
    RegistrationUserAccessFactory,
    SeatReservationCodeFactory,
    SignUpContactPersonFactory,
    SignUpFactory,
    SignUpGroupFactory,
)
from registrations.tests.test_registration_post import hel_email
from registrations.tests.test_signup_patch import description_fields
from registrations.tests.utils import create_user_by_role

test_email1 = "test@email.com"
test_street_address = "my street"
default_signups_data = {
    "signups": [
        {
            "first_name": "Michael",
            "last_name": "Jackson",
            "extra_info": "Extra info",
            "date_of_birth": "2011-04-07",
            "phone_number": "0401111111",
            "street_address": test_street_address,
            "zipcode": "myzip1",
            "user_consent": True,
            "contact_person": {
                "email": test_email1,
                "phone_number": "0441111111",
                "notifications": "sms",
                "service_language": "fi",
                "native_language": "fi",
            },
        }
    ],
}

# === util methods ===


def create_signups(api_client, signups_data):
    create_url = reverse("signup-list")
    response = api_client.post(create_url, signups_data, format="json")

    return response


def assert_create_signups(api_client, signups_data):
    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_201_CREATED

    return response


def assert_default_contact_person_created(contact_person_data):
    assert SignUpContactPerson.objects.count() == 1

    contact_person = SignUpContactPerson.objects.first()
    assert contact_person.email == contact_person_data["email"]
    assert contact_person.phone_number == contact_person_data["phone_number"]
    assert contact_person.notifications == NotificationType.SMS
    assert contact_person.native_language.pk == "fi"
    assert contact_person.service_language.pk == "fi"


def assert_default_signup_created(signups_data, user):
    assert SignUp.objects.count() == 1
    assert SeatReservationCode.objects.count() == 0

    signup = SignUp.objects.first()
    assert signup.attendee_status == SignUp.AttendeeStatus.ATTENDING
    assert signup.first_name == signups_data["signups"][0]["first_name"]
    assert signup.last_name == signups_data["signups"][0]["last_name"]
    assert signup.phone_number == signups_data["signups"][0]["phone_number"]
    if signups_data["signups"][0].get("date_of_birth"):
        assert signup.date_of_birth == date(2011, 4, 7)
    else:
        assert signup.date_of_birth is None
    if signups_data["signups"][0].get("extra_info"):
        assert signup.extra_info == signups_data["signups"][0]["extra_info"]
    else:
        assert signup.extra_info in [None, ""]
    assert signup.street_address == signups_data["signups"][0]["street_address"]
    assert signup.zipcode == signups_data["signups"][0]["zipcode"]
    assert signup.created_by_id == user.id
    assert signup.last_modified_by_id == user.id
    assert signup.created_time is not None
    assert signup.last_modified_time is not None
    assert signup.user_consent is signups_data["signups"][0]["user_consent"]

    assert_default_contact_person_created(signups_data["signups"][0]["contact_person"])


def assert_attending_and_waitlisted_signups(
    response,
    expected_status_code=status.HTTP_201_CREATED,
    expected_signups_count=2,
    expected_attending=2,
    expected_waitlisted=0,
):
    assert SignUp.objects.count() == expected_signups_count
    assert (
        SignUp.objects.filter(attendee_status=SignUp.AttendeeStatus.ATTENDING).count()
        == expected_attending
    )
    assert (
        SignUp.objects.filter(
            attendee_status=SignUp.AttendeeStatus.WAITING_LIST
        ).count()
        == expected_waitlisted
    )

    assert response.status_code == expected_status_code
    if expected_status_code == status.HTTP_403_FORBIDDEN:
        assert response.json()["detail"] == "The waiting list is already full"


# === tests ===


@pytest.mark.parametrize(
    "user_role",
    [
        "admin",
        "registration_admin",
        "financial_admin",
        "regular_user",
        "regular_user_without_organization",
        "registration_user_access",
        "registration_substitute_user",
    ],
)
@pytest.mark.django_db
def test_authenticated_users_can_create_signups(registration, api_client, user_role):
    LanguageFactory(pk="fi", service_language=True)

    user_email = (
        hel_email if user_role == "registration_substitute_user" else "user@test.com"
    )
    user = create_user_by_role(
        user_role,
        registration.publisher,
        additional_roles={
            "regular_user_without_organization": lambda usr: None,
            "registration_user_access": lambda usr: RegistrationUserAccessFactory(
                registration=registration,
                email=user_email,
            ),
            "registration_substitute_user": lambda usr: RegistrationUserAccessFactory(
                registration=registration, email=user_email, is_substitute_user=True
            ),
        },
    )
    user.email = user_email
    user.save(update_fields=["email"])

    api_client.force_authenticate(user)

    reservation = SeatReservationCodeFactory(seats=1, registration=registration)

    assert SignUp.objects.count() == 0
    assert SeatReservationCode.objects.count() == 1

    signups_data = default_signups_data
    signups_data["registration"] = registration.id
    signups_data["reservation_code"] = reservation.code

    assert_create_signups(api_client, signups_data)
    assert_default_signup_created(signups_data, user)


@pytest.mark.django_db
def test_can_create_signups_with_empty_extra_info_and_date_of_birth(
    user, user_api_client
):
    LanguageFactory(id="fi", service_language=True)

    reservation = SeatReservationCodeFactory(seats=1)

    assert SignUp.objects.count() == 0
    assert SeatReservationCode.objects.count() == 1

    signups_data = default_signups_data
    signups_data["registration"] = reservation.registration.id
    signups_data["reservation_code"] = reservation.code
    signups_data["signups"][0]["extra_info"] = ""
    signups_data["signups"][0]["date_of_birth"] = None

    assert_create_signups(user_api_client, signups_data)
    assert_default_signup_created(signups_data, user)


@pytest.mark.django_db
def test_non_authenticated_user_cannot_create_signups(api_client, languages):
    reservation = SeatReservationCodeFactory(seats=1)
    signups_data = default_signups_data
    signups_data["registration"] = reservation.registration.id
    signups_data["reservation_code"] = reservation.code

    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_add_signups_to_group(user_api_client, languages, registration, user):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=2)

    signup_group = SignUpGroupFactory(registration=registration)
    SignUpFactory(signup_group=signup_group, registration=registration)
    SignUpContactPersonFactory(signup_group=signup_group)

    assert signup_group.signups.count() == 1
    assert SeatReservationCode.objects.count() == 1
    assert SignUpContactPerson.objects.count() == 1

    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "signup_group": signup_group.id,
                "first_name": "Michael",
                "last_name": "Jackson",
                "date_of_birth": "2011-04-07",
                "street_address": test_street_address,
                "zipcode": "myzip1",
            },
            {
                "signup_group": signup_group.id,
                "first_name": "Mickey",
                "last_name": "Mouse",
                "date_of_birth": "1928-05-15",
                "street_address": test_street_address,
                "zipcode": "myzip1",
                "user_consent": True,
            },
        ],
    }

    assert_create_signups(user_api_client, signups_data)

    signup_group.refresh_from_db()
    assert signup_group.signups.count() == 3
    assert SeatReservationCode.objects.count() == 0

    new_signup = signup_group.signups.filter(first_name="Michael").first()
    assert new_signup.registration_id == registration.id
    assert new_signup.created_by_id == user.id
    assert new_signup.last_modified_by_id == user.id
    assert new_signup.created_time is not None
    assert new_signup.last_modified_time is not None
    assert new_signup.user_consent is False

    new_signup2 = signup_group.signups.filter(first_name="Mickey").first()
    assert new_signup2.registration_id == registration.id
    assert new_signup2.created_by_id == user.id
    assert new_signup2.last_modified_by_id == user.id
    assert new_signup2.created_time is not None
    assert new_signup2.last_modified_time is not None
    assert new_signup2.user_consent is True

    assert SignUpContactPerson.objects.count() == 1
    assert (
        SignUpContactPerson.objects.filter(
            signup_id__in=(new_signup.pk, new_signup2.pk)
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_cannot_signup_if_enrolment_is_not_opened(
    user_api_client, event, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.enrolment_start_time = localtime() + timedelta(days=1)
    registration.enrolment_end_time = localtime() + timedelta(days=2)
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
        },
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(user_api_client, signups_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["detail"] == "Enrolment is not yet open."


@pytest.mark.django_db
def test_cannot_signup_if_enrolment_is_closed(
    user_api_client, event, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.enrolment_start_time = localtime() - timedelta(days=2)
    registration.enrolment_end_time = localtime() - timedelta(days=1)
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
        },
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(user_api_client, signups_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["detail"] == "Enrolment is already closed."


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_missing(
    user_api_client, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    signups_payload = {
        "registration": registration.id,
        "signups": [],
    }

    response = create_signups(user_api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0].code == "required"


@pytest.mark.django_db
def test_amount_if_signups_cannot_be_greater_than_maximum_group_size(
    user_api_client, event, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.audience_min_age = None
    registration.audience_max_age = None
    registration.maximum_attendee_capacity = None
    registration.maximum_group_size = 2
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=3)
    code = reservation.code
    signup_payload = {
        "first_name": "Mickey",
        "last_name": "Mouse",
        "contact_person": {
            "email": "test3@test.com",
        },
    }
    signups_payload = {
        "registration": registration.id,
        "reservation_code": code,
        "signups": [signup_payload, signup_payload, signup_payload],
    }
    response = create_signups(user_api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["signups"][0].code == "max_group_size"


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_invalid(
    user_api_client, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    signups_payload = {
        "registration": registration.id,
        "reservation_code": "c5e7d3ba-e48d-447c-b24d-c779950b2acb",
        "signups": [],
    }

    response = create_signups(user_api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code doesn't exist."


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_for_different_registration(
    user_api_client, registration, registration2, user
):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(registration=registration2, seats=2)
    code = reservation.code
    signups_payload = {
        "registration": registration.id,
        "reservation_code": code,
        "signups": [],
    }

    response = create_signups(user_api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code doesn't exist."


@pytest.mark.django_db
def test_cannot_signup_if_number_of_signups_exceeds_number_reserved_seats(
    user_api_client, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)

    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "Mickey",
                "last_name": "Mouse",
                "contact_person": {
                    "email": "test3@test.com",
                },
            },
            {
                "first_name": "Minney",
                "last_name": "Mouse",
                "contact_person": {
                    "email": "test2@test.com",
                },
            },
        ],
    }
    response = create_signups(user_api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["signups"][0]
        == "Number of signups exceeds the number of requested seats"
    )


@pytest.mark.django_db
def test_cannot_signup_if_reservation_code_is_expired(
    user_api_client, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    reservation.timestamp = reservation.timestamp - timedelta(days=1)
    reservation.save()

    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "Mickey",
                "last_name": "Mouse",
                "date_of_birth": "2011-04-07",
                "contact_person": {
                    "email": "test3@test.com",
                },
            },
        ],
    }
    response = create_signups(user_api_client, signups_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["reservation_code"][0] == "Reservation code has expired."


@pytest.mark.django_db
def test_can_signup_twice_with_same_phone_or_email(user_api_client, registration, user):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=3)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "date_of_birth": "2011-04-07",
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
        },
    }
    signup_data_same_email = deepcopy(signup_data)
    signup_data_same_email["contact_person"]["phone_number"] = "0442222222"
    signup_data_same_phone = deepcopy(signup_data)
    signup_data_same_phone["contact_person"]["email"] = "another@email.com"
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data, signup_data_same_email, signup_data_same_phone],
    }

    # Create a signups
    assert_create_signups(user_api_client, signups_data)


@pytest.mark.parametrize("min_age", [None, 0, 10])
@pytest.mark.parametrize("max_age", [None, 0, 100])
@pytest.mark.parametrize("date_of_birth", [None, "1980-12-30"])
@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_date_of_birth_is_mandatory_if_audience_min_or_max_age_specified(
    user_api_client, date_of_birth, min_age, max_age, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

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
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
            "notifications": "sms",
        },
    }
    if date_of_birth:
        signup_data["date_of_birth"] = date_of_birth

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }
    response = create_signups(user_api_client, signups_data)
    assert response.status_code == expected_status

    if expected_error:
        assert response.data["signups"][0]["date_of_birth"][0] == expected_error


@pytest.mark.parametrize(
    "date_of_birth,expected_status,expected_error,has_event_start_time",
    [
        (
            "2004-03-13",
            status.HTTP_400_BAD_REQUEST,
            "The participant is too young.",
            False,
        ),
        (
            "2004-03-13",
            status.HTTP_201_CREATED,
            None,
            True,
        ),
        (
            "1982-03-13",
            status.HTTP_400_BAD_REQUEST,
            "The participant is too old.",
            False,
        ),
        (
            "1983-03-13",
            status.HTTP_400_BAD_REQUEST,
            "The participant is too old.",
            True,
        ),
        ("2000-02-29", status.HTTP_201_CREATED, None, False),
    ],
)
@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_signup_age_has_to_match_the_audience_min_max_age(
    user_api_client,
    date_of_birth,
    expected_error,
    expected_status,
    registration,
    user,
    has_event_start_time,
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.event.start_time = (
        localtime() + timedelta(days=365) if has_event_start_time else None
    )
    registration.event.end_time = localtime() + timedelta(days=2 * 365)
    registration.event.save()
    registration.audience_max_age = 40
    registration.audience_min_age = 20
    registration.enrolment_start_time = localtime()
    registration.enrolment_end_time = localtime() + timedelta(days=10)
    registration.maximum_attendee_capacity = 1
    registration.save()

    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "date_of_birth": date_of_birth,
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
            "notifications": "sms",
        },
    }
    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = create_signups(user_api_client, signups_data)

    assert response.status_code == expected_status
    if expected_error:
        assert response.data["signups"][0]["date_of_birth"][0] == expected_error


@pytest.mark.parametrize(
    "mandatory_field_id",
    [
        MandatoryFields.CITY,
        MandatoryFields.FIRST_NAME,
        MandatoryFields.LAST_NAME,
        MandatoryFields.PHONE_NUMBER,
        MandatoryFields.STREET_ADDRESS,
        MandatoryFields.ZIPCODE,
    ],
)
@pytest.mark.django_db
def test_signup_mandatory_fields_has_to_be_filled(
    user_api_client, mandatory_field_id, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.mandatory_fields = [mandatory_field_id]
    registration.save()

    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "street_address": "Street address",
        "city": "Helsinki",
        "zipcode": "00100",
        mandatory_field_id: "",
        "contact_person": {
            "email": test_email1,
            "phone_number": "0441111111",
            "notifications": "sms",
        },
    }
    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = create_signups(user_api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["signups"][0][mandatory_field_id][0]
        == "This field must be specified."
    )


@freeze_time("2023-03-14 03:30:00+02:00")
@pytest.mark.django_db
def test_cannot_signup_with_not_allowed_service_language(
    user_api_client, languages, registration, user
):
    user.get_default_organization().registration_admin_users.add(user)

    languages[0].service_language = False
    languages[0].save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "Michael",
                "last_name": "Jackson",
                "date_of_birth": "2011-04-07",
                "contact_person": {
                    "email": test_email1,
                    "service_language": languages[0].pk,
                },
            }
        ],
    }

    response = create_signups(user_api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["signups"][0]["contact_person"]["service_language"][0].code
        == "does_not_exist"
    )


@pytest.mark.django_db
def test_group_signup_successful_with_waitlist(user_api_client, registration, user):
    user.get_default_organization().registration_admin_users.add(user)

    registration.maximum_attendee_capacity = 2
    registration.waiting_list_capacity = 2
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=2)
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "User",
                "last_name": "1",
                "contact_person": {
                    "email": "test1@test.com",
                },
            },
            {
                "first_name": "User",
                "last_name": "2",
                "contact_person": {
                    "email": "test2@test.com",
                },
            },
        ],
    }
    assert_create_signups(user_api_client, signups_payload)
    assert registration.signups.count() == 2

    reservation2 = SeatReservationCodeFactory(registration=registration, seats=2)
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation2.code,
        "signups": [
            {
                "first_name": "User",
                "last_name": "3",
                "contact_person": {
                    "email": "test3@test.com",
                },
            },
            {
                "first_name": "User",
                "last_name": "4",
                "contact_person": {
                    "email": "test4@test.com",
                },
            },
        ],
    }
    assert_create_signups(user_api_client, signups_payload)
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
    "maximum_attendee_capacity,waiting_list_capacity,expected_signups_count,"
    "expected_attending,expected_waitlisted,expected_status_code",
    [
        (0, 0, 0, 0, 0, status.HTTP_403_FORBIDDEN),
        (1, 1, 2, 1, 1, status.HTTP_201_CREATED),
        (1, 0, 1, 1, 0, status.HTTP_201_CREATED),
        (0, 1, 1, 0, 1, status.HTTP_201_CREATED),
        (2, 1, 2, 2, 0, status.HTTP_201_CREATED),
        (0, 2, 2, 0, 2, status.HTTP_201_CREATED),
        (None, None, 2, 2, 0, status.HTTP_201_CREATED),
        (None, 1, 2, 2, 0, status.HTTP_201_CREATED),
        (1, None, 2, 1, 1, status.HTTP_201_CREATED),
        (0, None, 2, 0, 2, status.HTTP_201_CREATED),
    ],
)
@pytest.mark.django_db
def test_maximum_attendee_and_waiting_list_capacities(
    api_client,
    maximum_attendee_capacity,
    waiting_list_capacity,
    expected_signups_count,
    expected_attending,
    expected_waitlisted,
    expected_status_code,
):
    registration = RegistrationFactory(
        maximum_attendee_capacity=maximum_attendee_capacity,
        waiting_list_capacity=waiting_list_capacity,
    )

    user = UserFactory()
    user.registration_admin_organizations.add(registration.publisher)
    api_client.force_authenticate(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=2)
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "User",
                "last_name": "1",
                "email": "test1@test.com",
            },
            {
                "first_name": "User",
                "last_name": "2",
                "email": "test2@test.com",
            },
        ],
    }

    assert SignUp.objects.count() == 0

    response = create_signups(api_client, signups_payload)

    assert_attending_and_waitlisted_signups(
        response,
        expected_status_code,
        expected_signups_count,
        expected_attending,
        expected_waitlisted,
    )


@pytest.mark.parametrize(
    "maximum_attendee_capacity,waiting_list_capacity,expected_signups_count,"
    "expected_attending,expected_waitlisted,expected_status_code",
    [
        (0, 0, 0, 0, 0, status.HTTP_403_FORBIDDEN),
        (1, 1, 2, 1, 1, status.HTTP_201_CREATED),
        (1, 0, 1, 1, 0, status.HTTP_201_CREATED),
        (0, 1, 1, 0, 1, status.HTTP_201_CREATED),
        (2, 1, 2, 1, 1, status.HTTP_201_CREATED),
        (0, 2, 2, 0, 2, status.HTTP_201_CREATED),
        (None, None, 2, 1, 1, status.HTTP_201_CREATED),
        (None, 1, 2, 1, 1, status.HTTP_201_CREATED),
        (1, None, 2, 1, 1, status.HTTP_201_CREATED),
        (0, None, 2, 0, 2, status.HTTP_201_CREATED),
    ],
)
@pytest.mark.django_db
def test_maximum_attendee_and_waiting_list_capacities_with_attendee_status_given_in_post_data(
    api_client,
    maximum_attendee_capacity,
    waiting_list_capacity,
    expected_signups_count,
    expected_attending,
    expected_waitlisted,
    expected_status_code,
):
    registration = RegistrationFactory(
        maximum_attendee_capacity=maximum_attendee_capacity,
        waiting_list_capacity=waiting_list_capacity,
    )

    user = UserFactory()
    user.registration_admin_organizations.add(registration.publisher)
    api_client.force_authenticate(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=2)
    signups_payload = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "User",
                "last_name": "1",
                "email": "test1@test.com",
                "attendee_status": SignUp.AttendeeStatus.WAITING_LIST,
            },
            {
                "first_name": "User",
                "last_name": "2",
                "email": "test2@test.com",
                "attendee_status": SignUp.AttendeeStatus.ATTENDING,
            },
        ],
    }

    assert SignUp.objects.count() == 0

    response = create_signups(api_client, signups_payload)

    assert_attending_and_waitlisted_signups(
        response,
        expected_status_code,
        expected_signups_count,
        expected_attending,
        expected_waitlisted,
    )


@pytest.mark.parametrize(
    "service_language,username,expected_subject,expected_heading,expected_secondary_heading,expected_text",
    [
        (
            "en",
            "Username",
            "Registration confirmation",
            "Welcome Username",
            "Registration to the event Foo has been saved.",
            "Congratulations! Your registration has been confirmed for the event <strong>Foo</strong>.",
        ),
        (
            "fi",
            "Käyttäjänimi",
            "Vahvistus ilmoittautumisesta",
            "Tervetuloa Käyttäjänimi",
            "Ilmoittautuminen tapahtumaan Foo on tallennettu.",
            "Onnittelut! Ilmoittautumisesi on vahvistettu tapahtumaan <strong>Foo</strong>.",
        ),
        (
            "sv",
            "Användarnamn",
            "Bekräftelse av registrering",
            "Välkommen Användarnamn",
            "Anmälan till evenemanget Foo har sparats.",
            "Grattis! Din registrering har bekräftats för evenemanget <strong>Foo</strong>.",
        ),
        (
            "en",
            None,
            "Registration confirmation",
            "Welcome",
            "Registration to the event Foo has been saved.",
            "Congratulations! Your registration has been confirmed for the event <strong>Foo</strong>.",
        ),
        (
            "fi",
            None,
            "Vahvistus ilmoittautumisesta",
            "Tervetuloa",
            "Ilmoittautuminen tapahtumaan Foo on tallennettu.",
            "Onnittelut! Ilmoittautumisesi on vahvistettu tapahtumaan <strong>Foo</strong>.",
        ),
        (
            "sv",
            None,
            "Bekräftelse av registrering",
            "Välkommen",
            "Anmälan till evenemanget Foo har sparats.",
            "Grattis! Din registrering har bekräftats för evenemanget <strong>Foo</strong>.",
        ),
    ],
)
@pytest.mark.django_db
def test_email_sent_on_successful_signup(
    user_api_client,
    expected_heading,
    expected_secondary_heading,
    expected_subject,
    expected_text,
    registration,
    service_language,
    username,
    user,
):
    user.get_default_organization().registration_admin_users.add(user)

    LanguageFactory(id=service_language, name=service_language, service_language=True)

    with translation.override(service_language):
        registration.event.type_id = Event.TypeId.GENERAL
        registration.event.name = "Foo"
        registration.event.save()

        reservation = SeatReservationCodeFactory(registration=registration, seats=1)
        signup_data = {
            "first_name": "Michael",
            "last_name": "Jackson",
            "date_of_birth": "2011-04-07",
            "contact_person": {
                "first_name": username,
                "email": test_email1,
                "service_language": service_language,
            },
        }
        signups_data = {
            "registration": registration.id,
            "reservation_code": reservation.code,
            "signups": [signup_data],
        }

        response = assert_create_signups(user_api_client, signups_data)
        assert signup_data["first_name"] in response.data[0]["first_name"]

        #  assert that the email was sent
        message_string = str(mail.outbox[0].alternatives[0])
        assert mail.outbox[0].subject.startswith(expected_subject)
        assert expected_heading in message_string
        assert expected_secondary_heading in message_string
        assert expected_text in message_string
        if username is None:
            assert f"{expected_heading} None" not in message_string


@pytest.mark.parametrize(
    "event_type,expected_heading,expected_text",
    [
        (
            Event.TypeId.GENERAL,
            "Registration to the event Foo has been saved.",
            "Congratulations! Your registration has been confirmed for the event <strong>Foo</strong>.",
        ),
        (
            Event.TypeId.COURSE,
            "Registration to the course Foo has been saved.",
            "Congratulations! Your registration has been confirmed for the course <strong>Foo</strong>.",
        ),
        (
            Event.TypeId.VOLUNTEERING,
            "Registration to the volunteering Foo has been saved.",
            "Congratulations! Your registration has been confirmed for the volunteering <strong>Foo</strong>.",
        ),
    ],
)
@pytest.mark.django_db
def test_confirmation_template_has_correct_text_per_event_type(
    user_api_client,
    event_type,
    expected_heading,
    expected_text,
    languages,
    registration,
    user,
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.event.type_id = event_type
    registration.event.name = "Foo"
    registration.event.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "service_language": "en",
        },
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = assert_create_signups(user_api_client, signups_data)
    assert signup_data["first_name"] in response.data[0]["first_name"]

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
    user_api_client,
    confirmation_message,
    languages,
    registration,
    service_language,
    user,
):
    user.get_default_organization().registration_admin_users.add(user)

    Language.objects.get_or_create(
        id=service_language, defaults={"name": service_language}
    )

    registration.confirmation_message_en = "Confirmation message"
    registration.confirmation_message_fi = "Vahvistusviesti"
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "service_language": service_language,
        },
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    assert_create_signups(user_api_client, signups_data)
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
    user_api_client,
    expected_subject,
    expected_text,
    languages,
    registration,
    service_language,
    signup,
    user,
):
    user.get_default_organization().registration_admin_users.add(user)

    with translation.override(service_language):
        registration.event.type_id = Event.TypeId.GENERAL
        registration.event.name = "Foo"
        registration.event.save()
        registration.maximum_attendee_capacity = 1
        registration.save()
        reservation = SeatReservationCodeFactory(registration=registration, seats=1)
        signup_data = {
            "first_name": "Michael",
            "last_name": "Jackson",
            "contact_person": {
                "email": test_email1,
                "service_language": service_language,
            },
        }
        signups_data = {
            "registration": registration.id,
            "reservation_code": reservation.code,
            "signups": [signup_data],
        }

        response = assert_create_signups(user_api_client, signups_data)
        assert signup_data["first_name"] in response.data[0]["first_name"]

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
    user_api_client,
    event_type,
    expected_text,
    languages,
    registration,
    signup,
    user,
):
    user.get_default_organization().registration_admin_users.add(user)

    registration.event.type_id = event_type
    registration.event.name = "Foo"
    registration.event.save()
    registration.maximum_attendee_capacity = 1
    registration.save()

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signup_data = {
        "first_name": "Michael",
        "last_name": "Jackson",
        "contact_person": {
            "email": test_email1,
            "service_language": "en",
        },
    }
    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [signup_data],
    }

    response = assert_create_signups(user_api_client, signups_data)
    assert signup_data["first_name"] in response.data[0]["first_name"]
    #  assert that the email was sent
    assert expected_text in str(mail.outbox[0].alternatives[0])


@pytest.mark.django_db
def test_signup_text_fields_are_sanitized(
    languages, organization, user, user_api_client
):
    user.get_default_organization().registration_admin_users.add(user)

    reservation = SeatReservationCodeFactory(seats=1)
    signups_data = {
        "registration": reservation.registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "Michael <p>Html</p>",
                "last_name": "Jackson <p>Html</p>",
                "extra_info": "Extra info <p>Html</p>",
                "street_address": f"{test_street_address} <p>Html</p>",
                "zipcode": "<p>zip</p>",
                "contact_person": {
                    "phone_number": "<p>0441111111</p>",
                },
            }
        ],
    }

    response = assert_create_signups(user_api_client, signups_data)
    response_signup = response.data[0]
    assert response_signup["first_name"] == "Michael Html"
    assert response_signup["last_name"] == "Jackson Html"
    assert response_signup["extra_info"] == "Extra info Html"
    assert response_signup["contact_person"]["phone_number"] == "0441111111"
    assert response_signup["street_address"] == f"{test_street_address} Html"
    assert response_signup["zipcode"] == "zip"


@pytest.mark.django_db
def test_signup_id_is_audit_logged_on_post(api_client, registration):
    LanguageFactory(pk="fi", service_language=True)

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    signups_data = default_signups_data
    signups_data["registration"] = registration.id
    signups_data["reservation_code"] = reservation.code

    user = UserFactory()
    user.registration_admin_organizations.add(registration.publisher)
    api_client.force_authenticate(user)

    response = assert_create_signups(api_client, signups_data)

    audit_log_entry = AuditLogEntry.objects.first()
    assert audit_log_entry.message["audit_event"]["target"]["object_ids"] == [
        response.data[0]["id"]
    ]


@pytest.mark.parametrize(
    "user_role",
    ["superuser", "admin", "registration_admin", "financial_admin", "regular_user"],
)
@pytest.mark.django_db
def test_can_create_signup_with_price_group(api_client, registration, user_role):
    user = create_user_by_role(user_role, registration.publisher)
    api_client.force_authenticate(user)

    LanguageFactory(id="fi", service_language=True)
    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    registration_price_group = RegistrationPriceGroupFactory(
        registration=registration, price_group__publisher=registration.publisher
    )

    signups_data = deepcopy(default_signups_data)
    signups_data["registration"] = registration.id
    signups_data["reservation_code"] = reservation.code
    signups_data["signups"][0]["price_group"] = {
        "registration_price_group": registration_price_group.pk
    }

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0

    assert_create_signups(api_client, signups_data)

    assert SignUp.objects.count() == 1
    assert SignUpPriceGroup.objects.count() == 1

    price_group = SignUpPriceGroup.objects.first()
    assert price_group.signup_id == SignUp.objects.first().pk
    assert price_group.registration_price_group_id == registration_price_group.pk
    assert price_group.price == registration_price_group.price
    assert price_group.vat_percentage == registration_price_group.vat_percentage
    assert price_group.price_without_vat == registration_price_group.price_without_vat
    assert price_group.vat == registration_price_group.vat
    for description_field in description_fields:
        assert getattr(price_group, description_field) == getattr(
            registration_price_group.price_group, description_field
        )


@pytest.mark.django_db
def test_can_create_signups_with_the_same_registration_price_group(
    api_client, registration
):
    user = create_user_by_role("registration_admin", registration.publisher)
    api_client.force_authenticate(user)

    LanguageFactory(id="fi", service_language=True)
    reservation = SeatReservationCodeFactory(registration=registration, seats=2)
    registration_price_group = RegistrationPriceGroupFactory(
        registration=registration, price_group__publisher=registration.publisher
    )

    signups_data = {
        "registration": registration.id,
        "reservation_code": reservation.code,
        "signups": [
            {
                "first_name": "Mickey",
                "last_name": "Mouse",
                "attendee_status": SignUp.AttendeeStatus.ATTENDING,
                "price_group": {
                    "registration_price_group": registration_price_group.pk,
                },
            },
            {
                "first_name": "Donald",
                "last_name": "Duck",
                "attendee_status": SignUp.AttendeeStatus.ATTENDING,
                "price_group": {
                    "registration_price_group": registration_price_group.pk,
                },
            },
        ],
    }

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0

    assert_create_signups(api_client, signups_data)

    assert SignUp.objects.count() == 2
    assert SignUpPriceGroup.objects.count() == 2

    common_kwargs = {
        "registration_price_group": registration_price_group.pk,
        "description_fi": registration_price_group.price_group.description_fi,
        "description_sv": registration_price_group.price_group.description_sv,
        "description_en": registration_price_group.price_group.description_en,
        "price": registration_price_group.price,
        "vat_percentage": registration_price_group.vat_percentage,
        "price_without_vat": registration_price_group.price_without_vat,
        "vat": registration_price_group.vat,
    }
    assert (
        SignUpPriceGroup.objects.filter(
            signup__first_name=signups_data["signups"][0]["first_name"], **common_kwargs
        ).count()
        == 1
    )
    assert (
        SignUpPriceGroup.objects.filter(
            signup__first_name=signups_data["signups"][1]["first_name"], **common_kwargs
        ).count()
        == 1
    )


@pytest.mark.parametrize(
    "user_role",
    ["superuser", "admin", "registration_admin", "financial_admin", "regular_user"],
)
@pytest.mark.django_db
def test_cannot_create_signup_with_another_registrations_price_group(
    api_client, registration, registration2, languages, user_role
):
    user = create_user_by_role(user_role, registration.publisher)
    api_client.force_authenticate(user)

    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    registration_price_group = RegistrationPriceGroupFactory(
        registration=registration2, price_group__publisher=registration2.publisher
    )

    signups_data = deepcopy(default_signups_data)
    signups_data["registration"] = registration.id
    signups_data["reservation_code"] = reservation.code
    signups_data["signups"][0]["price_group"] = {
        "registration_price_group": registration_price_group.pk
    }

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0

    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["signups"][0]["price_group"][0] == (
        "Price group is not one of the allowed price groups for this registration."
    )

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0


@pytest.mark.parametrize(
    "user_role",
    ["superuser", "admin", "registration_admin", "financial_admin", "regular_user"],
)
@pytest.mark.django_db
def test_cannot_create_signup_without_price_group_if_registration_has_price_groups(
    api_client, registration, user_role
):
    user = create_user_by_role(user_role, registration.publisher)
    api_client.force_authenticate(user)

    LanguageFactory(id="fi", service_language=True)
    reservation = SeatReservationCodeFactory(registration=registration, seats=1)
    RegistrationPriceGroupFactory(
        registration=registration, price_group__publisher=registration.publisher
    )

    signups_data = deepcopy(default_signups_data)
    signups_data["registration"] = registration.id
    signups_data["reservation_code"] = reservation.code

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0

    response = create_signups(api_client, signups_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["signups"][0]["price_group"][0] == (
        "Price group selection is mandatory for this registration."
    )

    assert SignUp.objects.count() == 0
    assert SignUpPriceGroup.objects.count() == 0
