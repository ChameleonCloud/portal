"""
Fill in the latest citation numbers for all publication
"""
from django.conf import settings
import logging
from pybliometrics.scopus import ScopusSearch
from pybliometrics.scopus import AbstractRetrieval
import re
import requests

from projects.models import Publication
from projects.pub_utils import PublicationUtils

logger = logging.getLogger("projects")


def update_scopus_citation(pub, dry_run=True):
    scopus_pub = None
    if pub.doi:
        scopus_pub = AbstractRetrieval(pub.doi, id_type="doi")
    if not scopus_pub:
        no_words = re.compile(r"[^a-zA-Z\d\s:\-_.]")
        whitespace = re.compile(r"\s+")
        search_title = no_words.sub("", pub.title)
        search_title = whitespace.sub(" ", search_title)
        search_title = search_title.strip().lower()
        search = ScopusSearch(f"TITLE ( {search_title} )")
        search_results = []
        if search and search.results:
            for x in search.results:
                if (
                    PublicationUtils.how_similar(x.title.lower(), pub.title.lower())
                    >= 0.9
                ):
                    search_results.append(x)
        if (len(search_results)) > 0:
            scopus_pub = search_results[0]

    if scopus_pub:
        if dry_run:
            logger.info(
                (
                    f"update scopus citation number for "
                    f"{pub.title} (id: {pub.id}) "
                    f"from {pub.scopus_citations} "
                    f"to {scopus_pub.citedby_count}"
                )
            )
        else:
            pub.scopus_citations = scopus_pub.citedby_count
            pub.save()


def update_semantic_scholar_citation(pub, dry_run=True):
    semantic_scholar_pub = None
    if pub.doi:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{pub.doi}"
        response = requests.get(
            url,
            params={"fields": "title,citationCount"},
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )
        semantic_scholar_pub = response.json()
    if not semantic_scholar_pub:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        fields = [
            "title",
            "citationCount",
        ]
        response = requests.get(
            url,
            params={"query": pub.title, "limit": 1, "fields": ",".join(fields)},
            headers={"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY},
        )

        result = response.json()["data"]
        if len(result) > 0:
            result = result[0]
            sc_title = result.get("title")
            if (
                sc_title
                and PublicationUtils.how_similar(sc_title.lower(), pub.title.lower())
                >= 0.9
            ):
                semantic_scholar_pub = result

    if semantic_scholar_pub:
        citation_cnt = semantic_scholar_pub.get("citationCount")
        if citation_cnt:
            if dry_run:
                logger.info(
                    (
                        f"update semantic scholar citation number for "
                        f"{pub.title} (id: {pub.id}) "
                        f"from {pub.semantic_scholar_citations} "
                        f"to {citation_cnt}"
                    )
                )
            else:
                pub.semantic_scholar_citations = citation_cnt
                pub.save()


def update_citation_numbers(dry_run=True):
    for pub in Publication.objects.all():
        try:
            update_scopus_citation(pub, dry_run)
        except Exception:
            logger.exception(
                f"failed to update scopus citation number for {pub.title} (id: {pub.id})"
            )
        try:
            update_semantic_scholar_citation(pub, dry_run)
        except Exception:
            logger.exception(
                f"failed to update semantic scholar citation number for {pub.title} (id: {pub.id})"
            )
