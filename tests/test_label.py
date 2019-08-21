import unittest

from ..models import Label

class LabelStringTest(unittest.TestCase):
    def test_to_string(self):
        l = Label.objects.create(label='label1')
        self.assertEqual(str(l), l.label)
