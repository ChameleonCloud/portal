from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from .forms import TicketGuestForm
from django import forms


class TicketGuestFormTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_request_with_session(self):
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_form_init_unbound(self):
        """Test that an unbound form initializes the session with captcha data."""
        request = self.get_request_with_session()
        form = TicketGuestForm(request=request)

        self.assertIn("captcha_expected_sum", request.session)
        self.assertIn("captcha_question", request.session)

        question = request.session["captcha_question"]
        self.assertEqual(form.fields["captcha_answer"].label, question)

    def test_form_init_bound(self):
        """Test that a bound form uses the stored question for the label."""
        request = self.get_request_with_session()
        # Pre-populate session
        request.session["captcha_question"] = "What is 1 + 1?"
        request.session["captcha_expected_sum"] = 2
        request.session.save()

        form = TicketGuestForm(data={}, request=request)
        self.assertEqual(form.fields["captcha_answer"].label, "What is 1 + 1?")

    def test_clean_captcha_correct(self):
        """Test correct captcha answer."""
        request = self.get_request_with_session()
        request.session["captcha_expected_sum"] = 5
        request.session.save()

        data = {"captcha_answer": 5}
        form = TicketGuestForm(data=data, request=request)

        # We manually clean just this field to avoid other field validation errors (like ReCaptcha)
        form.cleaned_data = data
        try:
            result = form.clean_captcha_answer()
            self.assertEqual(result, 5)
        except forms.ValidationError:
            self.fail("clean_captcha_answer raised ValidationError unexpectedly!")

    def test_clean_captcha_incorrect(self):
        """Test incorrect captcha answer."""
        request = self.get_request_with_session()
        request.session["captcha_expected_sum"] = 5
        request.session.save()

        data = {"captcha_answer": 3}
        form = TicketGuestForm(data=data, request=request)

        form.cleaned_data = data
        with self.assertRaises(forms.ValidationError) as cm:
            form.clean_captcha_answer()
        self.assertEqual(
            str(cm.exception.message), "Incorrect answer, please try again."
        )

    def test_clean_captcha_no_session(self):
        """Test validation when session data is missing."""
        request = self.get_request_with_session()
        # Don't populate session

        data = {"captcha_answer": 5}
        form = TicketGuestForm(data=data, request=request)

        form.cleaned_data = data
        with self.assertRaises(forms.ValidationError) as cm:
            form.clean_captcha_answer()
        self.assertEqual(
            str(cm.exception.message), "Session expired, please refresh the page."
        )
