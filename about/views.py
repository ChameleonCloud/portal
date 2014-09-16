from django.shortcuts import render
from django.views import generic

from about.models import TeamRole,TeamMember


def about(request):
    context = {"team_members": TeamMember.objects.all()}
    return render(request, 'about/index.html', context)

def schedule(request):
    return render(request, 'about/schedule.html', {})

def teamMembers(request):
    NUM_COLUMNS = 3
    rows = []
    members = TeamMember.objects.all()
    while len(members) > 3:
        rows.append(members[:3])
        members = members[3:]
    if len(members) > 0:
        rows.append(members)

    context = {"members": rows}
    print("rows: %s" % rows)

    return render(request, 'about/team/members.html', context)

class TeamMembersView(generic.ListView):
    model = TeamMember
    context_object_name = "members"
    template_name = "about/team/members.html"

class TeamMemberView(generic.DetailView):
    model = TeamMember
    context_object_name = "member"
    template_name = "about/team/member.html"
