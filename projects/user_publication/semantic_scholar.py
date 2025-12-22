import datetime
import logging
import re
import time

import requests
from django.conf import settings

from projects.models import (
    ChameleonPublication,
    Publication,
    PublicationQuery,
    RawPublication,
)
from projects.user_publication import utils
from projects.user_publication.utils import (
    PublicationUtils,
    RawPublicationSource,
    update_progress,
)

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


def _get_citation_count(pid):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}"
    for attempt in range(1, 4):
        response = requests.get(
            url,
            params={"fields": "citationCount"},
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )
        d = response.json()
        if response.status_code == 200:
            return d.get("citationCount", 0)

        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", attempt))
            logger.warning(
                f"Rate limit hit for {pid}, waiting {retry_after}s (attempt {attempt}/3)"
            )
            time.sleep(retry_after)
            continue
        else:
            logger.warning(
                f"Failed to get citation count for {pid}, status {response.status_code}; "
                f"attempt {attempt}/3"
            )
            time.sleep(attempt)
    logger.error(f"Giving up getting citation count for {pid}")
    return 0


FIELDS = [
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


def _get_citations(pid, fields=None):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}/citations"
    if fields is None:
        fields = FIELDS

    return _semantic_scholar_paginated_get(
        url=url,
        params={},
        fields=fields,
    )


def _bulk_search(query, fields=None):
    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"

    if fields is None:
        fields = FIELDS

    params = {
        "query": query,
    }

    return _semantic_scholar_paginated_get(
        url=url,
        params=params,
        fields=fields,
    )


def _semantic_scholar_paginated_get(url, params, fields, limit=1000):
    all_results = []
    offset = 0

    while True:
        params = params.copy()
        params.update(
            {
                "fields": ",".join(fields),
                "offset": offset,
                "limit": limit,
            }
        )

        logger.info(params)

        response = requests.get(
            url,
            params=params,
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )

        if response.status_code != 200:
            print(f"Request failed with status code: {response.status_code}")
            break

        data = response.json()
        results = data.get("data", [])

        if not results:
            break

        all_results.extend(results)
        offset += limit

    return all_results


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
    pubs = ChameleonPublication.objects.exclude(semantic_scholar_ref__isnull=True)
    total = len(pubs)
    for i, chameleon_pub in enumerate(pubs):
        update_progress(stage=0, current=i, total=total, task=task)
        for cc in _get_citations(chameleon_pub.semantic_scholar_ref):
            citing_paper = cc.get("citingPaper", {})
            if not citing_paper:
                continue
            pub = _get_pub_model(citing_paper, dry_run)
            if pub:
                publications.append(
                    RawPublicationSource(
                        pub_model=pub,
                        source_id=citing_paper.get("paperId"),
                        source_name=RawPublication.SEMANTIC_SCHOLAR,
                        cites_chameleon_pub=chameleon_pub,
                        found_with_query=None,
                    )
                )

    for query in PublicationQuery.objects.filter(
        source_type=RawPublication.SEMANTIC_SCHOLAR
    ):
        for cc in _bulk_search(query.query):
            pub = _get_pub_model(cc, dry_run)
            if pub:
                publications.append(
                    RawPublicationSource(
                        pub_model=pub,
                        source_id=cc.get("paperId"),
                        source_name=RawPublication.SEMANTIC_SCHOLAR,
                        cites_chameleon_pub=None,
                        found_with_query=query,
                    )
                )

    return publications


def update_citations():
    for pub in RawPublication.objects.filter(
        name=RawPublication.SEMANTIC_SCHOLAR,
        publication__status=Publication.STATUS_APPROVED,
        source_id__isnull=False,
    ).select_related("publication"):
        pub.citation_count = _get_citation_count(pub.source_id)
        pub.save()
