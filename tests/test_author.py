import unittest

from ..models import Author

class AuthorStringTest(unittest.TestCase):
    def test_to_string(self):
        author = Author.objects.create(
            title='Mr.',
            first_name='Albert',
            last_name='Einstein',
        )
        author.full_name = "That man"
        self.assertEqual(str(author), "That man")

class AuthorFullNameTest(unittest.TestCase):
    def test_save(self):
        author = Author.objects.create(
            title='Mr.',
            first_name='Albert',
            last_name='Einstein',
        )
        author.save()
        self.assertEqual(author.full_name, "Mr. Albert Einstein")
