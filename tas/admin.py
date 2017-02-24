from django import forms
from django.conf.urls import url
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from pytas.http import TASClient
from django.contrib import admin
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext, ugettext_lazy as _
from django.http import HttpResponse
from .forms import TasUserProfileAdminForm
import csv
import logging
import datetime

logger = logging.getLogger('default');

class ReadOnlyDirectToTasWidget(forms.Widget):
    def render(self, name, value, attrs):
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
    password = None # hide password

    def clean_username(self):
        # Cannot edit username, return initial value no matter what
        return self.initial['username']


class TasUserAdmin(UserAdmin):
    actions = ['reset_user_password', 'make_user_pi', 'download_user_report']

    form = TasUserAdminForm
    fieldsets = (
        (_('Account'), {'fields': ('username',)}),
    ) + UserAdmin.fieldsets[2:]

    def reset_user_password(self, request, selected_users, form_url=''):

        # The user has already confirmed the action.
        # Trigger password reset notifications
        if request.POST.get('post'):
            tas = TASClient()
            for user in selected_users:
                try:
                    resp = tas.request_password_reset(user.username, source='Chameleon')
                    self.message_user(request, _('Password Reset notification sent to: %s') % user.username)
                except:
                    logger.exception( 'Failed password reset request' )
                    self.message_user(request, _('Unable to reset password for: %s') % user.username, level=messages.ERROR)

            return None

        context = {
            'title': _('Send Password Reset Notification'),
            'opts': self.model._meta,
            'selected_users': selected_users,
            'form_url': form_url,
            'action_checkbox_name':helpers.ACTION_CHECKBOX_NAME
        }
        context.update(admin.site.each_context())

        return TemplateResponse(request,
            'admin/tas/reset_user_password.html',
            context, current_app=self.admin_site.name)

    reset_user_password.short_description = "Send password reset"

    def make_user_pi(self, request, selected_users, form_url=''):

        # The user has already confirmed the action.
        # Make the users PI Eligible
        if request.POST.get('post'):
            tas = TASClient()
            for user in selected_users:
                try:
                    tas_user = tas.get_user(username=user.username)
                    if tas_user['piEligibility'] == 'Eligible':
                        self.message_user(request, _('User %s already PI Eligible') % user.username, level=messages.WARNING)
                    else:
                        tas_user['piEligibility'] = 'Eligible'
                        tas.save_user(tas_user['id'], tas_user)
                        self.message_user(request, _('Granted PI Eligible to %s') % user.username)
                except:
                    logger.exception('Unable to Grant PI Eligible to %s' % user.username)
                    self.message_user(request, _('Unable to Grant PI Eligible to %s') % user.username, level=messages.ERROR)

            return None

        context = {
            'title': _('Grant PI eligibility'),
            'opts': self.model._meta,
            'selected_users': selected_users,
            'form_url': form_url,
            'action_checkbox_name':helpers.ACTION_CHECKBOX_NAME
        }
        context.update(admin.site.each_context())

        return TemplateResponse(request,
            'admin/tas/make_user_pi.html',
            context, current_app=self.admin_site.name)

    make_user_pi.short_description = "Grant PI Eligibility"

    def download_user_report(self, request, selected_users, form_url=''):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="chameleon_users.csv"'

        writer = csv.writer(response)
        writer.writerow(['username','first_name','last_name','email','is_active','is_staff','date_joined','last_login'])
        for user in selected_users:
            joined = user.date_joined.strftime("%d-%M-%Y %H:%M:%S %Z")
            last = user.last_login.strftime("%d-%M-%Y %H:%M:%S %Z")
            user = [user.username.encode('utf8'), user.first_name.encode('utf8'), user.last_name.encode('utf8'), user.email.encode('utf8'), user.is_active, user.is_staff, joined, last]
            writer.writerow(user)

        return response

    download_user_report.short_description = "Download User Report"

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
            logger.debug(request.POST)
            form = TasUserProfileAdminForm(request.POST)
            if form.is_valid():
                redirect = False
                user.first_name = tas_user['firstName'] = form.cleaned_data['firstName']
                user.last_name = tas_user['lastName'] = form.cleaned_data['lastName']
                user.email = tas_user['email'] = form.cleaned_data['email']
                tas_user['piEligibility'] = form.cleaned_data['piEligibility']
                try:
                    tas.save_user(tas_user['id'], tas_user) # Update remote TAS record
                    user.save() # Update local Django record
                    self.message_user(request, _('Successfully updated profile for user: %s') % user.username)
                    redirect = True
                except:
                    logger.exception('Error saving user %s' % user.username)
                    self.message_user(request, _('Error saving profile for user: %s') % user.username, level=messages.ERROR)
                    redirect = False

                if form.cleaned_data['reset_password']:
                    # trigger password reset
                    try:
                        resp = tas.request_password_reset( user.username, source='Chameleon' )
                        logger.debug( 'Administrator triggered password reset for user %s. Reset token: %s' % (user.username, resp) )
                        self.message_user(request, _('Sent password reset to user: %s') % user.username)
                        redirect = True
                    except:
                        logger.exception( 'Failed password reset request' )
                        self.message_user(request, _('Password reset failed for user: %s') % user.username, level=messages.ERROR)
                        redirect = False

                if redirect:
                    return HttpResponseRedirect(
                        reverse(
                            '%s:auth_%s_change' % (
                                self.admin_site.name,
                                user._meta.model_name,
                            ),
                            args=(user.pk,),
                        )
                    )

        else:
            form = TasUserProfileAdminForm(initial=tas_user)

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
