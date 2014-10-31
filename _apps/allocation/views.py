
import copy
import datetime

import ldap
import ldap.modlist

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader

from allocation.forms import *
from allocation.models import *

@login_required
def index(request):
    pi_allocations = Allocation.objects.filter(principal_investigator=request.user)
    manage_allocations = Allocation.objects.filter(allocation_manager=request.user)
    # improve this - don't have time to right now
    user_allocations = []
    for allocation in Allocation.objects.all():
        if allocation.users.filter(id=request.user.id) > 0:
            user_allocations.append(allocation)

    req_requests = AllocationRequest.objects.filter(requester=request.user)
    # improve this - don't have time to right now
    user_requests = []
    for allocation_request in AllocationRequest.objects.all():
        if allocation_request.initial_users.filter(id=request.user.id) > 0:
            if allocation_request not in req_requests:
                user_requests.append(allocation_request)

    context = {"pi_allocs": pi_allocations,
               "manage_allocs": manage_allocations,
               "use_allocs": user_allocations,
               "req_alloc_reqs": req_requests,
               "user_alloc_reqs": user_requests}

    return render(request, 'allocation/index.html', context)

@login_required
def allocation_view(request, id):
    allocation = get_object_or_404(Allocation,id=id)
    # test if the request.user is part of this allocation

    context = {"allocation": allocation}
    return render(request, 'allocation/allocation.html', context)

@login_required
def allocation_request_edit(request):
    if request.method == "POST":
        form = AllocationRequestForm(request.POST)
        if form.is_valid():
            allocation_request = form.save(commit=False)
            allocation_request.requester = request.user
            if "_submit" in request.POST:
                print("#### submit ####")
                allocation_request.status = "S"
                allocation_request = form.save(allocation_request)
                # automatically approve allocations that have a futuregrid_project flag?
                return redirect("allocation.views.allocation_request_thanks")
            else:  # assume "_save"
                print("#### save ####")
                allocation_request.status = "I"
                allocation_request = form.save(allocation_request)
                return redirect("allocation.views.allocation_request_continue",allocation_request.id)
    else:
        form = AllocationRequestForm()
    return render(request, 'allocation/request_form.html', {'form': form})

@login_required
def allocation_request_continue(request, id):
    allocation_request = get_object_or_404(AllocationRequest, id=id)
    if allocation_request.requester != request.user:
        return HttpResponse("Unauthorized",status=401)
    if allocation_request.status != "I":
        # can only edit incomplete allocation requests
        return redirect("allocation.views.allocation_request_view",id=id)
    if request.method == "POST":
        form = AllocationRequestForm(request.POST,instance=allocation_request)
        if form.is_valid():
            allocation_request = form.save()
            if "_submit" in request.POST:
                print("#### submit ####")
                allocation_request.status = "S"
                allocation_request = form.save(allocation_request)
                # automatically approve allocations that have a futuregrid_project flag?
                return redirect("allocation.views.allocation_request_thanks")
            else:  # assume "_save"
                print("#### save ####")
                allocation_request.status = "I"
                allocation_request = form.save(allocation_request)
                return redirect("allocation.views.allocation_request_continue",allocation_request.id)
    else:
        form = AllocationRequestForm(instance=allocation_request)
    return render(request, 'allocation/request_form.html', {'form': form})


@login_required
def allocation_request_view(request, id):
    allocation_request = get_object_or_404(AllocationRequest,id=id)
    # test if the request.user is the requester or part of this allocation associated with this request

    context = {"allocation_request": allocation_request}
    return render(request, 'allocation/request.html', context)



def allocation_request_thanks(request):
    return render(request, 'allocation/request_thanks.html')


@staff_member_required
def allocation_requests(request):
    allocation_requests = AllocationRequest.objects.all()
    print("## found %d allocation requests" % len(allocation_requests))
    context = {"allocation_requests": allocation_requests}
    return render(request,"allocation/review_requests.html",context)

