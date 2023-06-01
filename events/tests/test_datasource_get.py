import pytest
from rest_framework import status

from events.tests.utils import versioned_reverse as reverse


def get_list(api_client):
    url = reverse("datasource-list")

    return api_client.get(url, format="json")


def assert_data_sources_in_response(response, data_sources):
    response_ids = {ds["id"] for ds in response.data["data"]}
    expected_ids = {ds.id for ds in data_sources}
    assert response_ids == expected_ids


def get_list_and_assert_data_sources(
    api_client,
    data_sources,
):
    response = get_list(api_client)
    assert response.status_code == status.HTTP_200_OK
    assert_data_sources_in_response(response, data_sources)


def get_detail(api_client, detail_pk):
    detail_url = reverse("datasource-detail", kwargs={"pk": detail_pk})
    return api_client.get(detail_url, format="json")


def assert_get_data_source(api_client, detail_pk):
    response = get_detail(api_client, detail_pk)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_admin_user_can_get_data_sources(api_client, data_source, organization, user):
    api_client.force_authenticate(user)

    get_list_and_assert_data_sources(api_client, [data_source])


@pytest.mark.django_db
def test_anonymous_user_cannot_get_data_sources(api_client, data_source):
    response = get_list(api_client)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_regular_user_cannot_get_data_sources(
    api_client, data_source, organization, user
):
    user.get_default_organization().regular_users.add(user)
    user.get_default_organization().admin_users.remove(user)
    api_client.force_authenticate(user)

    response = get_list(api_client)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test__api_key_user_can_get_data_sources(
    api_client, data_source, organization, other_data_source
):
    data_source.owner = organization
    data_source.save()
    api_client.credentials(apikey=data_source.api_key)

    get_list_and_assert_data_sources(api_client, [data_source, other_data_source])


@pytest.mark.django_db
def test__anonymous_user_can_retrieve_data_source(api_client, data_source):
    assert_get_data_source(api_client, data_source.id)
