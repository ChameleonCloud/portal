import MySQLdb
import json

from django.conf import settings

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def connect_to_region_db(region):
    return MySQLdb.connect(**settings.REGION_OPENSTACK_DB_CONNECT[region])


def connect_to_portal_db():
    db = settings.DATABASES.get("default")
    return MySQLdb.connect(
        host=db.get("HOST"),
        user=db.get("USER"),
        passwd=db.get("PASSWORD"),
        database=db.get("NAME"),
    )


def parse_db_query(query_fetch):
    result = []
    for row in query_fetch:
        extra = json.loads(row["extra"])
        charge_code = extra.get("charge_code")
        if not charge_code:
            charge_code = row["project_name"]
        charge = {
            "username": row["username"],
            "charge_code": charge_code,
            "start_time": row["start_on"].strftime(DATETIME_FORMAT),
            "end_time": row["end_on"].strftime(DATETIME_FORMAT),
            "resource_id": row["resource_id"],
            "resource_type": row["resource_type"],
            "hourly_cost": float(row["hourly_cost"]),
        }
        result.append(charge)
    return result


def get_computehost_charges_by_ids(db, resource_ids=None):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    resource_id_params = "SELECT DISTINCT id FROM blazar.reservations"
    if resource_ids:
        resource_id_params = ",".join(f'"{r}"' for r in resource_ids)
    cursor.execute(
        """
        SELECT lu.name AS username, p.extra, p.name AS project_name,
        start_date AS start_on,
        LEAST(COALESCE(end_date, l.deleted_at, r.deleted_at),
        COALESCE(l.deleted_at, r.deleted_at, end_date),
        COALESCE(r.deleted_at, end_date, l.deleted_at)) AS end_on,
        r.id AS resource_id, r.resource_type,
        COUNT(DISTINCT c.id) *
          (CASE
                WHEN capability_value IS NULL THEN 1.0
                ELSE capability_value
           END) AS hourly_cost
        FROM blazar.leases AS l
        JOIN blazar.reservations AS r ON l.id = r.lease_id
        JOIN blazar.computehost_allocations AS ca ON ca.reservation_id = r.id
        JOIN blazar.computehosts AS c ON c.id = ca.compute_host_id
        JOIN keystone.project AS p ON p.id = l.project_id
        JOIN keystone.user AS u ON u.id = l.user_id
        JOIN keystone.local_user AS lu ON lu.user_id = u.id
        LEFT JOIN (
            SELECT cec.computehost_id, capability_value
            FROM blazar.computehost_extra_capabilities AS cec
            JOIN blazar.extra_capabilities AS ec ON cec.capability_id = ec.id
            WHERE capability_name = 'su_factor'
            AND resource_type = 'physical:host'
        ) AS j ON j.computehost_id = c.id
        WHERE r.id IN ({})
        GROUP BY r.id, capability_value
    """.format(
            resource_id_params
        )
    )

    return parse_db_query(cursor.fetchall())


def get_network_charges_by_ids(db, resource_ids=None):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    resource_id_params = "SELECT DISTINCT id FROM blazar.reservations"
    if resource_ids:
        resource_id_params = ",".join(f'"{r}"' for r in resource_ids)
    cursor.execute(
        """
        SELECT lu.name AS username, p.extra, p.name AS project_name,
        start_date AS start_on,
        LEAST(COALESCE(end_date, l.deleted_at, r.deleted_at),
        COALESCE(l.deleted_at, r.deleted_at, end_date),
        COALESCE(r.deleted_at, end_date, l.deleted_at)) AS end_on,
        r.id AS resource_id, r.resource_type,
        COUNT(DISTINCT n.id) *
            (CASE
                WHEN capability_value IS NULL THEN 1.0
                ELSE capability_value
           END) AS hourly_cost
        FROM blazar.leases AS l
        JOIN blazar.reservations AS r ON l.id = r.lease_id
        JOIN blazar.network_allocations AS na ON na.reservation_id = r.id
        JOIN blazar.network_segments AS n ON n.id = na.network_id
        JOIN keystone.project AS p ON p.id = l.project_id
        JOIN keystone.user AS u ON u.id = l.user_id
        JOIN keystone.local_user AS lu ON lu.user_id = u.id
        LEFT JOIN (
            SELECT nec.network_id, capability_value
            FROM blazar.networksegment_extra_capabilities AS nec
            JOIN blazar.extra_capabilities AS ec ON nec.network_id = ec.id
            WHERE capability_name = 'su_factor'
            AND resource_type = 'network'
        ) AS j ON j.network_id = n.id
        WHERE r.id IN ({})
        GROUP BY r.id, capability_value
    """.format(
            resource_id_params
        )
    )

    return parse_db_query(cursor.fetchall())


def get_floatingip_charges_by_ids(db, resource_ids=None):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    resource_id_params = "SELECT DISTINCT id FROM blazar.reservations"
    if resource_ids:
        resource_id_params = ",".join(f'"{r}"' for r in resource_ids)
    cursor.execute(
        """
        SELECT lu.name AS username, p.extra, p.name AS project_name,
        start_date AS start_on,
        LEAST(COALESCE(end_date, l.deleted_at, r.deleted_at),
        COALESCE(l.deleted_at, r.deleted_at, end_date),
        COALESCE(r.deleted_at, end_date, l.deleted_at)) AS end_on,
        r.id AS resource_id, r.resource_type, COUNT(DISTINCT f.id) AS hourly_cost
        FROM blazar.leases AS l
        JOIN blazar.reservations AS r ON l.id = r.lease_id
        JOIN blazar.floatingip_allocations AS fa ON fa.reservation_id = r.id
        JOIN blazar.floatingips AS f ON f.id = fa.floatingip_id
        JOIN keystone.project AS p ON p.id = l.project_id
        JOIN keystone.user AS u ON u.id = l.user_id
        JOIN keystone.local_user AS lu ON lu.user_id = u.id
        WHERE r.id IN ({})
        GROUP BY r.id
    """.format(
            resource_id_params
        )
    )

    return parse_db_query(cursor.fetchall())


def get_resource_id(
    db, project_id, user_id, lease_start_date, resource_type, lease_name
):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        """
        SELECT r.id AS id
        FROM blazar.leases AS l
        JOIN blazar.reservations AS r ON l.id = r.lease_id
        WHERE project_id = %(project_id)s
        AND user_id = %(user_id)s
        AND start_date = %(start_date)s
        AND resource_type = %(resource_type)s
        AND name = %(lease_name)s
        """,
        {
            "project_id": project_id,
            "user_id": user_id,
            "start_date": lease_start_date,
            "resource_type": resource_type,
            "lease_name": lease_name,
        },
    )
    resource_id = cursor.fetchone()
    if resource_id:
        return resource_id.get("id")
    else:
        return None
