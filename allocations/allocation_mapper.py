from pytas.models import Allocation as tas_alloc
from allocations.models import Allocation as portal_alloc
from allocations.allocations_api import BalanceServiceClient

class ProjectAllocationMapper:
    def __init__(self, request):
        self.allocations_from_db = self._wants_db_allocations(request)
        
    def _wants_db_allocations(self, request):
        if request.user.is_superuser:
            return True
        return False
    
    def map(self, project):
        if self.allocations_from_db:
            balance_service = BalanceServiceClient()
            reformated_allocations = []
            for alloc in portal_alloc.objects.filter(project_charge_code=project.chargeCode):
                if alloc.status == 'active':
                    active_allocation = balance_service.call(project.chargeCode)
                    if 'used' in active_allocation and active_allocation['used']:
                        alloc.su_used = float(balance_service.call(project.chargeCode)['used'])
                reformated_allocations.append(self.portal_to_tas_obj(alloc))
            project.allocations = reformated_allocations
        return project

    def portal_to_tas_obj(self, alloc):
        initial = {'computeUsed': alloc.su_used,
                   'computeAllocated': alloc.su_allocated,
                   'computeRequested': alloc.su_requested,
                   'dateRequested': alloc.date_requested,
                   'dateReviewed': alloc.date_reviewed,
                   'decisionSummary': alloc.decision_summary,
                   'end': alloc.expiration_date,
                   'id': alloc.id,
                   'justification': alloc.justification,
                   'memoryUsed': 0,
                   'memoryAllocated': 0,
                   'memoryRequested': 0,
                   'project': alloc.project_charge_code,
                   'projectId': None,
                   'requestor': alloc.requestor_username,
                   'requestorId': alloc.requestor_id,
                   'resource': 'Chameleon',
                   'resourceId': 0,
                   'reviewer': alloc.reviewer_username,
                   'reviewerId':alloc.reviewer_id,
                   'start': alloc.start_date,
                   'status': alloc.status.capitalize(),
                   'storageUsed': 0,
                   'storageAllocated': 0,
                   'storageRequested': 0,
                   }
        reformated_alloc = tas_alloc(initial=initial)
        return reformated_alloc
