import datetime
import logging
import re

import requests
from django.conf import settings

from projects.models import ChameleonPublication, Publication, PublicationSource
from projects.user_publication import utils
from projects.user_publication.utils import PublicationUtils, update_progress

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
    url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}/citations"
    fields = [
        "paperId",
        "externalIds",
        "url",
        "title",
        "venue",
        "year",
        "citationCount",
        "fieldsOfStudy",
        "publicationTypes",
        "publicationDate",
        "citationStyles",
        "journal",
        "authors",
        "abstract",
    ]
    limit = 1000
    all_citations = []
    offset = 0
    while True:
        params = {"fields": ",".join(fields), "offset": offset, "limit": limit}

        response = requests.get(
            url,
            params=params,
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )
        if response.status_code == 200:
            data = response.json()
            citations = data.get("data", [])
            if not citations:
                break
            all_citations.extend(citations)
            offset += limit
        else:
            print(f"Request failed with status code: {response.status_code}")
            break
    return all_citations


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
    journal = publication.get("journal", {})
    if journal:
        forum = journal.get("name", "")
    else:
        forum = publication.get("venue", "")
    external_ids = publication.get("externalIds", {})
    doi = ""
    # externalIds can be a None
    if external_ids:
        doi = external_ids.get("DOI", "")
    entry_type = ""
    if publication["publicationTypes"]:
        entry_type = ",".join(publication["publicationTypes"])
    if doi:
        link = f"https://www.doi.org/{doi}"
    else:
        link = publication.get("url", "")
    bibtex_source = publication.get("citationStyles", {})
    # "citationStyles" may have None in it
    if not bibtex_source:
        bibtex_source = {}
    pub_model = Publication(
        title=title,
        year=year,
        month=month,
        author=" and ".join(a["name"] for a in publication.get("authors", [])),
        bibtex_source=bibtex_source,
        added_by_username="admin",
        forum=forum,
        doi=doi,
        link=link,
        publication_type=PublicationUtils.get_pub_type(
            {"ENTRYTYPE": entry_type, "forum": forum}
        ),
        status=Publication.STATUS_SUBMITTED,
    )
    return pub_model


def pub_import(task, dry_run=True):
    publications = []
    pubs = ChameleonPublication.objects.exclude(ref__isnull=True)
    total = len(pubs)
    for i, chameleon_pub in enumerate(pubs):
        update_progress(stage=0, current=i, total=total, task=task)
        for cc in _get_citations(chameleon_pub.ref):
            citing_paper = cc.get("citingPaper", {})
            if not citing_paper:
                continue
            pub = _get_pub_model(citing_paper, dry_run)
            if pub:
                publications.append((PublicationSource.SEMANTIC_SCHOLAR, pub))
    return publications
