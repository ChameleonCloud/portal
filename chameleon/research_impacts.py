from difflib import SequenceMatcher
from django.contrib.auth.models import User
from chameleon.models import PIEligibility
from projects.models import Project, Publication, Tag
from datetime import datetime, timedelta
from django.db.models import Sum, FloatField, Count, Q, F, DurationField
from django.db.models.functions import TruncYear
from allocations.models import Charge, Allocation
from util.keycloak_client import KeycloakClient
from projects.util import get_project_members
from collections import defaultdict
import functools

import logging

from .constants import (
    MSI_UNIVERFSITY_LIST,
    UNI_STATE_LIST,
    allocation_statuses,
    EPSCOR_STATES,
)

import pytz
import statistics

UTC = pytz.UTC
LOG = logging.getLogger(__name__)


def institution_report():
    kcc = KeycloakClient()
    kcc_users = kcc.get_all_users_attributes()

    @functools.lru_cache()
    def similarity_score(str1, str2):
        ratio = SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
        return ratio

    edu_users = get_education_users()
    insts = set()
    edu_insts = set()
    for u in kcc_users:
        user = kcc_users[u]
        if not user:
            continue
        inst = user.get("affiliationInstitution", "")
        if isinstance(inst, list):
            inst = " || ".join(inst)
        insts.add(inst.lower())
        if user.get("username") in edu_users:
            edu_insts.add(inst.lower())

    MSI_UNI_SET = set(MSI_UNIVERFSITY_LIST)
    msi_found = set()
    for inst in insts:
        if inst in MSI_UNI_SET:
            msi_found.add(inst)
        else:
            max_score = 0
            # university names are submitted by users and often contain typos
            # check if they are 90% similar to the list of MSI institutes
            for uni in MSI_UNIVERFSITY_LIST:
                score = similarity_score(inst, uni)
                if score > max_score:
                    max_score = score
                    match_found = uni
            if max_score > 0.9:
                msi_found.add(match_found)
    edu_msi_found = msi_found.intersection(edu_insts)

    states = set()
    for uni in UNI_STATE_LIST:
        if uni["name"] in insts:
            states.add(uni["state"])
    epscor_states = set(s for s in states if s in EPSCOR_STATES)

    edu_states = set()
    for uni in UNI_STATE_LIST:
        if uni["name"] in edu_insts:
            edu_states.add(uni["state"])
    edu_epscor_states = set(s for s in edu_states if s in EPSCOR_STATES)

    return {
        "total": len(insts),
        "msi_total": len(msi_found),
        "states": len(states),
        "epscor_states": len(epscor_states),
        "edu_total": len(edu_insts),
        "edu_msi_total": len(edu_msi_found),
        "edu_states": len(edu_states),
        "edu_epscor_states": len(edu_epscor_states),
    }


def _allocation_counts(projects):
    allocation_counts = []
    # For projects that were active at one point
    for p in projects:
        allocation_counts.append(
            p.allocations.filter(status__in=allocation_statuses).count()
        )
    return allocation_counts


def extension_information():
    computing_education_tag = Tag.objects.get(name="Computing Education")

    allocation_counts = _allocation_counts(
        Project.objects.filter(allocations__status__in=allocation_statuses)
    )
    max_allocations = max(allocation_counts, default=0)
    med_allocations = statistics.median(allocation_counts)
    percentage_extended = (
        len(list(ac for ac in allocation_counts if ac > 1))
        / float(len(allocation_counts))
        * 100
    )

    education_allocation_counts = _allocation_counts(
        Project.objects.filter(
            allocations__status__in=allocation_statuses, tag=computing_education_tag
        )
    )
    edu_max_allocations = max(education_allocation_counts, default=0)
    edu_med_allocations = statistics.median(education_allocation_counts)
    edu_percentage_extended = (
        len(list(ac for ac in education_allocation_counts if ac > 1))
        / float(len(education_allocation_counts))
        * 100
    )

    return {
        "max": max_allocations,
        "median": med_allocations,
        "extended_percentage": percentage_extended,
        "edu_max": edu_max_allocations,
        "edu_median": edu_med_allocations,
        "edu_extended_percentage": edu_percentage_extended,
    }


def pi_report(start_year, end_year):
    report = []
    for year in range(start_year, end_year):
        current_year = datetime(year=year, month=1, day=1)
        current_year = current_year.replace(tzinfo=UTC)
        year_end = current_year.replace(year=year + 1)

        pis = PIEligibility.objects.filter(
            request_date__gte=current_year,
            request_date__lt=year_end,
            status="ELIGIBLE",
        ).count()
        report.append((year, pis))
    return report


def tag_information():
    active_projects = list(
        Project.objects.filter(allocations__status__in=allocation_statuses).all()
    )

    tags_by_count = []
    for tag in Tag.objects.annotate(
        project_count=Count("projects", filter=Q(projects__in=active_projects))
    ):
        tags_by_count.append((tag.name, tag.project_count))
    sorted_tags = sorted(tags_by_count, key=lambda tup: tup[1], reverse=True)

    return {
        "by_count": sorted_tags,
    }


