from collections import namedtuple
import datetime
import logging
import re
import unicodedata
from difflib import SequenceMatcher

import pytz
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from projects.models import RawPublication
from util.keycloak_client import KeycloakClient

LOG = logging.getLogger(__name__)

PUBLICATION_REPORT_KEYS = [
    "id",
    "title",
    "publication_type",
    "forum",
    "year",
    "month",
    "author",
    "bibtex_source",
    "link",
    "doi",
    "source",
    "author_usernames",
    "valid_projects",
    "projects",
    "reason",
]


def get_publications_with_same_attributes(pub, publication_model_class):
    # return publications with exact title, forum, author and year OR same DOI
    similar_pub = publication_model_class.objects.filter(
        Q(
            title__iexact=pub.title,
            forum__iexact=pub.forum,
            author__iexact=pub.author,
            year=pub.year,
        )
        | Q(doi__iexact=pub.doi)
    )

    if not similar_pub.exists():
        # Fallback: try matching by DOI only
        similar_pub = publication_model_class.objects.filter(doi__iexact=pub.doi)

    # Order results: approved first, then others. Return as a list so the
    # caller can rely on ordering.
    approved = similar_pub.filter(status=publication_model_class.STATUS_APPROVED)
    others = similar_pub.exclude(
        status=publication_model_class.STATUS_APPROVED
    ).exclude(status="DUPLICATE")
    # Evaluate querysets into lists to preserve order
    return list(approved) + list(others)


def add_source_to_pub(pub, raw_pub):
    LOG.info(
        f"Publication already exists - {pub.id} - {pub.title} - adding other source - {raw_pub.source_name}"
    )
    with transaction.atomic():
        # Match by exist source ID first
        # Fallback to source_name (legacy data)
        # Otherwise create
        source = RawPublication.objects.filter(source_id=raw_pub.source_id).first()
        if not source:
            source = RawPublication.objects.filter(
                name=raw_pub.source_name, publication=pub
            ).first()
        if not source:
            source = RawPublication.from_publication(pub, raw_pub.source_name)
            source.name = raw_pub.source_name

        source.source_id = raw_pub.source_id
        source.is_found_by_algorithm = True

        source.cites_chameleon = True
        # Adding source to a publication only when it already exists is a valid publication with project in chameleon
        if pub.status == pub.STATUS_APPROVED:
            source.approved_with = source.APPROVED_WITH_PUBLICATION
        else:
            source.approved_with = None
        source.save()

        if (
            raw_pub.cites_chameleon_pub
            and not source.chameleon_publications.filter(
                pk=raw_pub.cites_chameleon_pub.pk
            ).exists()
        ):
            source.chameleon_publications.add(raw_pub.cites_chameleon_pub)
            source.save()

        if (
            raw_pub.found_with_query
            and not source.publication_queries.filter(
                pk=raw_pub.found_with_query.pk
            ).exists()
        ):
            source.publication_queries.add(raw_pub.found_with_query)
            source.save()


def decode_unicode_text(en_text):
    # for texts with unicode chars - accented chars replace them with eq ASCII
    # to perform LIKE operation to database
    de_text = (
        unicodedata.normalize("NFKD", en_text).encode("ascii", "ignore").decode("ascii")
    )
    if en_text != de_text:
        LOG.debug(f"decoding - {en_text} to {de_text}")
    return de_text


def get_projects_of_users(usernames):
    kcc = KeycloakClient()
    projects = []
    for username in usernames:
        projects.extend(kcc.get_user_projects_by_username(username))
    return projects


def is_project_prior_to_publication(project, pub_year):
    fake_start = datetime.datetime(year=9999, month=1, day=1, tzinfo=pytz.UTC)
    # Consider the runtime of a project to be the start of its first allocation
    # until the end of its last allocation
    try:
        start = min(
            alloc.start_date or fake_start for alloc in project.allocations.all()
        )
    except ValueError:
        # In case project doesn't have any allocations
        start = fake_start
    # if project's allocation is prior to publication year
    if start.year <= pub_year:
        return True
    return False


def get_usernames_for_author(author):
    from projects.models import ProjectPIAlias

    name_filter = Q()
    author = decode_unicode_text(author)
    try:
        first_name, *_, last_name = author.rsplit(" ", 1)
    except ValueError:
        # There are some authors on semantic scholar with only a last name
        name_filter = Q(last_name=author)
    else:
        name_filter = Q(first_name__iexact=first_name, last_name__iexact=last_name)
    # Aliases for PI are in the PIAliases table. Get the users with aliases
    # in PI aliases table
    aliases = ProjectPIAlias.objects.filter(alias__iexact=author)
    for alias in aliases.all():
        name_filter |= Q(
            first_name__iexact=alias.pi.first_name,
            last_name__iexact=alias.pi.last_name,
        )
    users = User.objects.filter(name_filter)
    return [user.username for user in users]


def format_author_name(author):
    """Parse author by stripping off the spaces
    and joining as "firstname lastname" instead of "lastname, firstname"
    returns arg:author is only single name is passed

    Args:
        author (str): author name in "lastname, firstname" format

    Returns:
        str: Name of the author in "firstname lastname"
    """
    names = [name.strip() for name in author.split(",")]
    if len(names) > 1:
        return f"{names[1]} {names[0]}"
    else:
        return names[0]


RawPublicationSource = namedtuple(
    "RawPublicationSource",
    field_names=(
        "source_name",
        "source_id",
        "pub_model",
        "cites_chameleon_pub",
        "found_with_query",
    ),
)


