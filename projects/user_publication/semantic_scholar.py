import datetime
import logging
import re

import requests
from django.conf import settings

from projects.models import ChameleonPublication, Publication, PublicationSource
from projects.user_publication import utils
from projects.user_publication.utils import PublicationUtils

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
        "citations.citationStyles",
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
    fields = [
        "name",
        "aliases"
    ]
    data = {'ids' : aids}
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
        authors.add(author_detail['name'])
        if author_detail['aliases']:
            authors.update(set(author_detail['aliases']))
    proj = utils.guess_project_for_publication(list(authors), year)
    journal = publication.get("journal")
    if journal:
        forum = journal.get("name")
    else:
        forum = publication.get("venue")
    doi = (publication.get("externalIds", {}).get("DOI"),)

    if (
        not proj
        or ChameleonPublication.objects.filter(title__iexact=title).exists()
    ):
        return None
    pub_exists = Publication.objects.filter(title=title, project=proj)
    if pub_exists:
        utils.add_source_to_pub(pub_exists[0], Publication.SEMANTIC_SCHOLAR)
        return
    # semantic scholar returns all publication types in a list ["JournalArticle", "Review"]
    entry_type = ''
    if publication["publicationTypes"]:
        entry_type = ','.join(publication["publicationTypes"])
    pub_model = Publication(
        title=title,
        year=year,
        month=month,
        author=" and ".join(a["name"] for a in publication.get("authors", [])),
        entry_created_date=datetime.date.today(),
        project=proj,
        bibtex_source=publication.get("citationStyles", {}),
        added_by_username="admin",
        forum=forum,
        doi=doi,
        link=f"https://www.doi.org/{doi}" if doi else publication.get("url"),
        publication_type=PublicationUtils.get_pub_type({
            "ENTRYTYPE": entry_type,
            "forum": forum
        }),
        status=Publication.STATUS_IMPORTED,
    )
    logger.info(f"import {str(pub_model)}")
    if not dry_run:
        # save publication model with source
        utils.save_publication(pub_model, PublicationSource.SEMANTIC_SCHOLAR)
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
    return publications
