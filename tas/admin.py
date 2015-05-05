from django.shortcuts import render, redirect
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from pytas.pytas import client as TASClient
from django.contrib import admin

@admin.site.register_view('user_edit')
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

@admin.site.register_view('tas_admin')
def tas_users(request, selectedUsers):
    tas = TASClient()
    users = []

    for username in selectedUsers:
        users.append(tas.get_user(username=username))

    institutions = tas.institutions()

    return render(request, 'admin/admin.html', { 'users': users, 'institutions' : institutions })


class TasUserAdmin(UserAdmin):
    actions = ['tas_user_info']

    def tas_user_info(self, request, queryset):
        return tas_users(request, queryset)

admin.site.unregister(User)
admin.site.register(User, TasUserAdmin)


