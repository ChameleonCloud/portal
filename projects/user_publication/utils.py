import csv
import datetime
import logging
import re
from collections import Counter
from difflib import SequenceMatcher

import pytz
from django.db.models import Q
from django.db import transaction
import unicodedata

LOG = logging.getLogger(__name__)

PUBLICATION_REPORT_KEYS = [
    "id",
    "title",
    "project_id",
    "publication_type",
    "forum",
    "year",
    "month",
    "author",
    "bibtex_source",
    "link",
    "doi",
    "source",
]


def add_source_to_pub(pub, source):
    LOG.info(
        f"Publication already exists - {pub.title}"
        f" - adding other source - {source} - This check might be outdated"
    )
    with transaction.atomic():
        source = pub.source.get_or_create(name=source)[0]
        source.found_by_source = True
        source.save()
        return


def decode_unicode_text(en_text):
    # for texts with unicode chars - accented chars replace them with eq ASCII
    # to perform LIKE operation to database
    de_text = (
        unicodedata.normalize("NFKD", en_text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    if en_text != de_text:
        LOG.info(f"decoding - {en_text} to {de_text}")
    return de_text


def guess_project_for_publication(authors, pub_year):
    """
    For a given publication, we figure out which project it is most-likely from by
    finding out which projects were active during the publication year, and have a PI
    in the publication's list of authors.
    """
    from projects.models import Project, ProjectPIAlias
    pub_year = int(pub_year)
    # Build a complex filter for all projects which have a PI that matches an author name
    name_filter = Q()
    for author in authors:
        author = decode_unicode_text(author)
        try:
            first_name, *_, last_name = author.rsplit(" ", 1)
        except ValueError:
            # There are some authors on semantic scholar with only a last name
            name_filter |= Q(pi__last_name=author)
            continue
        name_filter |= Q(
            pi__first_name__iexact=first_name, pi__last_name__iexact=last_name
        )
        aliases = ProjectPIAlias.objects.filter(alias__iexact=author)
        # If the author has any aliases, look for those as well
        for alias in aliases.all():
            name_filter |= Q(
                pi__first_name__iexact=alias.pi.first_name,
                pi__last_name__iexact=alias.pi.last_name,
            )
    # Grab all the projects who have a publications written by one of the requested authors
    projects = Project.objects.filter(name_filter)
    if not projects.exists():
        LOG.info(f"Could not find project for authors {authors}")
        return
    counter = Counter()
    fake_start = datetime.datetime(year=9999, month=1, day=1, tzinfo=pytz.UTC)
    fake_end = datetime.datetime(year=1, month=1, day=1, tzinfo=pytz.UTC)
    for project in projects.all():
        if not project.allocations.exists():
            continue
        # Consider the runtime of a project to be the start of its first allocation
        # until the end of its last allocation
        start = min(
            alloc.start_date or fake_start for alloc in project.allocations.all()
        )
        end = max(  
            alloc.expiration_date or fake_end for alloc in project.allocations.all()
        )
        # If the publication took place during the lifetime of the project, record it
        if start.year <= pub_year <= end.year + 1:
            # Count the number of authors that appear in this project's publications
            all_authors = {p.author.lower() for p in project.project_publication.all()}
            found_authors = len({a for a in authors if a in all_authors})
            counter.update({project: found_authors})

    if len(counter) == 0:
        LOG.info(
            f"Could not find project during publication timeframe: "
            f"(Year {pub_year}, authors {authors})"
        )
        return

    return counter.most_common(1)[0][0]


def report_publications(pubs):
    for pub in pubs:
        print(pub.__repr__())
        print("\n")
    return


def export_publications(pubs, file_name):
    with open(file_name, "w", newline="") as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(PUBLICATION_REPORT_KEYS)
        for pub in pubs:
            pd = pub.__dict__
            wr.writerow([pd.get(k) for k in PUBLICATION_REPORT_KEYS])
    return


def parse_author(author):
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


def clean_authors_attr(authors):
    """Split the authors based on the presense of ',' and 'and' in the text
    stripped off whitespaces

    Args:
        authors (str): list of authors seperated by , or and

    Returns:
        cleaned_authors (list)
    """
    # names with lastname, firstname and lastname, firstname
    # split by and make firstname lastname format
    if 'and' in authors and ', ' in authors:
        split_authors = [name.strip() for name in authors.split('and')]
        cleaned_authors = [parse_author(author) for author in split_authors]
    elif ', ' in authors:
        split_authors = [name.strip() for name in authors.split(',')]
        cleaned_authors = [parse_author(author) for author in authors]
    elif 'and' in authors:
        cleaned_authors = [name.strip() for name in authors.split('and')]
    else:
        # when there is a single author
        return [authors]
    return cleaned_authors


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
        bibtex_types = bibtex_entry.get("ENTRYTYPE", '').lower()
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
        for bibtex_type in bibtex_types.split(','):
            if bibtex_type == "incollection":
                return "book chapter"
            if (
                "techreport" in bibtex_as_str
                or "tech report" in bibtex_as_str
                or "internal report" in bibtex_as_str
            ):
                return "tech report"
            if bibtex_type in ["article", "review", "journal article", "journalarticle"]:
                return "journal article"
            if (
                bibtex_type in ["inproceedings", "conference paper", "conference full paper"]
                or "proceeding" in bibtex_as_str
            ):
                return "conference paper"
        return "other"

    @staticmethod
    def how_similar(str1, str2):
        return SequenceMatcher(None, str1, str2).ratio()

    @staticmethod
    def is_similar_str(str1, str2):
        return (
            PublicationUtils.how_similar(str1, str2) >= PublicationUtils.SIMILARITY_THRESHOLD
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
        if (pub1.year != pub2.year):
            return False
        if not (
            PublicationUtils.how_similar(
                pub1.title, pub2.title
            ) > PublicationUtils.PUB_DUPLICATE_CHECK_SIMILARITY_THRESHOLD
        ):
            return False
        if not (
            PublicationUtils.how_similar(
                pub1.forum, pub2.forum
            ) > PublicationUtils.PUB_DUPLICATE_CHECK_SIMILARITY_THRESHOLD
        ):
            return False
        return True


def save_publication(pub_model, source):
    """Saves publication model along with the source
    Creates the source model with FK to publication"""
    with transaction.atomic():
        pub_model.save()
        pub_model.source.create(
            name=source,
            found_by_algorithm=True
        )
