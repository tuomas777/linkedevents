from datetime import timedelta

import pytz
from django.utils.timezone import localdate, localtime
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.fields import DateTimeField

from events.models import Language
from registrations.exceptions import ConflictException
from registrations.models import (
    Registration,
    RegistrationUserAccess,
    SeatReservationCode,
    SignUp,
    SignUpGroup,
    SignUpNotificationType,
)
from registrations.utils import code_validity_duration


def validate_registration_enrolment_times(registration):
    enrolment_start_time = registration.enrolment_start_time
    enrolment_end_time = registration.enrolment_end_time
    current_time = localtime()

    if enrolment_start_time and current_time < enrolment_start_time:
        raise ConflictException(_("Enrolment is not yet open."))
    if enrolment_end_time and current_time > enrolment_end_time:
        raise ConflictException(_("Enrolment is already closed."))


class SignUpSerializer(serializers.ModelSerializer):
    view_name = "signup"
    id = serializers.IntegerField(required=False)
    service_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.filter(service_language=True),
        many=False,
        required=False,
    )

    created_at = DateTimeField(
        default_timezone=pytz.UTC, required=False, allow_null=True
    )
    last_modified_at = DateTimeField(
        default_timezone=pytz.UTC, required=False, allow_null=True
    )

    created_by = serializers.StringRelatedField(required=False, allow_null=True)
    last_modified_by = serializers.StringRelatedField(required=False, allow_null=True)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user

        registration = validated_data["registration"]
        already_attending = SignUp.objects.filter(
            registration=registration, attendee_status=SignUp.AttendeeStatus.ATTENDING
        ).count()
        already_waitlisted = SignUp.objects.filter(
            registration=registration,
            attendee_status=SignUp.AttendeeStatus.WAITING_LIST,
        ).count()
        attendee_capacity = registration.maximum_attendee_capacity
        waiting_list_capacity = registration.waiting_list_capacity

        if (attendee_capacity is None) or (already_attending < attendee_capacity):
            signup = super().create(validated_data)
            if signup.responsible_for_group or not signup.signup_group_id:
                signup.send_notification(SignUpNotificationType.CONFIRMATION)
            return signup
        elif (waiting_list_capacity is None) or (
            already_waitlisted < waiting_list_capacity
        ):
            validated_data["attendee_status"] = SignUp.AttendeeStatus.WAITING_LIST
            signup = super().create(validated_data)
            if signup.responsible_for_group or not signup.signup_group_id:
                signup.send_notification(
                    SignUpNotificationType.CONFIRMATION_TO_WAITING_LIST
                )
            return signup
        else:
            raise DRFPermissionDenied(_("The waiting list is already full"))

    def update(self, instance, validated_data):
        errors = {}

        if (
            "attendee_status" in validated_data
            and instance.attendee_status != validated_data["attendee_status"]
        ):
            errors["attendee_status"] = _(
                "You may not change the attendee_status of an existing object."
            )
        if (
            "registration" in validated_data
            and instance.registration != validated_data["registration"]
        ):
            errors["registration"] = _(
                "You may not change the registration of an existing object."
            )

        if errors:
            raise serializers.ValidationError(errors)

        validated_data["last_modified_by"] = self.context["request"].user
        super().update(instance, validated_data)
        return instance

    def validate(self, data):
        errors = {}

        if isinstance(self.instance, SignUp):
            registration = self.instance.registration
        else:
            registration = data["registration"]

        falsy_values = ("", None)

        # Validate mandatory fields
        for field in registration.mandatory_fields:
            # Don't validate field if request method is PATCH and field is missing from the payload
            if self.partial and field not in data.keys():
                continue
            elif data.get(field) in falsy_values:
                errors[field] = _("This field must be specified.")

        # Validate date_of_birth if audience_min_age or registration.audience_max_age is defined
        # Don't validate date_of_birth if request method is PATCH and field is missing from the payload
        if (
            registration.audience_min_age not in falsy_values
            or registration.audience_max_age not in falsy_values
        ) and not (self.partial and "date_of_birth" not in data.keys()):
            date_of_birth = data.get("date_of_birth")

            if date_of_birth in falsy_values:
                errors["date_of_birth"] = _("This field must be specified.")
            else:
                today = localdate()
                current_age = (
                    today.year
                    - date_of_birth.year
                    - (
                        (today.month, today.day)
                        < (date_of_birth.month, date_of_birth.year)
                    )
                )
                if (
                    registration.audience_min_age
                    and current_age < registration.audience_min_age
                ):
                    errors["date_of_birth"] = _("The participant is too young.")
                elif (
                    registration.audience_max_age
                    and current_age > registration.audience_max_age
                ):
                    errors["date_of_birth"] = _("The participant is too old.")

        if errors:
            raise serializers.ValidationError(errors)

        super().validate(data)
        return data

    class Meta:
        fields = "__all__"
        model = SignUp