class PublicationUtils:
    # ratio threshold from difflib.SequenceMatcher for publication titles
    SIMILARITY_THRESHOLD = 0.9
    PUB_TITLE_DUPLICATE_CHECK_SIMILARITY_THRESHOLD = 0.7

    @staticmethod
    def get_month(bibtex_entry):
        month = bibtex_entry.get("month")
        m = None
        try:
            m = int(month)
        except Exception:
            pass
        try:
            m = datetime.datetime.strptime(month, "%b").month
        except Exception:
            pass
        try:
            m = datetime.datetime.strptime(month, "%B").month
        except Exception:
            pass

        return m

    @staticmethod
    def get_forum(bibtex_entry):
        forum = []
        if "journal" in bibtex_entry:
            forum.append(bibtex_entry["journal"])
        if "booktitle" in bibtex_entry:
            forum.append(bibtex_entry["booktitle"])
        if "series" in bibtex_entry:
            forum.append(bibtex_entry["series"])
        if "publisher" in bibtex_entry:
            forum.append(bibtex_entry["publisher"])
        if "school" in bibtex_entry:
            forum.append(bibtex_entry["school"])
        if "institution" in bibtex_entry:
            forum.append(bibtex_entry["institution"])
        if "address" in bibtex_entry:
            forum.append(bibtex_entry["address"])
        return ",".join(forum)

    @staticmethod
    def get_link(bibtex_entry):
        if "url" in bibtex_entry:
            return bibtex_entry.get("url")
        if "doi" in bibtex_entry:
            return "https://doi.org/" + bibtex_entry.get("doi")
        if "note" in bibtex_entry:
            m = re.search("^\\\\url{(.+?)}$", bibtex_entry["note"])
            if m:
                return m.group(1)
        if "howpublished" in bibtex_entry:
            m = re.search("^\\\\url{(.+?)}$", bibtex_entry["howpublished"])
            if m:
                return m.group(1)
        return None

    @staticmethod
    def get_pub_type(bibtex_entry):
        """For a bibtex entry: dictionary
        with "ENTRYTYPE" key expected return type of publication based on ENTRYTYPE
        and other relevant text in the bibtex (excluding abstract)"""
        bibtex_types = bibtex_entry.get("ENTRYTYPE", "").lower()
        bibtex_entry.pop("abstract", None)
        bibtex_as_str = str(bibtex_entry).lower()
        if "arxiv" in bibtex_as_str:
            return "preprint"
        if "poster" in bibtex_as_str:
            return "poster"
        if "thesis" in bibtex_as_str:
            if "ms" in bibtex_as_str or "master thesis" in bibtex_as_str:
                return "ms thesis"
            if "phd" in bibtex_as_str:
                return "phd thesis"
            return "thesis"
        if "github" in bibtex_as_str:
            return "github"
        if "patent" in bibtex_as_str:
            return "patent"
        for bibtex_type in bibtex_types.split(","):
            if bibtex_type == "incollection":
                return "book chapter"
            if (
                "techreport" in bibtex_as_str
                or "tech report" in bibtex_as_str
                or "internal report" in bibtex_as_str
            ):
                return "tech report"
            if bibtex_type in [
                "article",
                "review",
                "journal article",
                "journalarticle",
            ]:
                return "journal article"
            if (
                bibtex_type
                in ["inproceedings", "conference paper", "conference full paper"]
                or "proceeding" in bibtex_as_str
            ):
                return "conference paper"
        return "other"

    @staticmethod
    def how_similar(str1, str2):
        if not str1:
            str1 = ""
        if not str2:
            str2 = ""
        return SequenceMatcher(None, str1, str2).ratio()

    @staticmethod
    def is_similar_str(str1, str2):
        return (
            PublicationUtils.how_similar(str1, str2)
            >= PublicationUtils.SIMILARITY_THRESHOLD
        )

    @staticmethod
    def is_pub_similar(pub1, pub2):
        """Returns if the arg:pub1 and arg:pub2 are similar
        It returns true if the year are an exact match and
        if title is almost similar strings see difflib.SequenceMatcher
        Not checking for forum as forums can be abbreviated
        Not checking for authors match - as authors can have alias
        A reviewer to flagged duplicates can verify for authors

        Args:
            pub1 (projects.models.Publication)
            pub2 (projects.models.Publication)

        Returns:
            boolean
        """
        if str(pub1.year) != str(pub2.year):
            return False
        if (
            PublicationUtils.how_similar(pub1.title, pub2.title)
            > PublicationUtils.PUB_TITLE_DUPLICATE_CHECK_SIMILARITY_THRESHOLD
        ):
            return True
        return False

    @staticmethod
    def get_projects_for_author_names(author_names, year):
        usernames = []
        for author in author_names:
            usernames.extend(get_usernames_for_author(author))
        kcc = KeycloakClient()
        projects = [
            proj for u in usernames for proj in kcc.get_user_projects_by_username(u)
        ]
        return projects


def update_progress(task, stage=None, current=None, total=None, message=None):
    """
    Update the task's progress. This is essentially 2 different progress bars depending on stage.
    Stage: 0 - import, 1 - processing.
    """
    if message:
        task.update_state(state="PROGRESS", meta={"message": message})
    else:
        stage_multiplier = 50 / total
        stage_offset = stage * 50
        calculated_current = int(current * stage_multiplier + stage_offset)
        LOG.info(
            f"Updating task progress: {current}/{total} -> {calculated_current}/100"
        )
        task.update_state(
            state="PROGRESS", meta={"current": calculated_current, "total": 100}
        )