def get_context():
    start_year = 2015
    end_year = datetime.now().year + 1

    computing_education_tag = Tag.objects.get(name="Computing Education")
    tags = {
        "edge": Tag.objects.get(name="Edge Computing"),
        "education": computing_education_tag,
    }

    active_projects_per_year = []
    total_unique_projects_per_tag = {
        name: Project.objects.filter(
            allocations__status__in=allocation_statuses, tag=tag
        )
        .distinct()
        .count()
        for name, tag in tags.items()
    }
    active_projects_per_year_per_tag = defaultdict(list)
    active_education_projects_per_academic_year = []
    for year in range(2020, end_year):
        current_year = datetime(year=year, month=1, day=1)
        current_year = current_year.replace(tzinfo=UTC)
        year_end = current_year.replace(year=year + 1)
        # Query to filter projects with active allocations in the current year
        projects_with_active_allocations = Project.objects.filter(
            allocations__status__in=allocation_statuses,
            allocations__start_date__lte=year_end,
            allocations__expiration_date__gte=current_year,
        ).distinct()
        active_projects_per_year.append(
            (year, projects_with_active_allocations.count())
        )

        for name, tag in tags.items():
            active_projects_per_year_per_tag[name].append(
                (
                    year,
                    Project.objects.filter(
                        allocations__status__in=allocation_statuses,
                        allocations__start_date__lte=year_end,
                        allocations__expiration_date__gte=current_year,
                        tag=tag,
                    )
                    .distinct()
                    .count(),
                )
            )

        academic_current_year = datetime(year=year, month=7, day=1)
        academic_current_year = academic_current_year.replace(tzinfo=UTC)
        academic_year_end = academic_current_year.replace(year=year + 1)
        ay_education_projects_with_active_allocations = Project.objects.filter(
            allocations__status__in=allocation_statuses,
            allocations__start_date__lte=academic_year_end,
            allocations__expiration_date__gte=academic_current_year,
            tag=computing_education_tag,
        ).distinct()
        active_education_projects_per_academic_year.append(
            (
                f"Fall {year} - Spring {year+1}",
                ay_education_projects_with_active_allocations.count(),
            )
        )

    publications_per_year = publication_information(start_year, end_year)

    edu_users = get_education_users()

    return {
        "project_count": Project.objects.filter(
            allocations__status__in=allocation_statuses,
        ).count(),
        "total_active_projects": sum(a[1] for a in active_projects_per_year),
        "active_projects_per_year": active_projects_per_year,
        "total_publications": sum(a[1] for a in publications_per_year),
        "publications_per_year": publications_per_year,
        "citations": citation_report(),
        "active_projects_per_year_per_tag": active_projects_per_year_per_tag,
        "active_education_projects_per_academic_year": active_education_projects_per_academic_year,
        "total_unique_projects_per_tag": total_unique_projects_per_tag,
        "extensions": extension_information(),
        "pis_per_year": pi_report(start_year, end_year),
        "tags": tag_information(),
        "edu_users": len(edu_users),
    }


def get_institution_context():
    return {
        "institutions": institution_report(),
    }


def get_sus_context():
    start_year = 2015
    end_year = datetime.now().year + 1

    su_usage_data = su_information(start_year, end_year)
    new_data = {}
    all_sum = 0
    for k, v in su_usage_data.items():
        new_data[k] = dict(v)
        for n in v.values():
            all_sum += n
    new_data["Total"] = {all_sum: ""}
    return {
        "su_usage_data": new_data,
    }


def get_education_users():
    computing_education_tag = Tag.objects.get(name="Computing Education")
    edu_users = set()
    all_active_edu_projects = Project.objects.filter(
        allocations__status__in=allocation_statuses,
        tag=computing_education_tag,
    )
    for p in all_active_edu_projects:
        for u in get_project_members(p):
            edu_users.add(u.username)
    return edu_users


def su_information(start_year, end_year):
    su_usage_data = {}

    for year in range(start_year, end_year + 1):
        # Calculate SU usage
        sus = (
            Charge.objects.filter(start_time__year=year)
            .annotate(duration=F("end_time") - F("start_time"))
            .values("region_name", "duration", "hourly_cost")
        )
        total_su = defaultdict(int)
        total_su_all = 0
        for su in sus:
            cost = su["duration"].total_seconds() / 3600 * su["hourly_cost"]
            total_su[su["region_name"]] += cost
            total_su_all += cost
        total_su["All Sites"] = total_su_all
        # Append data to the dictionary
        su_usage_data[year] = total_su
    return su_usage_data


def publication_information(start_year, end_year):
    publications_per_year = []
    for year in range(start_year, end_year):
        pub_count = Publication.objects.filter(
            year=year, status=Publication.STATUS_APPROVED
        ).count()
        publications_per_year.append((year, pub_count))
    return publications_per_year


def citation_report():
    publications = []
    for p in Publication.objects.filter(status=Publication.STATUS_APPROVED):
        publications.append(
            (p, max((s.citation_count for s in p.sources.all()), default=0))
        )
    total = sum(p[1] for p in publications)
    gt100_unsorted = [
        (f"{p[0].project} - {p[0].title}", p[1]) for p in publications if p[1] >= 100
    ]
    gt100 = sorted(gt100_unsorted, key=lambda tup: tup[1], reverse=True)
    return {
        "total": total,
        "gt100": gt100,
    }
