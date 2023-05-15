import csv
import datetime
import logging
import os
import re
import unicodedata
from difflib import SequenceMatcher

import pytz
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

# from projects.models import Publication
from util.keycloak_client import KeycloakClient

LOG = logging.getLogger(__name__)

PUBLICATION_REPORT_KEYS = [
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


def get_publication_with_same_attributes(pub, publication_model_class):
    # return publications with exact title, forum, author and year
    return publication_model_class.objects.filter(
        title__iexact=pub.title,
        forum__iexact=pub.forum,
        author__iexact=pub.author,
        year=pub.year,
    ).exclude(status=publication_model_class.STATUS_DUPLICATE)


def update_original_pub_source(original_pub, duplicate_pub):
    """Updates original publications' source with the duplicate publication's sources

    Args:
        original_pubs (models.Publication)
        duplicate_pub (models.Publication)
    """
    with transaction.atomic():
        dpub_sources = duplicate_pub.sources.all()
        for dpub_source in dpub_sources:
            # copy all the objects's data to pub2_source
            opub_source = original_pub.sources.get_or_create(name=dpub_source.name)[0]
            opub_source.cites_chameleon = dpub_source.cites_chameleon
            opub_source.acknowledges_chameleon = dpub_source.acknowledges_chameleon
            opub_source.is_found_by_algorithm = True
            opub_source.approved_with = opub_source.APPROVED_WITH_PUBLICATION
            opub_source.entry_created_date = dpub_source.entry_created_date
            opub_source.save()


def add_source_to_pub(pub, source, dry_run=True):
    LOG.info(
        f"Publication already exists - {pub.title}" f" - adding other source - {source}"
    )
    if dry_run:
        return
    with transaction.atomic():
        source = pub.sources.get_or_create(name=source)[0]
        source.is_found_by_algorithm = True
        source.cites_chameleon = True
        # Adding source to a publication only when it already exists is a valid publication with project in chameleon
        source.approved_with = source.PUBLICATION
        source.save()


def decode_unicode_text(en_text):
    # for texts with unicode chars - accented chars replace them with eq ASCII
    # to perform LIKE operation to database
    de_text = (
        unicodedata.normalize("NFKD", en_text).encode("ascii", "ignore").decode("ascii")
    )
    if en_text != de_text:
        LOG.info(f"decoding - {en_text} to {de_text}")
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
    start = min(alloc.start_date or fake_start for alloc in project.allocations.all())
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


def get_pub_type(types, forum):
    """Return the type of publication

    Args:
        types (list): (semantic scholar) Journal Article, Conference, Review, etc.
        forum (str): EntryType - https://www.bibtex.com/e/entry-types/

    Returns:
        str : publication type - conference, thesis, report, etc.
    """
    if not forum:
        forum = ""
    forum = forum.lower()
    if not types:
        types = []
    types = [t.lower() for t in types]

    if "arxiv" in forum:
        return "preprint"
    if "poster" in forum:
        return "poster"
    if "thesis" in forum:
        if "ms" in forum or "master thesis" in forum:
            return "ms thesis"
        if "phd" in forum:
            return "phd thesis"
        return "thesis"
    if "github" in forum:
        return "github"
    if "techreport" in forum or "tech report" in forum or "internal report" in forum:
        return "tech report"
    if "journalarticle" in types:
        return "journal article"
    if "conference" in types or "proceeding" in forum or "conference" in forum:
        return "conference paper"

    return "other"


class PublicationUtils:
    # ratio threshold from difflib.SequenceMatcher for publication titles
    SIMILARITY_THRESHOLD = 0.9
    PUB_DUPLICATE_CHECK_SIMILARITY_THRESHOLD = 0.8

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
        if title and venue are almost similar strings see difflib.SequenceMatcher
        # Not checking for authors match - as authors can have alias
        # A reviewer to flagged duplicates can verify for authors

        Args:
            pub1 (projects.models.Publication)
            pub2 (projects.models.Publication)

        Returns:
            boolean
        """
        if pub1.year != pub2.year:
            return False
        if not (
            PublicationUtils.how_similar(pub1.title, pub2.title)
            > PublicationUtils.PUB_DUPLICATE_CHECK_SIMILARITY_THRESHOLD
        ):
            return False
        if not (
            PublicationUtils.how_similar(pub1.forum, pub2.forum)
            > PublicationUtils.PUB_DUPLICATE_CHECK_SIMILARITY_THRESHOLD
        ):
            return False
        return True

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


def save_publication(
    pub_model, source, cites_chameleon=True, acknowledges_chameleon=False
):
    """Saves publication model along with the source
    Creates the source model with FK to publication"""
    with transaction.atomic():
        pub_model.save()
        source = pub_model.sources.create(
            name=source,
            is_found_by_algorithm=True,
            cites_chameleon=cites_chameleon,
            acknowledges_chameleon=acknowledges_chameleon,
        )
        source.approved_with = source.PENDING_REVIEW
        source.save()


def export_publication_status_run(
    file_name, pub, author_usernames, valid_projects, projects, reason
):
    if not os.path.isfile(file_name):
        with open(file_name, "w", newline="") as csv_f:
            csv_f_writer = csv.writer(csv_f)
            csv_f_writer.writerow(PUBLICATION_REPORT_KEYS)
    with open(file_name, "a", newline="") as csv_f:
        csv_f_writer = csv.writer(csv_f)
        row = [
            pub.title,
            pub.publication_type,
            pub.forum,
            pub.year,
            pub.month,
            pub.author,
            pub.bibtex_source,
            pub.link,
            pub.doi,
            author_usernames,
            valid_projects,
            projects,
            reason,
        ]
        csv_f_writer.writerow(row)
