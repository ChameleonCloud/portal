from pytas.http import TASClient
import mysql.connector
import logging
import sys
import argparse
import configparser
import os

sys.path.append("../..") 
from consts.project import TAS_TO_PORTAL_MAP

PORTAL_PROJECT_TABLE_NAME = 'projects_project'
PORTAL_TYPE_TABLE_NAME = 'projects_type'
PORTAL_FIELD_TABLE_NAME = 'projects_field'
PORTAL_AUTH_USER_TABLE_NAME = 'auth_user'
PORTAL_PROJECT_EXTRA_TABLE_NAME = 'projects_projectextras'
PORTAL_FIELD_HIERARCHY_TABLE_NAME = 'projects_fieldhierarchy'
IGNORED_TAS_FIELDS = ['typeId', 'fieldId']
REQUIRED_FIELDS = ['type_id', 'description', 'pi_id', 'title', 'charge_code', 'nickname']

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def init_reformated_project():
    ignored_tas_keys = ['field', 'type'] # portal project requires ids instead of names
    proj = {}
    for tas_key, portal_key in TAS_TO_PORTAL_MAP.items():
        if tas_key in ignored_tas_keys:
            continue
        proj[portal_key] = None
        
    return proj

def is_reformated_project_missing_required_fields(proj):
    for key in REQUIRED_FIELDS:
        if not proj[key]:
            return True
        
    return False

def get_projects_from_tas(tas, db):
    result = {}
    type_name_to_id = get_types_from_portal(db)
    field_name_to_id = get_fields_from_portal(db)
    cursor = db.cursor(dictionary=True)
    
    resp = tas.projects_for_group('Chameleon')
    for proj in resp:
        reformated_proj = init_reformated_project()
        tas_proj_id = None
        tas_proj_nickname = None
        for key, val in proj.items():
            if key == 'id':
                tas_proj_id = val
            if key == 'nickname':
                tas_proj_nickname = val
            if key in TAS_TO_PORTAL_MAP and key not in IGNORED_TAS_FIELDS:
                if key == 'type':
                    # see if exists in portal db
                    if val not in type_name_to_id:
                        cursor.execute("INSERT INTO {table} (name) VALUES ('{val}')".format(table = PORTAL_TYPE_TABLE_NAME,
                                                                                            val = val))
                        db.commit()
                        type_name_to_id[val] = cursor.lastrowid
                    reformated_proj['type_id'] = type_name_to_id[val]
                    continue
                if key == 'field':
                    # see if exists in portal db
                    if val and val not in field_name_to_id:
                        cursor.execute("INSERT INTO {table} (name) VALUES ('{val}')".format(table = PORTAL_FIELD_TABLE_NAME,
                                                                                            val = val))
                        db.commit()
                        field_name_to_id[val] = cursor.lastrowid
                    reformated_proj['field_id'] = field_name_to_id[val]
                    continue
                if key == 'piId':
                    # convert TAS user id to portal user id
                    username = tas.get_user(id=proj[key])['username']
                    cursor.execute("SELECT id FROM {table} WHERE username = '{username}'".format(table = PORTAL_AUTH_USER_TABLE_NAME,
                                                                                                 username = username))
                    portal_user = cursor.fetchone()
                    if portal_user:
                        val = portal_user['id']
                    else:
                        logger.warning('can not find user with username {} in portal'.format(username))
                        val = None
                reformated_proj[TAS_TO_PORTAL_MAP[key]] = val
        # get nickname
        if tas_proj_nickname:
            reformated_proj['nickname'] = tas_proj_nickname
        elif tas_proj_id:
            cursor.execute("SELECT nickname FROM {table} WHERE tas_project_id = '{tas_project_id}'".format(table = PORTAL_PROJECT_EXTRA_TABLE_NAME,
                                                                                                           tas_project_id = tas_proj_id))
            nickname = cursor.fetchone()
            if nickname:
                reformated_proj['nickname'] = nickname['nickname']
            else:
                reformated_proj['nickname'] = reformated_proj['charge_code']
                logger.warning('No nickname found in portal for project with tas id {}. The charge code will be used.'.format(tas_proj_id))
        if is_reformated_project_missing_required_fields(reformated_proj):
            logger.warning('TAS project is missing required fields: {}'.format(proj))
        else:
            result[reformated_proj['charge_code']] = reformated_proj
    
    logger.info('TAS has {} records'.format(len(result)))
    
    return result

def get_projects_from_portal(db):
    result = {}
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM {}".format(PORTAL_PROJECT_TABLE_NAME))
    for proj in cursor.fetchall():
        result[proj['charge_code']] = proj
        
    logger.info('Portal has {} records'.format(len(result)))
        
    return result

