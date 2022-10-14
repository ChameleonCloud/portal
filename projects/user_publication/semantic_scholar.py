import datetime
from django.conf import settings
import logging
import re
import requests

from projects.models import Publication
from projects.user_publication import utils

logger = logging.getLogger("projects")

CHAMELEON_REFS_REGEX = [
    "chameleon:(.*)testbed",
    "Chameleon:(.*)configurable experimental environment"
    "lessons learned from(.*)chameleon testbed",
    "chameleon cloud testbed",
    "chameleoncloud.org",
    "chameleon cloud",
    "chameleon testbed",
    "chameleon project",
]

CHAMELEON_REFS = {
    "18f4a526234fbfed639b3788703d43fa6b468d9b": "Lessons Learned from the Chameleon Testbed",
    "1c91f729e7f51cb6fb709dfedcddb9bde10d1914": "Chameleon: A Scalable Production Testbed for Computer Science Research",
    "b99e844351487d620a69bf25a4df538b418b30f6": "Chameleon: A Large-Scale, Deeply Reconfigurable Testbed for Computer Science Research",
    "6738ab2ba7ab2971153fd951e02af62e43b15e5b": "Next Generation Clouds, the Chameleon Cloud Testbed, and Software Defined Networking (SDN)",
}


def _parse_authors(author_names):
    author_keys = []
    for name in author_names:
        n = name.rsplit(" ", 1)
        try:
            surname = n[1]
            givenname = n[0][0] + "."
        except Exception:
            continue
        author_keys.append((givenname.lower(), surname.lower()))
    return author_keys


def _search_semantic_scholar(query):
    url = "http://api.semanticscholar.org/graph/v1/paper/search"
    fields = [
        "externalIds",
        "url",
        "title",
        "venue",
        "year",
        "citationCount",
        "fieldsOfStudy",
        "publicationTypes",
        "publicationDate",
        "journal",
        "authors",
        "abstract",
    ]

    total = 1
    offset = 0
    results = []
    while offset < total:
        response = requests.get(
            url,
            params={
                "query": query,
                "limit": 100,
                "offset": offset,
                "fields": ",".join(fields),
            },
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )

        json_response = response.json()
        total = json_response.get("total")
        if not total:
            return results
        offset = json_response.get("next", total)
        results.extend(json_response["data"])
    return results


def _get_references(pid):
    url = f"http://api.semanticscholar.org/graph/v1/paper/{pid}"
    response = requests.get(
        url,
        params={"fields": "references.title"},
        headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
    )
    return response.json().get("references", [])


def _get_citations(pid):
    url = f"http://api.semanticscholar.org/graph/v1/paper/{pid}"
    fields = [
        "citations.externalIds",
        "citations.url",
        "citations.title",
        "citations.venue",
        "citations.year",
        "citations.citationCount",
        "citations.fieldsOfStudy",
        "citations.publicationTypes",
        "citations.publicationDate",
        "citations.journal",
        "citations.authors",
        "citations.abstract",
    ]

    response = requests.get(
        url,
        params={"fields": ",".join(fields)},
        headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
    )
    return response.json().get("citations", [])


def _get_pub_type(types, forum):
    forum = forum.lower()

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
    if "JournalArticle" in types:
        return "journal article"
    if "Conference" in types or "proceeding" in forum or "conference" in forum:
        return "conference paper"

    return "other"


def _save_publication(pi_projects, all_publications, publication, dry_run=True):
    title = publication.get("title")
    if publication.get("publicationDate"):
        published_on = datetime.datetime.strptime(
            publication.get("publicationDate"), "%Y-%m-%d"
        )
        year = published_on.year
        month = published_on.month
    else:
        year = publication.get("year")
        month = None
    author = _parse_authors([a["name"] for a in publication.get("authors", [])])
    proj = utils.link_publication_to_project(pi_projects, author, year)
    project_id = proj[0]

    if (
        project_id
        and title.lower() not in utils.CHAMELEON_PUBLICATIONS
        and not utils.pub_exists(all_publications, title, project_id)
    ):
        pub = Publication()

        pub.title = title
        pub.year = year
        pub.month = month
        pub.author = " and ".join([a["name"] for a in publication.get("authors", [])])
        pub.entry_created_date = datetime.date.today().strftime("%Y-%m-%d")
        pub.project_id = project_id
        pub.bibtex_source = "{}"
        pub.added_by_username = "admin"
        pub.forum = None
        if publication.get("journal"):
            pub.forum = publication.get("journal").get("name")
        if not pub.forum:
            pub.forum = publication.get("venue")
        pub.doi = None
        if publication.get("externalIds"):
            pub.doi = publication.get("externalIds").get("DOI")
        pub.link = None
        if pub.doi:
            pub.link = f"https://www.doi.org/{pub.doi}"
        else:
            pub.link = publication.get("url")
        scholar_types = publication.get("publicationTypes", [])
        if not scholar_types:
            scholar_types = []
        pub.publication_type = _get_pub_type(scholar_types, pub.forum)
        pub.source = "semantic_scholar"
        pub.status = Publication.STATUS_IMPORTED

        if dry_run:
            logger.info(f"import {str(pub)}")
        else:
            pub.save()
        return pub

    return None


def pub_import(dry_run=True):
    pi_projects = utils.get_pi_projects()
    all_publications = utils.get_publications()

    for pid, ptitle in CHAMELEON_REFS.items():
        for cc in _get_citations(pid):
            saved_pub = _save_publication(pi_projects, all_publications, cc, dry_run)
            if saved_pub:
                all_publications[saved_pub.title] = saved_pub.project_id

    pubs = _search_semantic_scholar("chameleon cloud testbed")
    for r in pubs:
        # filter pub by year and field of science
        pub_year = r.get("year", 2000)
        if not pub_year:
            pub_year = 2000
        pub_fos = r.get("fieldsOfStudy", [])
        if not pub_fos:
            pub_fos = []
        if pub_year <= 2014 and "Computer Science" in pub_fos:
            continue

        references = _get_references(r["paperId"])
        is_chameleon_paper = False
        for ref in references:
            for cref_regex in CHAMELEON_REFS_REGEX:
                if re.search(cref_regex, ref["title"].lower()):
                    is_chameleon_paper = True
                    break
        abstract = r.get("abstract")
        if not abstract:
            abstract = ""
        title = r.get("title")
        if (
            "chameleon testbed" in abstract
            or "chameleon cloud" in abstract
            or "chameleon testbed" in title.lower()
            or "chameleon cloud" in title.lower()
        ):
            is_chameleon_paper = True
        if is_chameleon_paper:
            _save_publication(pi_projects, all_publications, cc, dry_run)
