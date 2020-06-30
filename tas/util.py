from pytas.models import Project


def get_user_projects(username):
    all_user_projects = [
        p for p in Project.list(username=username)
        if p.source == 'Chameleon'
    ]
    active = [
        p for p in all_user_projects
        if (a.status in ['Active'] for a in p.allocations)
    ]
    approved = [
        p for p in all_user_projects
        if (a.status in ['Approved'] for a in p.allocations)
    ]
    return active, approved
