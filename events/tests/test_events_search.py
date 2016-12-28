#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
import haystack
import datetime
from .utils import versioned_reverse as reverse
from haystack.management.commands import rebuild_index, clear_index
from rest_framework.test import APIClient

from ..models import Event

from .common import TestDataMixin


# Make sure we don't overwrite our main indices
for key, val in settings.HAYSTACK_CONNECTIONS.items():
    if 'INDEX_NAME' in val:
        val['INDEX_NAME'] = 'test_%s' % val['INDEX_NAME']


class EventSearchTests(TestCase, TestDataMixin):

    def setUp(self):
        self.client = APIClient()
        self.set_up_test_data()

        # setup haystack
        haystack.connections.reload('default')
        haystack.connections.reload('default-fi')
        haystack.connections.reload('default-en')
        haystack.connections.reload('default-sv')

        # create a dummy event
        self.dummy = Event(id='dummy_event',
                           name='dummy event',
                           data_source=self.test_ds,
                           publisher=self.test_org,
                           start_time=datetime.datetime.now(),
                           end_time=datetime.datetime.now()
        )
        self.dummy.save()

        # refresh haystack's index
        rebuild_index.Command().handle(interactive=False)

        super(EventSearchTests, self).setUp()

    def _get_response(self, query):
        return self.client.get('/v1/search/', {'q': query}, format='json')

    def test__search_should_respond(self):
        response = self._get_response('a random search query')
        self.assertEquals(response.status_code, 200, msg=response.content)

    def test__search_should_return_at_least_one_match(self):
        query = self.dummy.name.split()[0]  # let's use just the first word
        response = self._get_response(query)

        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertTrue(response.data['meta']['count'] >= 1)

    def test__search_shouldnt_return_matches(self):
        response = self._get_response('ASearchQueryThatShouldntReturnMatches')
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertTrue(response.data['meta']['count'] == 0)

    def test__event_endpoint_search(self):
        # another event that should not be returned
        Event.objects.create(
            id='another',
            name='another',
            data_source=self.test_ds,
            publisher=self.test_org,
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
        )

        query = self.dummy.name.split()[0]

        # normal query
        response = self.client.get('/v1/event/', {'q': query}, format='json')
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['id'], self.dummy.id)

        # autocomplete
        response = self.client.get('/v1/event/', {'input': query}, format='json')
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['id'], self.dummy.id)

        # filter existing value
        response = self.client.get('/v1/event/', {'q': query, 'data_source': self.test_ds.name}, format='json')
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['id'], self.dummy.id)

        # filter non existing value
        response = self.client.get('/v1/event/', {'q': query, 'data_source': 'bogus_ds'}, format='json')
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertEqual(response.data['meta']['count'], 0)

    def tearDown(self):
        # delete dummy
        self.dummy.delete()

        # clear index
        clear_index.Command().handle(interactive=False)