def sync(db, tas_projects, portal_projects):
    records_to_insert = []
    records_to_update = []
    columns = None
    
    for proj_charge_code in tas_projects.keys():
        if not columns: columns = tas_projects[proj_charge_code].keys()
        if proj_charge_code in portal_projects:
            portal_proj_id = portal_projects[proj_charge_code]['id']
            del portal_projects[proj_charge_code]['id']
            if tas_projects[proj_charge_code] != portal_projects[proj_charge_code]:
                proj_values = [tas_projects[proj_charge_code][key] for key in sorted(tas_projects[proj_charge_code].keys())]
                proj_values.append(portal_proj_id)
                records_to_update.append(tuple(proj_values))
        else:
            proj_values = [tas_projects[proj_charge_code][key] for key in sorted(tas_projects[proj_charge_code].keys())]
            records_to_insert.append(tuple(proj_values))
        
    cursor = db.cursor()
    
    if columns:
        insert_query = '''INSERT INTO {table} ({columns}) 
                          VALUES ({variable})'''.format(table = PORTAL_PROJECT_TABLE_NAME,
                                                        columns = ','.join(sorted(columns)),
                                                        variable = ','.join(['%s'] * len(columns)))
        cursor.executemany(insert_query, records_to_insert)
        db.commit()    
    logger.info('inserted {} records to portal'.format(len(records_to_insert)))
    
    if columns:
        values = []
        for c in sorted(columns):
            values.append('{}=%s'.format(c))
        update_query = '''UPDATE {table} SET {variables} WHERE id = %s'''.format(table = PORTAL_PROJECT_TABLE_NAME,
                                                                                 variables = ','.join(values))
        cursor.executemany(update_query, records_to_update)
        db.commit()    
    logger.info('updated {} records in portal'.format(len(records_to_update)))
                
def get_types_from_portal(db):
    result = {}
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM {table}".format(table = PORTAL_TYPE_TABLE_NAME))
    for ptype in cursor.fetchall():
        result[ptype['name']] = ptype['id']
    
    return result

def parse_field_recursive(parent):
    result = []
    for child in parent['children']:
        result.append((parent['name'], child['name']))
        result = result + parse_field_recursive(child)
    return result
    
def sync_fields_from_tas(tas, db):
    cursor = db.cursor()
    parent_child_tuple_list = []
    fields = tas.fields()
    for f in fields:
        parent_child_tuple_list = parent_child_tuple_list + parse_field_recursive(f)
        
    # insert fields into field table
    field_names = set()
    for item in parent_child_tuple_list:
        field_names.add('(\'{}\')'.format(item[0]))
        field_names.add('(\'{}\')'.format(item[1]))
    cursor.execute('''INSERT IGNORE INTO {table} (name) VALUES {values}'''.format(table = PORTAL_FIELD_TABLE_NAME,
                                                                                  values = ','.join(field_names)))
    db.commit()
    
    # get fields from portal
    portal_field_name_to_id_map = get_fields_from_portal(db)
    
    # insert field hierarchy
    field_parent_child_id_pairs = set()
    for item in parent_child_tuple_list:
        parent_id = portal_field_name_to_id_map[item[0]]
        child_id = portal_field_name_to_id_map[item[1]]
        field_parent_child_id_pairs.add('({},{})'.format(parent_id, child_id))
    cursor.execute('''INSERT IGNORE INTO {table} (parent_id, child_id) VALUES {values}'''.format(table = PORTAL_FIELD_HIERARCHY_TABLE_NAME,
                                                                                                 values = ','.join(field_parent_child_id_pairs)))
    db.commit()

def get_fields_from_portal(db):
    result = {}
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM {table}".format(table = PORTAL_FIELD_TABLE_NAME))
    for field in cursor.fetchall():
        result[field['name']] = field['id']
    
    return result

def main(argv=None):
    if argv is None:
        argv = sys.argv
        
    parser = argparse.ArgumentParser(description='Sync project from TAS to portal')
    parser.add_argument('--config', type=str, help='Config file path name', required=True)
    parser.add_argument('--portal-db', type=str, help='Portal database name', default='chameleon_dev')

    args = parser.parse_args(argv[1:])
    conf = configparser.SafeConfigParser(os.environ)
    conf.read(args.config)
    
    db = mysql.connector.connect(host=conf.get('portal', 'host'),
                                 user=conf.get('portal', 'username'),
                                 passwd=conf.get('portal', 'password'),
                                 database = args.portal_db)
    tas = TASClient(baseURL=conf.get('tas', 'url'), 
                    credentials={'username': conf.get('tas', 'client_key'), 'password': conf.get('tas', 'client_secret')})
    
    sync_fields_from_tas(tas, db)
    sync(db, get_projects_from_tas(tas, db), get_projects_from_portal(db))

if __name__ == '__main__':
    sys.exit(main(sys.argv))
