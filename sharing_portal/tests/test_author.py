from django.test import TestCase

from ..models import Author


class AuthorStringTest(TestCase):
    def test_to_string(self):
        author = Author.objects.create(
            name='Albert Einstein',
        )
        self.assertEqual(str(author), 'Albert Einstein')

    def test_with_affiliation(self):
        author = Author.objects.create(
            name='Albert Einstein',
            affiliation='Physicist',
        )
        self.assertEqual(str(author), 'Albert Einstein (Physicist)')
