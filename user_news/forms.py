from django.forms import ModelForm, Select
from user_news.models import News, Event, Outage, OutageUpdate

class EventForm(ModelForm):

    class Meta:
        model = Event
        widgets = {
            'event_type': Select
        }
