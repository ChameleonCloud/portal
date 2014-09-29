
import copy

import ldap
import ldap.modlist

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template import loader
from django.views import generic

from user.forms import *
from user.models import ChameleonUser, UserProfile

def request_account(request):
    if request.method == "POST":
        cform = ChameleonUserForm(request.POST)
        pform = UserProfileForm(request.POST)
        if cform.is_valid() and pform.is_valid():
            # save the ChameleonUser (is_active False?)
            user = cform.save()
            # save the UserProfile
            profile = pform.save(commit=False)
            profile.user = user
            profile.status = "S"
            profile = pform.save()
            return redirect("user/request_thanks.html")
    else:
        cform = ChameleonUserForm()
        pform = UserProfileForm()
    return render(request, 'user/request.html', {'cform': cform, 'pform': pform})

@staff_member_required
def account_requests(request):
    profiles = UserProfile.objects.all()
    context = {"profiles": profiles}
    return render(request,"user/review_requests.html",context)

@staff_member_required
def approve_account(request, username):
    print("#### user name is %s" % username)
    users = ChameleonUser.objects.filter(username=username)
    if len(users) == 0:
        print("#### throw exception - didn't find user")
        user = None
    else:
        user = users[0]

    profiles = UserProfile.objects.filter(user=user)
    if len(profiles) == 0:
        print("#### throw exception - didn't find profile")
        profile = None
    else:
        profile = profiles[0]

    if request.method == "POST":
        form = ApproveUserForm(request.POST)
        if form.is_valid():
            if "_approve" in request.POST:
                print("## approved user")
                # change profile status
                profile.status = "A"
                profile.save()
                # create the LDAP entry
                #_create_user_ldap(user,profile)
                # make the user active (in ldap!)
                _activate_user_ldap(user,profile)
                user.is_active = True
                user.save()
                # send password reset email
                print("## sending email")
                _send_approve_email(user,profile)
                return redirect("user.views.approve_request")
            elif "_deny" in request.POST:
                # change profile status
                profile.status = "D"
                print("## deny reason: %s" % form.cleaned_data["deny_reason"])
                if form.cleaned_data["deny_reason"]:
                    profile.deny_reason += "\n" + form.cleaned_data["deny_reason"]
                profile.save()
                # send deny email
                _send_deny_email(user,profile)
                # clean up denied account requests now and then
                return redirect("user.views.deny_request")
            else:
                print("#### didn't see approve or deny")
    else:
        form = ApproveUserForm(request.POST)

    context = {"form": form,
               "user": user,
               "profile": profile,
               "hide_password": True}
    return render(request,"user/review.html",context)

def _create_user_ldap(user, profile):
    uri = settings.AUTH_LDAP_SERVER_URI
    if callable(uri):
        uri = uri()
    conn = ldap.initialize(uri)

    template = settings.AUTH_LDAP_USER_DN_TEMPLATE
    username = ldap.dn.escape_dn_chars(user.username)
    dn = template % {'user': username}

    # connect as the portal to create the user's entry
    conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

    # figure out what uidNumber to use (probably better to use a uidNext entry, but this is good enough for now)
    entries = conn.search_s("ou=people,dc=chameleoncloud,dc=org",
                            ldap.SCOPE_SUBTREE,
                            "(objectclass=posixAccount)",
                            ["uidNumber"])
    # each entry is (dn, attr dict)
    largest_uid_number = max(map(lambda entry: int(entry[1]["uidNumber"][0]),entries))
    uid_number = largest_uid_number + 1

    # ldap expects strings, django uses in unicode
    attrs = {}
    attrs["objectclass"] = ["top","inetOrgPerson","posixAccount","pwdPolicy","ldapPublicKey"]
    attrs["cn"] = str(username)
    attrs["gecos"] = str("%s %s" % (user.first_name,user.last_name))
    attrs["gidNumber"] = "100"
    attrs["givenName"] = str(user.first_name)
    attrs["homeDirectory"] = str("/home/%s" % username)
    attrs["loginShell"] = "/bin/bash"
    attrs["mail"] = str(user.email)
    attrs["pwdAttribute"] = "userPassword"
    attrs["sn"] = str(user.last_name)
    # sshPublicKey, if there are any in the profile
    attrs["uid"] = str(username)
    attrs["uidNumber"] = "%d" % uid_number

    ldif = ldap.modlist.addModlist(attrs)
    print(ldif)

    conn.add_s(dn,ldif)

    conn.unbind_s()


def _activate_user_ldap(user, profile):
    uri = settings.AUTH_LDAP_SERVER_URI
    if callable(uri):
        uri = uri()
    conn = ldap.initialize(uri)

    template = settings.AUTH_LDAP_USER_DN_TEMPLATE
    username = ldap.dn.escape_dn_chars(user.username)
    user_dn = str(template % {'user': username})

    # connect as the portal to create the user's entry
    conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

    active_dn = "cn=active,ou=group,dc=django,dc=chameleoncloud,dc=org"
    entries = conn.search_s(active_dn,
                            ldap.SCOPE_BASE,
                            "(objectclass=*)")

    #print("## found %d entries" % len(entries))
    entry = entries[0]
    #print(entry)
    old = entry[1]
    #print("old: %s" % old)
    new = copy.deepcopy(old)
    if user_dn in old["member"]:
        #print("#### %s is already a member" % user_dn)
        pass
    else:
        #print("#### %s is not a member" % user_dn)
        new["member"].append(user_dn)
    #print("new: %s" % new)

    ldif = ldap.modlist.modifyModlist(old,new)
    #print("ldif is: %s" % ldif)

    conn.modify_s(active_dn,ldif)

    conn.unbind_s()

def _send_approve_email(user, profile):
    context = {"user": user,
               "profile": profile}
    body = loader.render_to_string("user/approve_email.txt",context).strip()
    subject = "Chameleon account request approved"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,[user.email])

def _send_deny_email(user, profile):
    context = {"user": user,
               "profile": profile}
    body = loader.render_to_string("user/deny_email.txt",context).strip()
    subject = "Chameleon account request denied"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,[user.email])




def approve_request(request):
    return render(request,"user/review_approve.html")

def deny_request(request):
    return render(request,"user/review_deny.html")

def profile(request):
    user_profile = UserProfile.objects.filter(user=request.user)
    if len(user_profile) == 0:
        user_profile = None
    else:
        user_profile = user_profile[0]
    print(user_profile)
    ssh_keys = SshPublicKey.objects.filter(user=request.user)
    context = {"user_profile": user_profile,
               "ssh_keys": ssh_keys}
    return render(request,"user/profile.html",context)

# can't use this in menus.py
class UserView(generic.DetailView):
    model = User
    template_name = "user/profile.html"


def logged_out(request):
    return render(request, 'user/logged_out.html')
