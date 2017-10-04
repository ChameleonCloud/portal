from django.forms import ModelForm, Select, BooleanField
from user_news.models import News, Event, Outage, OutageUpdate

class EventForm(ModelForm):

    class Meta:
        model = Event
	fields = '__all__'
        widgets = {
            'event_type': Select
        }

class OutageForm(ModelForm):
    send_email_notification = BooleanField(required=False)

    class Meta:
        model = Outage
	fields = '__all__'

    def clean_send_email_notification(self):
        send = self.cleaned_data.get('send_email_notification')
        self.instance.send_email_notification = send
        return send
