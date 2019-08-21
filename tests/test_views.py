from datetime import datetime
#import unittest

from django.test import TestCase

from ..models import Artifact, Author, Label
from ..views import artifacts_from_form


def sorted_list_ids(alist):
    new_list = list(map(lambda x: x.id, list(alist)))
    new_list.sort()
    return new_list

class ArtifactsFromFormTest(TestCase):
    def setUp(self):
        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact a is cool',
                    description="Apple",
                    short_description="a vowel",
                    created_at=now,
                    updated_at=now,
        )    
        self.b = Artifact.objects.create(
                    title='Test Case Artifact b',
                    description="Banana",
                    created_at=now,
                    updated_at=now,
        )    
        self.c = Artifact.objects.create(
                    title='Test Case Artifact c',
                    description="Carrot",
                    created_at=now,
                    updated_at=now,
        )    
        self.d = Artifact.objects.create(
                    title='Test Case Artifact d',
                    description="Dinosaur",
                    created_at=now,
                    updated_at=now,
        )    
        self.e = Artifact.objects.create(
                    title='Test Case Artifact e',
                    description="Elephant",
                    short_description="a vowel",
                    created_at=now,
                    updated_at=now,
        )    
        self.f = Artifact.objects.create(
                    title='cool Test Case Artifact f',
                    created_at=now,
                    updated_at=now,
        )    

        # Adding labels to their multiples
        self.label1 = Label.objects.create(label='label1')
        self.label2 = Label.objects.create(label='label2')
        self.label3 = Label.objects.create(label='label3')
        self.label4 = Label.objects.create(label='label4')
        self.label5 = Label.objects.create(label='label5')
        self.a.labels.set([self.label1])
        self.b.labels.set([self.label1, self.label2])
        self.c.labels.set([self.label1, self.label3])
        self.d.labels.set([self.label1, self.label4])
        self.e.labels.set([self.label1, self.label5])
        self.f.labels.set([self.label1, self.label2, self.label3])

        # Give Einstein's initials an author
        albert = Author.objects.create(
                    title="Mr.",
                    first_name="Albert",
                    last_name="Einstein"
        )
        self.a.authors.set([albert])
        self.e.authors.set([albert])

    def test_empty_label(self):
        data = {
            'labels': [800000000],
            'search': '',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([])
        self.assertEqual(filtered, goal)
        
    def test_duplicate_matches_or(self):
        data = {
            'labels': [self.label1.id, self.label2.id, self.label3.id],
            'search': '',
            'is_or': True
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a, self.b, self.c, self.d, self.e, self.f])
        self.assertEqual(filtered, goal)
        
    def test_some_partial_matches_and(self):
        data = {
            'labels': [self.label1.id, self.label3.id],
            'search': '',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.c, self.f])
        self.assertEqual(filtered, goal)
        
    def test_keywords_title(self):
        data = {
            'labels': [],
            'search': 'cool',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a, self.f])
        self.assertEqual(filtered, goal)
        
    def test_keywords_author(self):
        data = {
            'labels': [],
            'search': 'Albert Einstein',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a, self.e])
        self.assertEqual(filtered, goal)

    def test_keywords_desc(self):
        data = {
            'labels': [],
            'search': 'Apple',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a])
        self.assertEqual(filtered, goal)

    def test_keywords_short_desc_no_isor(self):
        data = {
            'labels': [],
            'search': 'voWel',
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a, self.e])
        self.assertEqual(filtered, goal)

    def test_keywords_and_label(self):
        data = {
            'labels': [self.label5.id],
            'search': 'vowel',
            'is_or': False
        }
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.e])
        self.assertEqual(filtered, goal)

    def test_empty_form(self):
        data = {}
        filtered = sorted_list_ids(artifacts_from_form(data))
        goal = sorted_list_ids([self.a, self.b, self.c, self.d, self.e, self.f])
        self.assertEqual(filtered, goal)
