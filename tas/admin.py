from django.shortcuts import render, redirect
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from pytas.pytas import client as TASClient
from django.contrib import admin

@admin.site.register_view('user_edit')
def user_edit(request):
    if request.POST:
        data = request.POST.copy()
        num_users = data['num_users']
        tas = TASClient()

        user = {}
        for x in range (0, int(num_users)):
            user['username'] = data['username_'+str(x)]
            user['firstName'] = data['firstName_'+str(x)]
            user['lastName'] = data['lastName_'+str(x)]
            user['email'] = data['email_'+str(x)]
            user['departmentId'] = int(data['department_'+str(x)])
            dept = tas.department(data['department_'+str(x)])
            user['department'] = dept.name
            user['institutionId'] = int(data['institution_'+str(x)])
            inst = tas.institution(data['institution_'+str(x)])
            user['institution'] = inst.name

            if 'piEligable_'+str(x) in data:
                user['piEligable'] = True
            else:
                user['piEligable'] = False

            user_result = tas.save_user(data['id_'+str(x)], user)

            if user_result.username:
                success = True

    return tas_users(request, user.username)

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