class RegistrationUserAccessIdField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        registration_id = self.context["request"].parser_context["kwargs"]["pk"]
        return RegistrationUserAccess.objects.filter(registration__pk=registration_id)


class RegistrationUserAccessSerializer(serializers.ModelSerializer):
    id = RegistrationUserAccessIdField(required=False, allow_null=True)

    language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.filter(service_language=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = RegistrationUserAccess
        fields = ["id", "email", "language"]


# Don't use this serializer directly but use events.api.RegistrationSerializer instead.
# Implement methods to mutate and validate Registration in events.api.RegistrationSerializer
class RegistrationBaseSerializer(serializers.ModelSerializer):
    view_name = "registration-detail"

    signups = serializers.SerializerMethodField()

    current_attendee_count = serializers.SerializerMethodField()

    current_waiting_list_count = serializers.SerializerMethodField()

    remaining_attendee_capacity = serializers.SerializerMethodField()

    remaining_waiting_list_capacity = serializers.SerializerMethodField()

    data_source = serializers.SerializerMethodField()

    publisher = serializers.SerializerMethodField()

    registration_user_accesses = RegistrationUserAccessSerializer(
        many=True, required=False
    )

    created_time = DateTimeField(
        default_timezone=pytz.UTC, required=False, allow_null=True
    )

    last_modified_time = DateTimeField(
        default_timezone=pytz.UTC, required=False, allow_null=True
    )

    created_by = serializers.StringRelatedField(required=False, allow_null=True)

    last_modified_by = serializers.StringRelatedField(required=False, allow_null=True)

    def get_signups(self, obj):
        params = self.context["request"].query_params

        if "signups" in params.get("include", "").split(","):
            # Only organization registration admins or the registration user
            # should be able to access the signup information.
            user = self.context["user"]
            if user.is_authenticated and (
                user.is_superuser
                or user.is_registration_admin_of(obj.event.publisher)
                or user.is_strongly_identificated
                and obj.registration_user_accesses.filter(email=user.email).exists()
            ):
                signups = obj.signups.all()
                return SignUpSerializer(signups, many=True, read_only=True).data

        return None

    def get_current_attendee_count(self, obj):
        return obj.current_attendee_count

    def get_current_waiting_list_count(self, obj):
        return obj.current_waiting_list_count

    def get_remaining_attendee_capacity(self, obj):
        return obj.remaining_attendee_capacity

    def get_remaining_waiting_list_capacity(self, obj):
        return obj.remaining_waiting_list_capacity

    def get_data_source(self, obj):
        return obj.data_source.id

    def get_publisher(self, obj):
        return obj.publisher.id

    class Meta:
        fields = "__all__"
        model = Registration


class CreateSignUpsSerializer(serializers.Serializer):
    reservation_code = serializers.CharField()
    registration = serializers.PrimaryKeyRelatedField(
        queryset=Registration.objects.all(),
        many=False,
        required=True,
    )
    signups = SignUpSerializer(many=True, required=True)

    def validate(self, data):
        reservation_code = data["reservation_code"]
        registration = data["registration"]

        # Prevent to signup if enrolment is not open.
        # Raises 409 error if enrolment is not open
        validate_registration_enrolment_times(registration)

        try:
            reservation = SeatReservationCode.objects.get(
                code=reservation_code, registration=registration
            )
            data["reservation"] = reservation
        except SeatReservationCode.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "reservation_code": ErrorDetail(
                        _("Reservation code doesn't exist."),
                        code="does_not_exist",
                    )
                }
            )

        expiration = reservation.timestamp + timedelta(
            minutes=code_validity_duration(reservation.seats)
        )
        if localtime() > expiration:
            raise serializers.ValidationError(
                {"reservation_code": "Reservation code has expired."}
            )

        maximum_group_size = registration.maximum_group_size

        # Validate maximum group size
        if maximum_group_size is not None and len(data["signups"]) > maximum_group_size:
            raise serializers.ValidationError(
                {
                    "signups": ErrorDetail(
                        _(
                            "Amount of signups is greater than maximum group size: {max_group_size}."
                        ).format(max_group_size=maximum_group_size),
                        code="max_group_size",
                    )
                }
            )

        if len(data["signups"]) > reservation.seats:
            raise serializers.ValidationError(
                {"signups": "Number of signups exceeds the number of requested seats"}
            )
        data = super().validate(data)
        return data


