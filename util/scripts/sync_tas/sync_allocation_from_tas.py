import argparse
import configparser
import logging
import os
import sys
from datetime import datetime

import mysql.connector
import pytz
from pytas.http import TASClient

sys.path.append("../..")
from consts.allocation import TAS_DATE_FORMAT, TAS_TO_PORTAL_MAP

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PORTAL_ALLOCATION_TABLE_NAME = "allocations_allocation"
PORTAL_AUTH_USER_TABLE_NAME = "auth_user"
PORTAL_PROJECT_TABLE_NAME = "projects_project"

REQUIRED_FIELDS = ["project_id", "status", "date_requested", "su_requested"]
ALLOCATION_ID_KEYS = ["project_id", "requestor_id", "justification", "date_requested"]


def init_reformated_alloc():
    alloc = {"project_id": None}
    for key in list(TAS_TO_PORTAL_MAP.values()):
        alloc[key] = None

    return alloc


def is_reformated_alloc_missing_required_fields(alloc):
    for key in REQUIRED_FIELDS:
        if not alloc[key]:
            return True

    return False


tas_users = {}


def get_tas_user(tas, id):
    if id not in tas_users:
        tas_users[id] = tas.get_user(id=id)
    return tas_users[id]


def alloc_equals(portal_alloc, tas_alloc):
    return all(
        tas_alloc.get(key) == portal_alloc.get(key) for key in ALLOCATION_ID_KEYS
    )


def alloc_delta(portal_alloc, tas_alloc):
    """Compute the difference between a Portal and a TAS allocation."""
    ignored_keys = ALLOCATION_ID_KEYS + ["id"]
    return {
        key: tas_alloc.get(key)
        for key in list(tas_alloc.keys())
        if key not in ignored_keys and portal_alloc.get(key) != tas_alloc.get(key)
    }


def get_allocations_from_tas(tas, db):
    result = []
    cursor = db.cursor(dictionary=True)

    resp = tas.projects_for_group("Chameleon")
    for p in resp:
        for a in p["allocations"]:
            if a["resource"] == "Chameleon":
                reformated_a = init_reformated_alloc()
                for key, val in list(a.items()):
                    if key == "project":
                        cursor.execute(
                            "SELECT id FROM {table} WHERE charge_code = '{charge_code}'".format(
                                table=PORTAL_PROJECT_TABLE_NAME, charge_code=a[key]
                            )
                        )
                        project = cursor.fetchone()
                        if project:
                            reformated_a["project_id"] = project["id"]
                        else:
                            logger.warning(
                                "can not find project with charge_code {} in portal".format(
                                    a[key]
                                )
                            )
                        continue
                    if key in TAS_TO_PORTAL_MAP:
                        if key == "status":
                            val = val.lower()
                        if key == "requestorId" or key == "reviewerId":
                            if a[key] == 0 or a[key] == None:
                                val = None
                            else:
                                # convert TAS user id to portal user id
                                username = get_tas_user(tas, a[key])["username"]
                                cursor.execute(
                                    "SELECT id FROM {table} WHERE username = '{username}'".format(
                                        table=PORTAL_AUTH_USER_TABLE_NAME,
                                        username=username,
                                    )
                                )
                                portal_user = cursor.fetchone()
                                if portal_user:
                                    val = portal_user["id"]
                                else:
                                    logger.warning(
                                        "can not find user with username {} in portal".format(
                                            username
                                        )
                                    )
                                    val = None
                        try:
                            val = datetime.strptime(val, TAS_DATE_FORMAT)
                            val = (
                                pytz.timezone("America/Chicago")
                                .localize(val, is_dst=None)
                                .astimezone(pytz.utc)
                            )
                        except:
                            pass
                        reformated_a[TAS_TO_PORTAL_MAP[key]] = val
                if is_reformated_alloc_missing_required_fields(reformated_a):
                    logger.warning(
                        "TAS allocation is missing required fields: {}".format(a)
                    )
                else:
                    result.append(reformated_a)

    logger.info("TAS has {} records".format(len(result)))

    return result


def get_allocations_from_portal(db):
    result = []
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM {}".format(PORTAL_ALLOCATION_TABLE_NAME))
    for alloc in cursor.fetchall():
        for key, val in list(alloc.items()):
            if isinstance(val, datetime):
                alloc[key] = val.replace(tzinfo=pytz.UTC)
        result.append(alloc)

    logger.info("Portal has {} records".format(len(result)))

    return result


def sync(db, tas_allocs, portal_allocs):
    records_to_insert = []
    records_to_update = []
    columns = None

    for tas_alloc in tas_allocs:
        if not columns:
            columns = list(tas_alloc.keys())
        compare_tas_alloc = {}
        for key in list(tas_alloc.keys()):
            if key in ALLOCATION_ID_KEYS:
                compare_tas_alloc[key] = tas_alloc[key]
        exist = False
        for portal_alloc in portal_allocs:
            if alloc_equals(portal_alloc, tas_alloc):
                exist = True
                delta = alloc_delta(portal_alloc, tas_alloc)
                if delta:
                    alloc_values = [
                        tas_alloc[key] for key in sorted(tas_alloc.keys())
                    ] + [portal_alloc["id"]]
                    records_to_update.append(alloc_values)
                break
        if not exist:
            alloc_values = [tas_alloc[key] for key in sorted(tas_alloc.keys())]
            records_to_insert.append(tuple(alloc_values))

    cursor = db.cursor()

    insert_query = """INSERT INTO {table} ({columns})
                      VALUES ({variable})""".format(
        table=PORTAL_ALLOCATION_TABLE_NAME,
        columns=",".join(sorted(columns)),
        variable=",".join(["%s"] * len(columns)),
    )
    cursor.executemany(insert_query, records_to_insert)
    db.commit()
    logger.info("inserted {} records to portal".format(len(records_to_insert)))

    values = []
    for c in sorted(columns):
        values.append("{}=%s".format(c))
    update_query = """UPDATE {table} SET {variables} WHERE id = %s""".format(
        table=PORTAL_ALLOCATION_TABLE_NAME, variables=",".join(values)
    )
    cursor.executemany(update_query, records_to_update)
    db.commit()
    logger.info("updated {} records in portal".format(len(records_to_update)))


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(description="Sync allocation from TAS to portal")
    parser.add_argument(
        "--config", type=str, help="Config file path name", required=True
    )
    parser.add_argument(
        "--portal-db", type=str, help="Portal database name", default="chameleon_dev"
    )

    args = parser.parse_args(argv[1:])
    conf = configparser.SafeConfigParser(os.environ)
    conf.read(args.config)

    db = mysql.connector.connect(
        host=conf.get("portal", "host"),
        user=conf.get("portal", "username"),
        passwd=conf.get("portal", "password"),
        database=args.portal_db,
    )
    tas = TASClient(
        baseURL=conf.get("tas", "url"),
        credentials={
            "username": conf.get("tas", "client_key"),
            "password": conf.get("tas", "client_secret"),
        },
    )

    sync(db, get_allocations_from_tas(tas, db), get_allocations_from_portal(db))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
