from django import forms
from django.contrib.auth.models import User
import django_filters
from .models import Artifact, Label

class LabelFilter(django_filters.FilterSet):
    labels = django_filters.ModelMultipleChoiceFilter(queryset=Label.objects.all(), widget=forms.CheckBoxSelectMultiple)

    class Meta:
        model = Artifact
        fields = ['labels']
        
