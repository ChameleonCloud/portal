from collections import defaultdict
from django.db import connection
from projects.models import Publication
from projects.pub_utils import PublicationUtils


CHAMELEON_PUBLICATIONS = [
    "lessons learned from the chameleon testbed",
    "chameleon: a large-scale, deeply reconfigurable testbed for computer science research",
    "chameleon@edge community workshop report",
    "operational lessons from chameleon",
    "application-based qos support with p4 and openflow: a demonstration using chameleon",
    "application-based qoe support with p4 and openflow",
    "overcast: running controlled experiments spanning research and commercial clouds",
    "managing allocatable resources",
    "a case for integrating experimental containers with notebooks",
    "managing allocatable resources ( invited paper )",
    "next generation clouds, the chameleon cloud testbed, and software defined networking (sdn)",
    "chi-in-a-box: reducing operational costs of research testbeds",
    "migrating towards single sign-on and federated identity",
]


def get_pi_projects():
    with connection.cursor() as cursor:
        sql = """
            SELECT MIN(first_name) AS first_name, MIN(last_name) AS last_name,
                proj.project_id AS project_id, MIN(charge_code) AS charge_code,
                MIN(a.start_date) AS start_date, MAX(a.expiration_date) AS end_date
            FROM
            (
                SELECT u.first_name, u.last_name, p.id AS project_id, p.charge_code
                FROM auth_user AS u
                JOIN projects_project AS p
                ON u.id = p.pi_id
            ) AS proj
            JOIN allocations_allocation AS a
            ON proj.project_id = a.project_id
            GROUP BY proj.project_id
        """
        cursor.execute(sql)

        pi_projects = defaultdict(list)
        for r in cursor.fetchall():
            first_name = r[0]
            last_name = r[1]
            project_id = r[2]
            charge_code = r[3]
            start_date = r[4]
            end_date = r[5]

            last_name = last_name.rsplit(" ", 1)
            if len(last_name) == 1:
                last_name = last_name[0]
            else:
                last_name = last_name[1]

            # Vijay uses a different name for his publications
            if last_name.lower() == "pillai" and r["first_name"].lower().startswith(
                "vijay"
            ):
                last_name = "chidambaram"

            key = (first_name.lower()[0] + ".", last_name.lower())
            pi_projects[key].append((project_id, charge_code, start_date, end_date))
        return pi_projects


def link_publication_to_project(pi_projects, author_keys, pub_year):
    counter = defaultdict(int)
    for key in author_keys:
        if key in pi_projects:
            for proj in pi_projects[key]:
                proj_id = proj[0]
                proj_charge_code = proj[1]
                allocation_start = proj[2]
                allocation_end = proj[3]
                if (
                    allocation_start
                    and allocation_start.year <= pub_year
                    and allocation_end
                    and allocation_end.year + 1 >= pub_year
                ):
                    counter[(proj_id, proj_charge_code)] += 1

    if counter:
        return max(counter, key=counter.get)
    else:
        return (None, None)


def get_publications():
    result = defaultdict(str)
    for pub in Publication.objects.all():
        result[pub.title] = pub.project_id

    return result


def pub_exists(all_publications, pub_title, pub_project_id):
    for title, proj in all_publications.items():
        if (
            PublicationUtils.how_similar(title.lower(), pub_title.lower()) >= 0.9
            and proj == pub_project_id
        ):
            return True

    return False
