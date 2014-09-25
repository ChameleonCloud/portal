
from django.forms import Form, ModelForm, ValidationError
from django.forms import CharField, IntegerField, Textarea

from user.models import ChameleonUser
from allocation.models import AllocationRequest


class AllocationRequestForm(ModelForm):
    class Meta:
        model = AllocationRequest
        exclude = ["requester","review_date","status","deny_reason","granted_units","granted_duration"]
        #fields = []

    def clean_name(self):
        name = self.cleaned_data.get("name")
        users = ChameleonUser.objects.filter(username=name)
        if len(users) > 0:
            raise ValidationError(u'name conflicts with an existing name')
        return name

    def clean_accept_allocation_agreement(self):
        accept_allocation_agreement = self.cleaned_data.get("accept_allocation_agreement")
        if not accept_allocation_agreement:
            raise ValidationError(u'you must accept the allocation agreement.')
        return accept_allocation_agreement

class ApproveAllocationForm(Form):
    granted_units = IntegerField(required=False,help_text="the number of units granted")
    granted_duration = IntegerField(required=False,help_text="the number of months granted")
    deny_reason = CharField(max_length=2000,
                            required=False,
                            widget=Textarea,
                            help_text="the reason why the account request was denied (optional)")
