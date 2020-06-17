from pytas.http import TASClient
import mysql.connector
import logging
import sys
import argparse
import configparser
import os

PORTAL_PROJECT_TABLE_NAME = 'projects_project'
PORTAL_PROJECT_PUBLICATION_TABLE_NAME = 'projects_publication'

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_tas_to_portal_project_id_map(tas, db):
    result = {}
    cursor = db.cursor(dictionary=True)
    
    resp = tas.projects_for_group('Chameleon')
    for proj in resp:
        tas_proj_id = proj['id']
        charge_code = proj['chargeCode']
        if tas_proj_id and charge_code:
            cursor.execute("SELECT id FROM {table} WHERE charge_code = '{charge_code}'".format(table = PORTAL_PROJECT_TABLE_NAME,
                                                                                               charge_code = charge_code))
            portal_proj_id = cursor.fetchone()
            if portal_proj_id:
                result[tas_proj_id] = portal_proj_id['id']
            else:
                logger.warning('Couldn\'t find project with charge code {} in portal'.format(charge_code))
    
    return result

def sync(db, tas_to_portal_project_id_map):
    cursor = db.cursor(dictionary=True)
    update_query = '''UPDATE {table} SET project_id = %s WHERE id = %s'''.format(table = PORTAL_PROJECT_PUBLICATION_TABLE_NAME)
    cursor.execute("SELECT id, tas_project_id FROM {table}".format(table = PORTAL_PROJECT_PUBLICATION_TABLE_NAME))
    for row in cursor.fetchall():
        tas_proj_id = row['tas_project_id']
        if tas_proj_id:
            if tas_proj_id in tas_to_portal_project_id_map:
                try:
                    portal_proj_id = tas_to_portal_project_id_map[tas_proj_id]
                    cursor.execute(update_query, (portal_proj_id, row['id']))
                    db.commit()
                except:
                    logger.exception('failed to update record {} in publication table'.format(row['id']))
            else:
                logger.warning('Counld\'t find mapping from tas project {} to portal project'.format(tas_proj_id))

def main(argv=None):
    if argv is None:
        argv = sys.argv
        
    parser = argparse.ArgumentParser(description='Sync publication in portal')
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
    
    sync(db, get_tas_to_portal_project_id_map(tas, db))

if __name__ == '__main__':
    sys.exit(main(sys.argv))
