import json

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from .support import PatchMixin


class TestSources(PatchMixin, TestCase):

    def setUp(self):
        self.login()
        self.requests_mock = self.patch('frontend.views.sources.requests')

    def assert_post_to_api(self, data):
        self.requests_mock.post.assert_called_with(
            settings.SOURCES_ENDPOINT,
            data=json.dumps({'sources': [data]}),
            headers={'X-ODE-Producer-Id': self.user.pk,
                     'Content-Type': 'application/json'},
        )

    def login(self):
        username, password = 'bob', 'foobar'
        self.user = User.objects.create_user(username, password=password)
        login_result = self.client.login(username=username, password=password)
        self.assertTrue(login_result)

    def test_source_form(self):
        response = self.client.get('/sources/create')
        self.assertContains(response, '<form action="/sources/create"')
        self.assertNotContains(response, 'error')

    def test_create_valid_source(self):
        sample_data = {
            'url': 'http://example.com/foo',
        }

        response = self.client.post('/sources/create', sample_data,
                                    follow=True)

        self.assert_post_to_api(sample_data)
        self.assertContains(response, 'success')

    def test_create_invalid_source(self):
        sample_data = {
            'url': '*** invalid url ***',
        }
        response_mock = self.requests_mock.post.return_value
        response_mock.json.return_value = {
            "status": "error",
            "errors": [{
                "location": "body",
                "name": "sources.0.url",
                "description": "The error message"
            }]
        }

        response = self.client.post('/sources/create', sample_data,
                                    follow=True)

        self.assert_post_to_api(sample_data)
        self.assertContains(response, 'class="errors"')
        self.assertContains(response, u'The error message')

    def test_source_list(self):
        response_mock = self.requests_mock.get.return_value
        response_mock.json.return_value = {
            "sources": [
                {
                    "id": 1,
                    "url": "http://example.com/source1",
                },
                {
                    "id": 2,
                    "url": "http://example.com/source2",
                },
            ]
        }

        response = self.client.get('/sources')

        self.requests_mock.get.assert_called_with(
            settings.SOURCES_ENDPOINT,
            headers={'X-ODE-Producer-Id': self.user.pk,
                     'Accept': 'application/json'})
        self.assertContains(response, "http://example.com/source1")
        self.assertContains(response, "http://example.com/source2")
        self.assertNotContains(
            response, "success",
            msg_prefix="not a redirect from an edition form")