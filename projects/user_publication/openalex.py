import datetime
import logging
import time

import requests
from django.conf import settings

from projects.models import (
    ChameleonPublication,
    Publication,
    RawPublication,
)
from projects.user_publication import utils
from projects.user_publication.utils import (
    PublicationUtils,
    RawPublicationSource,
    update_progress,
)

logger = logging.getLogger("projects")

OPENALEX_BASE = "https://api.openalex.org/works"
PER_PAGE = 200
MAILTO = settings.OPENALEX_MAILTO


def _openalex_get_citations_for_work(openalex_work_id):
    """
    Fetch all works that cite the given OpenAlex work ID using
    page-based pagination.
    """
    page = 1
    results = []

    while True:
        params = {
            "filter": f"cites:{openalex_work_id}",
            "sort": "cited_by_count:desc",
            "page": page,
            "per_page": PER_PAGE,
            "mailto": MAILTO,
        }

        response = requests.get(OPENALEX_BASE, params=params)

        if response.status_code != 200:
            logger.warning(
                f"OpenAlex request failed ({response.status_code}): {response.text}"
            )
            break

        data = response.json()
        page_results = data.get("results", [])

        if not page_results:
            break

        results.extend(page_results)

        meta = data.get("meta", {})
        total_pages = meta.get("page_count")

        if total_pages and page >= total_pages:
            break

        page += 1
        time.sleep(0.5)

    return results


def _normalize_openalex_work(work):
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        if author.get("display_name"):
            authors.append({"name": author["display_name"]})

    doi = ""
    if work.get("doi"):
        doi = work["doi"].replace("https://doi.org/", "")

    venue = work.get("host_venue", {}) or {}

    return {
        "title": work.get("title"),
        "publicationDate": work.get("publication_date"),
        "year": work.get("publication_year"),
        "venue": venue.get("display_name", ""),
        "journal": {"name": venue.get("display_name")} if venue else {},
        "externalIds": {"DOI": doi} if doi else {},
        "url": work.get("id"),
        "authors": authors,
        "publicationTypes": [work.get("type")] if work.get("type") else [],
    }


def _build_publication_model(normalized):
    title = utils.decode_unicode_text(normalized.get("title"))

    pub_date_raw = normalized.get("publicationDate")
    if pub_date_raw:
        published_on = datetime.datetime.strptime(pub_date_raw, "%Y-%m-%d")
        year = published_on.year
        month = published_on.month
    else:
        year = normalized.get("year")
        month = None

    if not year:
        return None

    journal = normalized.get("primary_location", {})
    forum = journal.get("raw_source_name", "")

    external_ids = normalized.get("externalIds", {}) or {}
    doi = external_ids.get("DOI", "")

    entry_type = ",".join(normalized.get("publicationTypes", []))

    link = f"https://www.doi.org/{doi}" if doi else normalized.get("url", "")

    return Publication(
        title=title,
        year=year,
        month=month,
        author=" and ".join(a["name"] for a in normalized.get("authors", [])),
        bibtex_source={},
        added_by_username="admin",
        forum=forum,
        doi=doi,
        link=link,
        publication_type=PublicationUtils.get_pub_type(
            {"ENTRYTYPE": entry_type, "forum": forum}
        ),
        status=Publication.STATUS_SUBMITTED,
    )


def pub_import(task, dry_run=True):
    """
    Fetch OpenAlex citations of Chameleon publications via openalex_ref.
    """
    publications = []

    chameleon_pubs = ChameleonPublication.objects.exclude(openalex_ref__isnull=True)

    total = len(chameleon_pubs)

    for i, chameleon_pub in enumerate(chameleon_pubs):
        update_progress(stage=0, current=i, total=total, task=task)

        works = _openalex_get_citations_for_work(chameleon_pub.openalex_ref)

        for work in works:
            normalized = _normalize_openalex_work(work)
            pub = _build_publication_model(normalized)

            if pub:
                publications.append(
                    RawPublicationSource(
                        pub_model=pub,
                        source_id=work.get("id"),
                        source_name=RawPublication.OPENALEX,
                        cites_chameleon_pub=chameleon_pub,
                        found_with_query=None,
                    )
                )

    return publications
