import datetime
from django.conf import settings
import logging
import re
import requests
from django.db.models import Q

from projects.models import Publication, ChameleonPublication
from projects.user_publication import utils

logger = logging.getLogger("projects")

CHAMELEON_REFS_REGEX = [
    re.compile(pattern)
    for pattern in [
        "chameleon:(.*)testbed",
        "Chameleon:(.*)configurable experimental environment"
        "lessons learned from(.*)chameleon testbed",
        "chameleon cloud testbed",
        "chameleoncloud.org",
        "chameleon cloud",
        "chameleon testbed",
        "chameleon project",
    ]
]


def _search_semantic_scholar(query):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
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
    url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}"
    response = requests.get(
        url,
        params={"fields": "references.title"},
        headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
    )
    return response.json().get("references", [])


def _get_citations(pid):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}"
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


def _get_pub_model(publication, dry_run=True):
    title = utils.decode_unicode_text(publication.get("title"))
    pub_date_raw = publication.get("publicationDate")
    if pub_date_raw:
        published_on = datetime.datetime.strptime(pub_date_raw, "%Y-%m-%d")
        year = published_on.year
        month = published_on.month
    else:
        year = publication.get("year")
        month = None
    if not year:
        return None
    authors = [a["name"] for a in publication.get("authors", [])]
    proj = utils.guess_project_for_publication(authors, year)
    journal = publication.get("journal")
    if journal:
        forum = journal.get("name")
    else:
        forum = publication.get("venue")
    doi = (publication.get("externalIds", {}).get("DOI"),)

    if (
        not proj
        or ChameleonPublication.objects.filter(title__iexact=title).exists()
        or Publication.objects.filter(Q(title=title) | Q(project=proj)).exists()
    ):
        return None

    pub_model = Publication(
        title=title,
        year=year,
        month=month,
        author=" and ".join(a["name"] for a in publication.get("authors", [])),
        entry_created_date=datetime.date.today(),
        project=proj,
        bibtex_source="{}",
        added_by_username="admin",
        forum=forum,
        doi=doi,
        link=f"https://www.doi.org/{doi}" if doi else publication.get("url"),
        publication_type=_get_pub_type(publication.get("publicationTypes", []), forum),
        source="semantic_scholar",
        status=Publication.STATUS_IMPORTED,
    )
    if dry_run:
        logger.info(f"import {str(pub_model)}")
    return pub_model


def _publication_references_chameleon(raw_pub):
    references = _get_references(raw_pub["paperId"])
    for ref in references:
        for cref_regex in CHAMELEON_REFS_REGEX:
            if cref_regex.search(ref["title"].lower()):
                return True
    # The dict might contain these keys with null as the value
    abstract = raw_pub.get("abstract") or ""
    title = raw_pub.get("title") or ""
    return (
        "chameleon testbed" in abstract
        or "chameleon cloud" in abstract
        or "chameleon testbed" in title.lower()
        or "chameleon cloud" in title.lower()
    )


def pub_import(dry_run=True):
    publications = []
    for chameleon_pub in ChameleonPublication.objects.exclude(ref__isnull=True):
        for cc in _get_citations(chameleon_pub.ref):
            p = _get_pub_model(cc, dry_run)
            if p:
                publications.append(p)

    pubs = _search_semantic_scholar("chameleon cloud testbed")
    for raw_pub in pubs:
        pub_year = raw_pub.get("year")
        if not pub_year or pub_year <= 2014:
            continue
        if _publication_references_chameleon(raw_pub):
            p = _get_pub_model(raw_pub, dry_run)
            if p:
                publications.append(p)
    return publications
