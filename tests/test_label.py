from django.test import TestCase

from ..models import Label


class LabelStringTest(TestCase):
    def test_to_string(self):
        l1 = Label.objects.create(label='label1')
        self.assertEqual(str(l1), l1.label)
