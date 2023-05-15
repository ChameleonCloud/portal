import datetime
import logging
import re

import requests
from django.conf import settings
from django.db.models import Q

from projects.models import ChameleonPublication, Publication
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


def _get_authors(aids):
    url = "https://api.semanticscholar.org/graph/v1/author/batch"
    fields = ["name", "aliases"]
    data = {"ids": aids}
    response = requests.post(
        url,
        json=data,
        params={"fields": ",".join(fields)},
        headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
    )
    return response.json()


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
    author_ids = [a["authorId"] for a in publication.get("authors", [])]
    author_details = _get_authors(author_ids)
    authors = set()
    for author_detail in author_details:
        if not author_detail:
            continue
        authors.add(author_detail["name"])
        if author_detail["aliases"]:
            authors.update(set(author_detail["aliases"]))
    journal = publication.get("journal")
    if journal:
        forum = journal.get("name")
    else:
        forum = publication.get("venue")
    doi = (publication.get("externalIds", {}).get("DOI"),)
    entry_type = ""
    if publication["publicationTypes"]:
        entry_type = ",".join(publication["publicationTypes"])
    pub_model = Publication(
        title=title,
        year=year,
        month=month,
        author=" and ".join(a["name"] for a in publication.get("authors", [])),
        bibtex_source=publication.get("citationStyles", {}),
        added_by_username="admin",
        forum=forum,
        doi=doi,
        link=f"https://www.doi.org/{doi}" if doi else publication.get("url"),
        publication_type=PublicationUtils.get_pub_type(
            {"ENTRYTYPE": entry_type, "forum": forum}
        ),
        status=Publication.STATUS_SUBMITTED,
    )
    same_pub = utils.get_publication_with_same_attributes(pub_model, Publication)
    if same_pub.exists():
        utils.add_source_to_pub(same_pub.get(), PublicationSource.SEMANTIC_SCHOLAR)
    return pub_model


def pub_import(dry_run=True):
    publications = []
    for chameleon_pub in ChameleonPublication.objects.exclude(ref__isnull=True):
        for cc in _get_citations(chameleon_pub.ref):
            p = _get_pub_model(cc, dry_run)
            if p:
                publications.append((PublicationSource.SEMANTIC_SCHOLAR, p))
    return publications
