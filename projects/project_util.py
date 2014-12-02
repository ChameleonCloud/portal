from django.db import connections
from projectModel import Project

def list_migration_users( fg_project_num ):
    query_str = """SELECT DISTINCT
                member.name,
                member.mail
                FROM node n
                LEFT JOIN content_type_fg_projects p on p.nid = n.nid
                LEFT JOIN content_field_project_members mem ON mem.nid = n.nid
                LEFT JOIN users member ON mem.field_project_members_uid = member.uid
                WHERE n.type = 'fg_projects'
                AND p.field_projectid_value = %s"""

    cursor = connections['futuregrid'].cursor()
    cursor.execute( query_str, [ fg_project_num ] )
    result_set = cursor.fetchall()
    users = map( lambda u: { 'username': u[0], 'email': u[1] }, result_set )
    return users

def list_migration_projects( user_email ):
    query_str = """SELECT DISTINCT
                u.name,
                n.title,
                p.field_projectid_value,
                p.field_project_abstract_value,
                manager.mail AS manager,
                lead.mail AS lead,
                u.uid = lead.uid OR u.uid = manager.uid AS is_pi
                FROM node n
                LEFT JOIN content_type_fg_projects p on p.nid = n.nid
                LEFT JOIN content_field_project_members mem ON mem.nid = n.nid
                LEFT JOIN users manager on manager.uid = p.field_project_manager_uid
                LEFT JOIN users lead on lead.uid = p.field_project_lead_uid
                LEFT JOIN users member ON mem.field_project_members_uid = member.uid
                LEFT JOIN users u on u.uid = member.uid OR u.uid = lead.uid OR u.uid = manager.uid
                WHERE n.type = 'fg_projects'
                AND u.mail = %s"""

    cursor = connections['futuregrid'].cursor()
    cursor.execute( query_str, [ user_email ] )
    result_set = cursor.fetchall()
    projects = []
    for p in result_set:
        projects.append( Project( p[0], p[1], p[2], p[3], p[4], p[5], p[6] ) )

    return projects
