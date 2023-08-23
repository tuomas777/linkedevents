import logging
from smtplib import SMTPException

import bleach
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.db.models import ProtectedError, Q, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from events.api import (
    _filter_event_queryset,
    JSONAPIViewMixin,
    RegistrationSerializer,
    UserDataSourceAndOrganizationMixin,
)
from events.models import Event
from events.permissions import (
    DataSourceResourceEditPermission,
    OrganizationUserEditPermission,
)
from linkedevents.registry import register_view
from registrations.exceptions import ConflictException
from registrations.models import (
    Registration,
    RegistrationUserAccess,
    SeatReservationCode,
    SignUp,
    SignUpGroup,
)
from registrations.permissions import CanAccessRegistration, CanAccessSignup
from registrations.serializers import (
    CreateSignUpsSerializer,
    MassEmailSerializer,
    RegistrationUserAccessSerializer,
    SeatReservationCodeSerializer,
    SignUpGroupCreateSerializer,
    SignUpGroupSerializer,
    SignUpSerializer,
)
from registrations.utils import send_mass_html_mail

logger = logging.getLogger(__name__)


class RegistrationViewSet(
    UserDataSourceAndOrganizationMixin,
    JSONAPIViewMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = RegistrationSerializer
    queryset = Registration.objects.all()

    permission_classes = [CanAccessRegistration & DataSourceResourceEditPermission]

    def perform_create(self, serializer):
        # Check object level permissions for event which has the relevant data_source.
        event = serializer.validated_data.get("event")
        self.check_object_permissions(self.request, event)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        # Check object level permissions for event which has the relevant data_source.
        event = serializer.validated_data.get("event", serializer.instance.event)
        self.check_object_permissions(self.request, event)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        # At the moment ProtecterError is raised only if user tries to remove registration with signups.
        # Add logic to handle protected errors if more proteted fks are added in the future.
        except ProtectedError:
            raise ConflictException(_("Registration with signups cannot be deleted"))

    def filter_queryset(self, queryset):
        events = Event.objects.exclude(registration=None)

        # Copy query_params to get mutable version of it
        query_params = self.request.query_params.copy()
        # By default _filter_event_queryset only returns events with GENERAL type.
        # This causes problem when getting a registration details, so filter registrations
        # by event_type only when explicitly set
        if not query_params.get("event_type"):
            event_types = {k[1].lower(): k[0] for k in Event.TYPE_IDS}
            query_params["event_type"] = ",".join(event_types.keys())

        events = _filter_event_queryset(events, query_params)

        val = self.request.query_params.get("admin_user", None)
        if val and str(val).lower() == "true":
            if isinstance(self.request.user, AnonymousUser):
                events = Event.objects.none()
            else:
                events = self.request.user.get_editable_events(events)
        registrations = Registration.objects.filter(event__in=events)

        return registrations

    def get_serializer_class(self):
        if self.action == "send_message":
            return MassEmailSerializer
        return super().get_serializer_class()

    @action(
        methods=["post"],
        detail=True,
        permission_classes=[CanAccessRegistration & DataSourceResourceEditPermission],
    )
    def send_message(self, request, pk=None, version=None):
        registration = self.get_object()

        data = request.data
        data["registration"] = registration
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        signups = serializer.validated_data.get(
            "signups", registration.signups.exclude(email=None)
        )

        messages = []
        body = serializer.validated_data["body"]
        subject = serializer.validated_data["subject"]
        cleaned_body = bleach.clean(
            body.replace("\n", "<br>"), settings.BLEACH_ALLOWED_TAGS
        )
        plain_text_body = bleach.clean(body, strip=True)

        # Make personal email for each signup that:
        # - is responsible for a group
        # - belongs to a group with no responsible signups
        # - does not belong to a group
        for signup in signups:
            if (
                signup.signup_group_id
                and (
                    signup.responsible_for_group
                    or not signup.signup_group.responsible_signups
                )
                or not signup.signup_group_id
            ):
                message = signup.get_registration_message(
                    subject, cleaned_body, plain_text_body
                )
                messages.append(message)

        try:
            send_mass_html_mail(messages, fail_silently=False)
        except SMTPException as e:
            logger.exception("Couldn't send mass HTML email.")

            return Response(
                str(e),
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "html_message": cleaned_body,
                "message": plain_text_body,
                "signups": [su.id for su in signups],
                "subject": subject,
            },
            status=status.HTTP_200_OK,
        )


register_view(RegistrationViewSet, "registration")


class RegistrationUserAccessViewSet(viewsets.GenericViewSet):
    queryset = RegistrationUserAccess.objects.all()
    serializer_class = RegistrationUserAccessSerializer
    permission_classes = [OrganizationUserEditPermission]

    @action(detail=True, methods=["post"])
    def send_invitation(self, request, pk=None, version=None):
        registration_user_access = self.get_object()
        registration_user_access.send_invitation()
        return Response(
            status=status.HTTP_200_OK,
        )


