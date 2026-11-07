import re

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from apps.channels.models import Channel

User = get_user_model()


class SignupCsrfTests(TestCase):
    def test_signup_sets_csrf_cookie_and_accepts_a_valid_post(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("signup"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        token = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"', response.content
        ).group(1).decode()

        response = client.post(
            reverse("signup"),
            {
                "username": "csrf-signup-user",
                "email": "csrf-signup@example.test",
                "password1": "SafePassword-98765",
                "password2": "SafePassword-98765",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertEqual(response.status_code, 302)

    @override_settings(
        ALLOWED_HOSTS=["*"],
        CSRF_TRUSTED_ORIGINS=["http://192.168.10.103:3000"],
        CSRF_COOKIE_SECURE=False,
        CSRF_COOKIE_SAMESITE="Lax",
        SECURE_SSL_REDIRECT=False,
    )
    def test_signup_csrf_works_from_a_lan_ip(self):
        client = Client(enforce_csrf_checks=True)
        host = "192.168.10.103:3000"
        origin = "http://192.168.10.103:3000"
        response = client.get(reverse("signup"), HTTP_HOST=host)

        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        token = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"', response.content
        ).group(1).decode()

        response = client.post(
            reverse("signup"),
            {
                "username": "lan-csrf-signup-user",
                "email": "lan-csrf-signup@example.test",
                "password1": "SafePassword-98765",
                "password2": "SafePassword-98765",
                "csrfmiddlewaretoken": token,
            },
            HTTP_HOST=host,
            HTTP_ORIGIN=origin,
            HTTP_REFERER=origin + reverse("signup"),
        )

        self.assertEqual(response.status_code, 302)


class AccountAndChannelEditingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="account-editor", email="editor@example.test", password="SafePassword-4567", email_verified=True)
        cls.channel = Channel.objects.create(owner=cls.user, name="Initial Channel", slug="initial-channel", description="Before")

    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_email_change_resets_verification(self):
        response = self.client.post(reverse("settings"), {"first_name": "Sam", "email": "new@example.test", "bio": "Updated profile", "preferred_language": "en"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.test")
        self.assertEqual(self.user.first_name, "Sam")
        self.assertEqual(self.user.preferred_language, "en")
        self.assertFalse(self.user.email_verified)

    def test_channel_owner_can_edit_channel_name_description_and_slug(self):
        response = self.client.get(reverse("channel_setup"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("channel_setup"), {"name": "Renamed Channel", "description": "After"})
        self.assertEqual(response.status_code, 302)
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "Renamed Channel")
        self.assertEqual(self.channel.description, "After")
        self.assertEqual(self.channel.slug, "renamed-channel")