class SignUpGroupCreateSerializer(serializers.ModelSerializer, CreateSignUpsSerializer):
    reservation_code = serializers.CharField(write_only=True)

    def _create_signups(self, instance, validated_signups_data):
        for signup_data in validated_signups_data:
            signup_data["signup_group"] = instance
            signup_serializer = SignUpSerializer(data=signup_data, context=self.context)
            signup_serializer.create(signup_data)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user

        validated_data.pop("reservation_code")
        reservation = validated_data.pop("reservation")
        signups_data = validated_data.pop("signups")

        instance = super().create(validated_data)
        self._create_signups(instance, signups_data)

        reservation.delete()

        return instance

    class Meta:
        fields = (
            "id",
            "registration",
            "signups",
            "reservation_code",
            "extra_info",
        )
        model = SignUpGroup


class SignUpGroupSerializer(serializers.ModelSerializer):
    view_name = "signupgroup-detail"

    def get_fields(self):
        fields = super().get_fields()
        fields["signups"] = SignUpSerializer(
            many=True, required=False, partial=self.partial
        )
        return fields

    def validate(self, data):
        validated_data = super().validate(data)

        errors = {}

        if (
            "registration" in validated_data
            and self.instance
            and self.instance.registration != validated_data["registration"]
        ):
            errors["registration"] = _(
                "You may not change the registration of an existing object."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return validated_data

    def _update_signups(self, instance, validated_signups_data):
        for signup_data in validated_signups_data:
            if not signup_data.get("id"):
                continue

            if not self.partial:
                signup_data["signup_group"] = instance

            signup = SignUp.objects.get(pk=signup_data["id"])
            signup_serializer = SignUpSerializer(
                instance=signup,
                data=signup_data,
                context=self.context,
                partial=self.partial,
            )
            signup_serializer.update(signup_serializer.instance, signup_data)

    def update(self, instance, validated_data):
        signups_data = validated_data.pop("signups", [])
        validated_data["last_modified_by"] = self.context["request"].user

        super().update(instance, validated_data)
        self._update_signups(instance, signups_data)

        return instance

    class Meta:
        fields = ("id", "registration", "signups", "extra_info")
        model = SignUpGroup


class SeatReservationCodeSerializer(serializers.ModelSerializer):
    seats = serializers.IntegerField(required=True)

    timestamp = DateTimeField(default_timezone=pytz.UTC, required=False, read_only=True)

    expiration = serializers.SerializerMethodField()

    in_waitlist = serializers.SerializerMethodField()

    def get_expiration(self, obj):
        return obj.expiration

    def get_in_waitlist(self, obj):
        registration = obj.registration
        maximum_attendee_capacity = registration.maximum_attendee_capacity

        if maximum_attendee_capacity is None:
            return False

        attendee_count = registration.signups.filter(
            attendee_status=SignUp.AttendeeStatus.ATTENDING
        ).count()

        return maximum_attendee_capacity - attendee_count <= 0

    def to_internal_value(self, data):
        if self.instance:
            data["registration"] = self.instance.registration.id
        return super().to_internal_value(data)

    def validate(self, data):
        instance = self.instance
        errors = {}

        if instance:
            # The code must be defined and match instance code when updating existing seats reservation
            if self.initial_data.get("code") is None:
                errors["code"] = ErrorDetail(
                    _("This field must be specified."), code="required"
                )
            elif str(instance.code) != self.initial_data["code"]:
                errors["code"] = _("The value doesn't match.")

            # Raise validation error if reservation code doesn't match
            if errors:
                raise serializers.ValidationError(errors)

        registration = data["registration"]

        # Prevent to reserve seats if enrolment is not open.
        # Raises 409 error if enrolment is not open
        validate_registration_enrolment_times(registration)

        maximum_group_size = registration.maximum_group_size

        # Validate maximum group size
        if maximum_group_size is not None and data["seats"] > maximum_group_size:
            errors["seats"] = ErrorDetail(
                _(
                    "Amount of seats is greater than maximum group size: {max_group_size}."
                ).format(max_group_size=maximum_group_size),
                code="max_group_size",
            )

        maximum_attendee_capacity = registration.maximum_attendee_capacity
        waiting_list_capacity = registration.waiting_list_capacity

        # Validate attendee capacity only if maximum_attendee_capacity is defined
        if maximum_attendee_capacity is not None:
            attendee_count = registration.current_attendee_count
            attendee_capacity_left = maximum_attendee_capacity - attendee_count

            if instance:
                reserved_seats_amount = max(
                    registration.reserved_seats_amount - instance.seats, 0
                )
            else:
                reserved_seats_amount = registration.reserved_seats_amount

            # Only allow to reserve seats to event if attendee capacity is not used
            if attendee_capacity_left > 0:
                # Prevent to reserve seats if all available seats are already reserved
                if data["seats"] > attendee_capacity_left - reserved_seats_amount:
                    errors["seats"] = _(
                        "Not enough seats available. Capacity left: {capacity_left}."
                    ).format(
                        capacity_left=max(
                            attendee_capacity_left - reserved_seats_amount, 0
                        )
                    )
            # Validate waiting list capacity only if waiting_list_capacity is defined and
            # and all seats in the event are used
            elif waiting_list_capacity is not None:
                waiting_list_count = registration.current_waiting_list_count
                waiting_list_capacity_left = waiting_list_capacity - waiting_list_count

                # Prevent to reserve seats to waiting ist if all available seats in waiting list
                # are already reserved
                if data["seats"] > waiting_list_capacity_left - reserved_seats_amount:
                    errors["seats"] = _(
                        "Not enough capacity in the waiting list. Capacity left: {capacity_left}."
                    ).format(
                        capacity_left=max(
                            waiting_list_capacity_left - reserved_seats_amount, 0
                        )
                    )

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(data)

    def update(self, instance, validated_data):
        if localtime() > instance.expiration:
            raise ConflictException(_("Cannot update expired seats reservation."))

        return super().update(instance, validated_data)

    class Meta:
        fields = (
            "id",
            "registration",
            "seats",
            "in_waitlist",
            "code",
            "timestamp",
            "expiration",
        )
        model = SeatReservationCode


class MassEmailSignupsField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        registration = self.context["request"].data["registration"]

        return registration.signups.exclude(email=None)


class MassEmailSerializer(serializers.Serializer):
    subject = serializers.CharField()
    body = serializers.CharField()
    signups = MassEmailSignupsField(
        many=True,
        required=False,
    )