@staff_member_required
def approve_allocation(request, id):
    allocation_request = AllocationRequest.objects.get(id=id)
    # test if allocation_request is None?

    if request.method == "POST":
        print("#### POST")
        form = ApproveAllocationForm(request.POST)
        if form.is_valid():
            print("#### valid form")
            if "_approve" in request.POST:
                print("## approved allocation")
                allocation_request.status = "A"
                allocation_request.save()
                print("## allocation request for %d units and %d months" % (allocation_request.units,allocation_request.duration))
                if form.cleaned_data["granted_units"]:
                    granted_units = int(form.cleaned_data["granted_units"])
                else:
                    granted_units = allocation_request.units
                if form.cleaned_data["granted_duration"]:
                    granted_duration = int(form.cleaned_data["granted_duration"])
                else:
                    granted_duration = allocation_request.duration
                try:
                    allocation = Allocation.objects.get(name=allocation_request.name)
                    _addToAllocation(allocation,allocation_request,granted_units,granted_duration)
                except:
                    _newAllocation(allocation_request,granted_units,granted_duration)
                _sendApproveEmail(allocation_request)
                return redirect("allocation.views.approve_request")
            elif "_deny" in request.POST:
                allocation_request.status = "D"
                print("## deny reason: %s" % form.cleaned_data["deny_reason"])
                if form.cleaned_data["deny_reason"]:
                    allocation_request.deny_reason = form.cleaned_data["deny_reason"]
                allocation_request.save()
                _sendDenyEmail(allocation_request)
                # clean up denied allocation requests now and then
                return redirect("allocation.views.deny_request")
            else:
                print("#### didn't see approve or deny")
    else:
        form = ApproveAllocationForm(request.POST)

    context = {"form": form,
               "allocation_request": allocation_request}
    return render(request,"allocation/review.html",context)

def _newAllocation(allocation_request, granted_units, granted_duration):
    allocation = Allocation()
    allocation.name = allocation_request.name
    allocation.principal_investigator = allocation_request.requester

    print("## new allocation with %d units and %d months" % (granted_units,granted_duration))
    allocation.granted_units = granted_units
    allocation.remaining_units = allocation.granted_units

    allocation.start_date = datetime.date.today()
    # do this better
    extra_days = int(granted_duration / 12.0 * 365)
    allocation.end_date = allocation.start_date + datetime.timedelta(days=extra_days)

    # save the instance before accessing any ManyToManyField
    allocation.save()

    for user in allocation_request.initial_users.all():
        allocation.users.add(user)
    allocation.save()

    allocation_request.allocation = allocation
    allocation_request.save()

    _updateLdapFromAllocation(allocation)

def _updateLdapFromAllocation(allocation):
    _updateLdapGroup(allocation)
    _updateLdapRoles(allocation)

def _updateLdapGroup(allocation):
    print("## updateLdapGroup")
    conn = _bindLdap()

    # are we adding or updating?
    try:
        entries = conn.search_s("cn=%s,ou=group,dc=chameleoncloud,dc=org" % str(allocation.name),
                                ldap.SCOPE_BASE,
                                "(objectclass=*)")
    except ldap.NO_SUCH_OBJECT:
        _addLdapGroup(allocation,conn)
    else:
        _modifyLdapGroup(allocation,conn,entries[0])

# use the default dn and password (the portal) y default
def _bindLdap(dn=settings.AUTH_LDAP_BIND_DN, passwd = settings.AUTH_LDAP_BIND_PASSWORD):
    uri = settings.AUTH_LDAP_SERVER_URI
    if callable(uri):
        uri = uri()
    conn = ldap.initialize(uri)
    conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)
    return conn

def _addLdapGroup(allocation, conn=None):
    print("## addLdapGroup")
    if conn is None:
        conn = _bindLdap()

    # figure out what gidNumber to use (probably better to use a gidNext entry, but this is good enough for now)
    entries = conn.search_s("ou=group,dc=chameleoncloud,dc=org",
                            ldap.SCOPE_SUBTREE,
                            "(objectclass=posixGroup)",
                            ["gidNumber"])
    # each entry is (dn, attr dict)
    largest_gid_number = max(map(lambda entry: int(entry[1]["gidNumber"][0]),entries))
    gid_number = largest_gid_number + 1

    attrs = _getLdapGroupAttrs(allocation,gid_number)
    ldif = ldap.modlist.addModlist(attrs)

    dn = str("cn=%s,ou=group,dc=chameleoncloud,dc=org" % allocation.name)
    conn.add_s(dn,ldif)

    conn.unbind_s()


def _modifyLdapGroup(allocation, conn=None, entry=None):
    print("## modifyLdapGroup")
    if conn is None:
        conn = _bindLdap()
    if entry is None:
        entries = conn.search_s("cn=%s,ou=group,dc=chameleoncloud,dc=org" % str(allocation.name),
                                ldap.SCOPE_BASE,
                                "(objectclass=*)")
        if entries is None:
            print("cannot find existing LDAP group for %s" % allocation.name)
            return
        entry = entries[0]

    (dn,old) = entry
    # the only thing that can be updated are the memberUids
    new = copy.deepcopy(old)
    new["memberUid"] = _getMemberUids(allocation)
    
    ldif = ldap.modlist.modifyModlist(old,new)
    print("  ## updating %s with: %s" % (dn,ldif))
    conn.modify_s(dn,ldif)

    conn.unbind_s()


