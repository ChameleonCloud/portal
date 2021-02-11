from django.forms import BooleanField, ModelForm, Select

from user_news.models import Event, News, Outage, OutageUpdate


class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = "__all__"
        widgets = {"event_type": Select}


class OutageForm(ModelForm):
    send_email_notification = BooleanField(required=False)

    class Meta:
        model = Outage
        exclude = ["reminder_sent"]

    def clean_send_email_notification(self):
        send = self.cleaned_data.get("send_email_notification")
        self.instance.send_email_notification = send
        return send
