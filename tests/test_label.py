from django.test import TestCase

from ..models import Label

class LabelStringTest(TestCase):
    def test_to_string(self):
        l = Label.objects.create(label='label1')
        self.assertEqual(str(l), l.label)