register_view(RegistrationUserAccessViewSet, "registration_user_access")


class SignUpViewSet(
    UserDataSourceAndOrganizationMixin,
    viewsets.ModelViewSet,
):
    serializer_class = SignUpSerializer
    queryset = SignUp.objects.all()
    permission_classes = [CanAccessSignup & DataSourceResourceEditPermission]

    def create(self, request, *args, **kwargs):
        context = super().get_serializer_context()
        data = request.data
        registration = data.get("registration", None)
        if registration:
            for i in data["signups"]:
                i["registration"] = registration
        serializer = CreateSignUpsSerializer(data=data, context=context)
        serializer.is_valid(raise_exception=True)

        attending = []
        waitlisted = []

        # Create SignUps and add persons to correct list
        for i in data["signups"]:
            signup = SignUpSerializer(data=i, context=context)
            signup.is_valid()
            signee = signup.create(validated_data=signup.validated_data)

            if signee.attendee_status == SignUp.AttendeeStatus.ATTENDING:
                attending.append(SignUpSerializer(signee, context=context).data)
            else:
                waitlisted.append(SignUpSerializer(signee, context=context).data)
        data = {
            "attending": {"count": len(attending), "people": attending},
            "waitlisted": {"count": len(waitlisted), "people": waitlisted},
        }

        # Delete reservation
        reservation = serializer.validated_data["reservation"]
        reservation.delete()

        return Response(data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance._individually_deleted = True
        instance.delete()

    def filter_queryset(self, queryset):
        request = self.request
        user = request.user

        if registration_param := request.query_params.get("registration", None):
            registrations = []
            # Get registration admin organizations and descendants only
            # once instead of using is_registration_admin_of method.
            registration_admin_orgs = (
                user.get_registration_admin_organizations_and_descendants()
            )

            for pk in registration_param.split(","):
                try:
                    registration = Registration.objects.get(pk=pk)
                except (ValueError, Registration.DoesNotExist):
                    raise ParseError(
                        _("Registration with id {pk} doesn't exist.").format(pk=pk)
                    )

                if not (
                    user.is_superuser
                    or user.is_strongly_identificated
                    and registration.registration_user_accesses.filter(
                        email=user.email
                    ).exists()
                    or registration.publisher in registration_admin_orgs
                ):
                    raise DRFPermissionDenied(
                        _(
                            "Only the admins of the organization {organization} have access rights."
                        ).format(organization=registration.publisher)
                    )

                registrations.append(registration)
            queryset = queryset.filter(registration__in=registrations)
        elif self.action == "list" and not user.is_superuser:
            # By default, return only signups of registrations to which
            # user has admin rights or is registration user that is
            # strongly identified.
            list_filter = Q(
                registration__event__publisher__in=user.get_registration_admin_organizations_and_descendants()
            )
            if user.is_strongly_identificated:
                list_filter |= Q(
                    registration__registration_user_accesses__email=user.email
                )
            queryset = queryset.filter(list_filter)

        if text_param := request.query_params.get("text", None):
            queryset = queryset.annotate(
                first_last_name=Concat("first_name", Value(" "), "last_name"),
                last_first_name=Concat("last_name", Value(" "), "first_name"),
            ).filter(
                Q(first_last_name__icontains=text_param)
                | Q(last_first_name__icontains=text_param)
                | Q(email__icontains=text_param)
                | Q(extra_info__icontains=text_param)
                | Q(membership_number__icontains=text_param)
                | Q(phone_number__icontains=text_param)
            )

        if status_param := request.query_params.get("attendee_status", None):
            vals = status_param.lower().split(",")
            statuses = [k[0] for k in SignUp.ATTENDEE_STATUSES]

            for v in vals:
                if v not in statuses:
                    raise ParseError(
                        _(
                            "attendee_status can take following values: {statuses}, not {val}"
                        ).format(statuses=", ".join(statuses), val=status_param)
                    )

            queryset = queryset.filter(attendee_status__in=vals)

        return queryset


register_view(SignUpViewSet, "signup")


class SignUpGroupViewSet(
    UserDataSourceAndOrganizationMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SignUpGroupSerializer
    queryset = SignUpGroup.objects.all()
    permission_classes = [CanAccessSignup & DataSourceResourceEditPermission]

    def get_serializer_class(self):
        if self.action == "create":
            return SignUpGroupCreateSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        registration = data.get("registration")
        if registration and data.get("signups"):
            for signup_data in data["signups"]:
                signup_data["registration"] = registration
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


register_view(SignUpGroupViewSet, "signup_group")


class SeatReservationViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SeatReservationCodeSerializer
    queryset = SeatReservationCode.objects.all()
    permission_classes = []


register_view(SeatReservationViewSet, "seats_reservation")