def _getLdapGroupAttrs(allocation, gid_number):
    # ldap expects strings, django uses in unicode
    attrs = {}
    attrs["objectclass"] = ["top","posixGroup"]
    attrs["cn"] = str(allocation.name)
    attrs["gidNumber"] = "%d" % gid_number
    attrs["memberUid"] = _getMemberUids(allocation)
    return attrs

def _getMemberUids(allocation):
    members = []
    members.append(str(allocation.principal_investigator.username))
    if allocation.allocation_manager is not None:
        members.append(str(allocation.allocation_manager.username))
    for user in allocation.users.all():
        members.append(str(user.username))
    return members

def _updateLdapRoles(allocation):
    print("## updateLdapRoles")
    conn = _bindLdap()

    # are we adding or updating?
    try:
        conn.search_s("cn=member,cn=%s,ou=group,dc=chameleoncloud,dc=org" % str(allocation.name),
                      ldap.SCOPE_BASE,
                      "(objectclass=*)")
    except ldap.NO_SUCH_OBJECT:
        _addLdapRoles(allocation)
    else:
        _modifyLdapRoles(allocation)
    finally:
        conn.unbind_s()

def _addLdapRoles(allocation):
    print("## addLdapRoles")
    conn = _bindLdap()

    attrs = {}
    attrs["objectclass"] = ["organizationalRole"]
    attrs["cn"] = "admin"
    attrs["roleOccupant"] = ["cn=%s,ou=people,dc=chameleoncloud,dc=org" %
                                 str(allocation.principal_investigator.username)]
    ldif = ldap.modlist.addModlist(attrs)
    dn = str("cn=admin,cn=%s,ou=group,dc=chameleoncloud,dc=org" % allocation.name)
    conn.add_s(dn,ldif)

    attrs = {}
    attrs["objectclass"] = ["organizationalRole"]
    attrs["cn"] = "member"
    attrs["roleOccupant"] = map(lambda uid: "cn=%s,ou=people,dc=chameleoncloud,dc=org" % str(uid),
                                _getMemberUids(allocation))
    ldif = ldap.modlist.addModlist(attrs)
    dn = str("cn=member,cn=%s,ou=group,dc=chameleoncloud,dc=org" % allocation.name)
    conn.add_s(dn,ldif)

    conn.unbind_s()

def _modifyLdapRoles(allocation):
    print("## modifyLdapRoles")
    conn = _bindLdap()

    entries = conn.search_s("cn=admin,cn=%s,ou=group,dc=chameleoncloud,dc=org" % str(allocation.name),
                            ldap.SCOPE_BASE,
                            "(objectclass=*)")
    if entries is None:
        print("cannot find existing LDAP admin roles for %s" % allocation.name)
        return
    (dn,old) = entries[0]
    # the only thing that can be updated are the roleOccupant
    new = copy.deepcopy(old)
    new["roleOccupant"] = ["cn=%s,ou=people,dc=chameleoncloud,dc=org" %
                           str(allocation.principal_investigator.username)]
    ldif = ldap.modlist.modifyModlist(old,new)
    conn.modify_s(dn,ldif)

    entries = conn.search_s("cn=member,cn=%s,ou=group,dc=chameleoncloud,dc=org" % str(allocation.name),
                            ldap.SCOPE_BASE,
                            "(objectclass=*)")
    if entries is None:
        print("cannot find existing LDAP member roles for %s" % allocation.name)
        return
    (dn,old) = entries[0]
    # the only thing that can be updated are the roleOccupant
    new = copy.deepcopy(old)
    attrs["roleOccupant"] = map(lambda uid: "cn=%s,ou=people,dc=chameleoncloud,dc=org" %
                                uid,_getMemberUids(allocation))
    ldif = ldap.modlist.modifyModlist(old,new)
    conn.modify_s(dn,ldif)

    conn.unbind_s()

def _addToAllocation(allocation, allocation_request, granted_units, granted_duration):
    allocation.allocation_requests.add(allocation_request)
    allocation.granted_units += granted_units
    allocation.remaining_units += granted_units
    # do this better
    extra_days = int(granted_duration / 12.0 * 365)
    allocation.end_date = allocation.end_date + datetime.timedelta(days=extra_days)
    allocation.save()



def _sendApproveEmail(allocation_request):
    context = {"allocation_request": allocation_request}
    body = loader.render_to_string("allocation/approve_email.txt",context).strip()
    subject = "Chameleon allocation request approved"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,[allocation_request.requester.email])

def _sendDenyEmail(allocation_request):
    context = {"allocation_request": allocation_request}
    body = loader.render_to_string("allocation/deny_email.txt",context).strip()
    subject = "Chameleon allocation request denied"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,[allocation_request.requester.email])

def approve_request(request):
    return render(request,"allocation/review_approve.html")

def deny_request(request):
    return render(request,"allocation/review_deny.html")
