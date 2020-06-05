from pytas.models import Allocation as tas_alloc
from allocations.models import Allocation as portal_alloc
from allocations.allocations_api import BalanceServiceClient
from datetime import datetime
import logging
import json
import pytz
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from util.consts.allocation import TAS_DATE_FORMAT, TAS_TO_PORTAL_MAP

logger = logging.getLogger(__name__)

class ProjectAllocationMapper:
    def __init__(self, request):
        self.allocations_from_db = self._wants_db_allocations(request)
        
    def _wants_db_allocations(self, request):
        if request.user.is_superuser:
            return True
        return False

    def _send_allocation_request_notification(self, charge_code, host):
        subject = 'Pending allocation request for project {}'.format(charge_code)
        body = '''
                <p>Please review the pending allocation request for project {project_charge_code}
                at <a href='https://{host}/admin/allocations/' target='_blank'>admin page</a></p>
                '''.format(project_charge_code = charge_code, host = host)
        send_mail(subject, strip_tags(body), settings.DEFAULT_FROM_EMAIL, [settings.PENDING_ALLOCATION_NOTIFICATION_EMAIL], html_message=body)

    def _send_allocation_decision_notification(self, charge_code, requestor_id, status, decision_summary, host):
        user_model = get_user_model()
        user = user_model.objects.get(pk=requestor_id)
        subject = 'Decision of your allocation request for project {}'.format(charge_code)
        body = '''
                <p>Dear {first} {last},</p>
                <p>Your allocation request for project {project_charge_code} has been {status}, 
                due to the following reason:</p>
                <p>{decision_summary}</p>
                <br/>
                <p><i>This is an automatic email, please <b>DO NOT</b> reply!
                If you have any question or issue, please submit a ticket on our 
                <a href='https://{host}/user/help/' target='_blank'>help desk</a>.
                </i></p>
                <br/>
                <p>Thanks,</p>
                <p>Chameleon Team</p>
                '''.format(first = user.first_name,
                           last = user.last_name,
                           project_charge_code = charge_code,
                           status = status,
                           decision_summary = decision_summary,
                           host = host)
        send_mail(subject, strip_tags(body), settings.DEFAULT_FROM_EMAIL, [user.email], html_message=body)
    
    def map(self, project, fetch_balance = True):
        if self.allocations_from_db:
            balance_service = BalanceServiceClient()
            reformated_allocations = []
            project_charge_code = self.get_attr(project, 'chargeCode')
            convert_to_dict = isinstance(project, dict)
            for alloc in portal_alloc.objects.filter(project_charge_code=project_charge_code):
                if fetch_balance and alloc.status == 'active':
                    balance = balance_service.call(project_charge_code)
                    su_used = balance.get('used')
                    if su_used is not None:
                        alloc.su_used = float(su_used)
                    else:
                        logger.error('Can not find used balance for project {}'.format(project_charge_code))
                reformated_alloc = self.portal_to_tas_obj(alloc)
                if convert_to_dict:
                    reformated_alloc = reformated_alloc.__dict__
                reformated_allocations.append(reformated_alloc)
            self.set_attr(project, 'allocations', reformated_allocations)
        return project
    
    def save_allocation(self, alloc, project_charge_code, tas, host):
        if self.allocations_from_db:
            reformated_alloc = self.tas_to_portal_obj(alloc, project_charge_code)
            reformated_alloc.save()
            self._send_allocation_request_notification(project_charge_code, host)
        else:
            tas.create_allocation(alloc)

    def get_user_id(self, request, tas):
        if self.allocations_from_db:
            return request.user.id
        else:
            return tas.get_user(username=request.user)['id']

    def allocation_approval(self, data, tas, host):
        if self.allocations_from_db:
            # update allocation model
            alloc = portal_alloc.objects.get(pk=data['id'])
            data['status'] = data['status'].lower()
            data['dateReviewed'] = datetime.now(pytz.utc)
            for item in ['reviewerId', 'dateReviewed', 'start', 'end', 'status', 'decisionSummary', 'computeAllocated']:
                setattr(alloc, TAS_TO_PORTAL_MAP[item], data[item])
            alloc.save()
            logger.info('Allocation model updated: data=%s', alloc.__dict__)
            # send email to PI
            email_args = {'charge_code': data['project'],
                          'requestor_id': data['requestorId'],
                          'status': data['status'],
                          'decision_summary': data['decisionSummary'],
                          'host': host}
            self._send_allocation_decision_notification(**email_args)
        else:
            result = tas.allocation_approval(data['id'], data)
            logger.info('Allocation approval TAS response: data=%s', json.dumps(result))

    def portal_to_tas_obj(self, alloc):
        initial = {'computeUsed': alloc.su_used,
                   'computeAllocated': alloc.su_allocated,
                   'computeRequested': alloc.su_requested,
                   'dateRequested': alloc.date_requested.strftime(TAS_DATE_FORMAT) if alloc.date_requested else None,
                   'dateReviewed': alloc.date_reviewed.strftime(TAS_DATE_FORMAT) if alloc.date_reviewed else None,
                   'decisionSummary': alloc.decision_summary,
                   'end': alloc.expiration_date.strftime(TAS_DATE_FORMAT) if alloc.expiration_date else None,
                   'id': alloc.id,
                   'justification': alloc.justification,
                   'memoryUsed': 0,
                   'memoryAllocated': 0,
                   'memoryRequested': 0,
                   'project': alloc.project_charge_code,
                   'projectId': -1,
                   'requestor': alloc.requestor_username(),
                   'requestorId': alloc.requestor_id,
                   'resource': 'Chameleon',
                   'resourceId': 0,
                   'reviewer': alloc.reviewer_username(),
                   'reviewerId':alloc.reviewer_id,
                   'start': alloc.start_date.strftime(TAS_DATE_FORMAT) if alloc.start_date else None,
                   'status': alloc.status.capitalize(),
                   'storageUsed': 0,
                   'storageAllocated': 0,
                   'storageRequested': 0,
                   }
        reformated_alloc = tas_alloc(initial=initial)
        return reformated_alloc

    def tas_to_portal_obj(self, alloc, project_charge_code):
        reformated_alloc = {}        
        for key, val in alloc.items():
            if key in TAS_TO_PORTAL_MAP:
                reformated_alloc[TAS_TO_PORTAL_MAP[key]] = val
        
        reformated_alloc['date_requested'] = datetime.now(pytz.utc)
        reformated_alloc['status'] = 'pending'
        reformated_alloc['project_charge_code'] = project_charge_code
                
        reformated_alloc = portal_alloc(**reformated_alloc)
        
        return reformated_alloc

    def get_attr(self, obj, key):
        '''Attempt to resolve the key either as an attribute or a dict key'''
        if isinstance(obj, dict):
            return obj.get(key)
        else:
            return getattr(obj, key, None)

    def set_attr(self, obj, key, val):
        '''Attempt to resolve the key either as an attribute or a dict key'''
        if isinstance(obj, dict):
            obj[key] = val
        else:
            setattr(obj, key, val)
        return obj
