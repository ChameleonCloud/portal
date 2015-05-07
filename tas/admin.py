from django import forms
from django.conf.urls import url
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from pytas.pytas import client as TASClient
from django.contrib import admin
from django.utils.translation import ugettext, ugettext_lazy as _
from .forms import TasUserProfileAdminForm
import logging

logger = logging.getLogger('default');

def user_edit(request):
    data = request.POST.copy()
    num_users = data['num_users']
    tas = TASClient()

    user = {}
    usernameList = []
    for x in range (0, int(num_users)):
        user['username'] = data['username_'+str(x)]
        user['firstName'] = data['firstName_'+str(x)]
        user['lastName'] = data['lastName_'+str(x)]
        user['email'] = data['email_'+str(x)]
        user['source'] = data['source_'+str(x)]
        user['citizenshipId'] = data['citizenshipId_'+str(x)]
        user['citizenship'] = data['citizenship_'+str(x)]
        user['countryId'] = data['countryId_'+str(x)]
        user['country'] = data['country_'+str(x)]

        deptId = int(data['department_'+str(x)])
        instId = int(data['institution_'+str(x)])
        dept = tas.get_department(instId, deptId)
        inst = tas.get_institution(instId)

        user['departmentId'] = int(deptId)
        user['department'] = dept['name']
        user['institutionId'] = int(instId)
        user['institution'] = inst['name']

        if 'piEligible_'+str(x) in data:
            user['piEligibility'] = 'Eligible'
        else:
            user['piEligibility'] = 'Ineligible'

        if 'resetPassword_'+str(x) in data:
            try:
                resp = tas.request_password_reset( user['username'], source='Chameleon' )
                print resp
            except:
                print 'Failed password reset request'

        user_result = tas.save_user(data['id_'+str(x)], user)


        if user_result['username']:
            usernameList.append(user_result['username'])
            success = True

    if success:
        messages.success(request, 'TAS information successfully updated')
    else:
        messages.error(request, "There was an issue saving this user's TAS information. Please trying again later.")

    return tas_users(request, usernameList)

class ReadOnlyDirectToTasWidget(forms.Widget):
    def render(slef, name, value, attrs):
        return value

class ReadOnlyDirectToTasField(forms.Field):
    widget = ReadOnlyDirectToTasWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super(ReadOnlyDirectToTasField, self).__init__(*args, **kwargs)

    def bound_data(self, data, initial):
        # Always return initial because the widget doesn't
        # render an input field.
        return initial

    def has_changed(self, initial, data):
        return False


class TasUserAdminForm(UserChangeForm):
    username = ReadOnlyDirectToTasField(label=_("Username"),
        help_text = _('You can manage Permissions below. The User record itself is managed by TAS. Manage User Details <a href="tas/">using TAS</a>.')
    )


class TasUserAdmin(UserAdmin):
    actions = ['reset_user_password', 'make_user_pi']

    form = TasUserAdminForm
    fieldsets = (
        (_('Account'), { 'fields': ('username', ) }),
    ) + UserAdmin.fieldsets[2:]

    # def tas_user_info(self, request, username):
    #
    #     return render(request, 'admin/admin.html', context)

    def reset_user_password(self, request, selected_users):
        tas = TASClient()
        success = False

        for username in selected_users:
            try:
                resp = tas.request_password_reset(username, source='Chameleon' )

                if resp:
                    success = True
            except:
                logger.exception( 'Failed password reset request' )

        if success:
            messages.success(request, 'Password reset email triggered')
        else:
            messages.error(request, 'There was an issue triggering the password reset email')

    def make_user_pi(self, request, selected_users):
        tas = TASClient()
        success = False

        for username in selected_users:
            try:
                tas_user = tas.get_user(username=username)
                tas_user['piEligibility'] = 'Eligible'
                user_result = tas.save_user(tas_user['id'], tas_user)

                if user_result['username']:
                    success = True
            except:
                logger.exception( 'Failed user save request' )

        if success:
            messages.success(request, 'User granted PI eligibility')
        else:
            messages.error(request, 'There was an issue saving the user')

    reset_user_password.short_description = "Trigger Password Reset"
    make_user_pi.short_description = "Make PI"

    def tas_manage(self, request, id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = self.get_object(request, unquote(id))

        if user is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                'name': force_text(self.model._meta.verbose_name),
                'key': escape(id),
            })

        tas = TASClient()
        tas_user = tas.get_user(username=user.username)

        if request.method == 'POST':
            # TODO
            logger.debug(request.POST)
            form = TasUserProfileAdminForm(initial=tas_user)
        else:
            form = TasUserProfileAdminForm(initial=tas_user)

        # institutions = tas.institutions()

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Manage TAS User: %s') % user.username,
            'adminform': adminForm,
            'form_url': form_url,
            'form': form,
            'opts': self.model._meta,
            'original': user,
        }
        context.update(admin.site.each_context())

        return TemplateResponse(request,
            'admin/tas/tas_manage.html',
            context, current_app=self.admin_site.name)

    def get_urls(self):
        return [
            url(r'(.+)/tas/$', self.admin_site.admin_view(self.tas_manage), name='auth_user_tas'),
        ] + super(TasUserAdmin, self).get_urls()

admin.site.unregister(User)
admin.site.register(User, TasUserAdmin)
