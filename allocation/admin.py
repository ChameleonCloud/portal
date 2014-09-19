from django.contrib import admin
from allocation.models import Allocation,AllocationRequest,Resource

admin.site.register(Resource)
admin.site.register(Allocation)
admin.site.register(AllocationRequest)
