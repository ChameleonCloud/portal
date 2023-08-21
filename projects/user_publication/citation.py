"""
Fill in the latest citation numbers for all publication
"""
import logging
import re
import time

import requests
from django.conf import settings
from django.db import transaction
from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from pybliometrics.scopus.exception import Scopus404Error

from projects.models import Publication, PublicationSource
from projects.user_publication.gscholar import GoogleScholarHandler
from projects.user_publication.utils import PublicationUtils

logger = logging.getLogger("projects")

DOI_RE = r"(10.\d{4,9}\/[-._;()\/:\w]+)"
SEMANTIC_CITATION_RETRIES = 10


def update_scopus_citation(pub, dry_run=True):
    scopus_pub = None
    # few publications have doi in ('doi') format in the DB
    doi_re_result = re.search(DOI_RE, str(pub.doi))
    if doi_re_result:
        match = doi_re_result.group(1)
        try:
            scopus_pub = AbstractRetrieval(match, id_type="doi")
        except Scopus404Error:
            logger.info(
                f"Request resouce for doi: {pub.doi} not found - searching with title"
            )
    if not scopus_pub:
        no_words = re.compile(r"[^a-zA-Z\d\s:\-_.]")
        whitespace = re.compile(r"\s+")
        search_title = no_words.sub("", pub.title)
        search_title = whitespace.sub(" ", search_title)
        search_title = whitespace.sub(" ", search_title)
        search_title = search_title.strip().lower()
        search = ScopusSearch(f"TITLE ( {search_title} )")
        search_results = []
        if search and search.results:
            for x in search.results:
                if PublicationUtils.is_similar_str(x.title.lower(), pub.title.lower()):
                    search_results.append(x)
        if (len(search_results)) > 0:
            scopus_pub = search_results[0]
    if scopus_pub:
        # Returns a tuple of (object, created)
        existing_scopus_source = pub.sources.get_or_create(name=PublicationSource.SCOPUS)[0]
        logger.info(
            f"update scopus citation number for "
            f"{pub.title} (id: {pub.id}) "
            f"from {existing_scopus_source.citation_count} "
            f"to {scopus_pub.citedby_count}"
        )
        if not dry_run:
            with transaction.atomic():
                existing_scopus_source.citation_count = scopus_pub.citedby_count
                existing_scopus_source.save()


def make_semantic_call(url, params, headers):
    """Makes a requests.get call
    Retries for 100 times waiting for 5 seconds between subsequent
    calls with response code 429 - too many requests
    After few retries - SemanticScholar responds with the response

    Args:
        url (str)
        params (dict): field names needed in the response
        headers (dict): with semantic scholar API key

    """
    count = 0
    while count < SEMANTIC_CITATION_RETRIES:
        response = requests.get(
            url,
            params=params,
            headers=headers,
        )
        if response.ok:
            return response.json()
        # if "Too many requests response"
        if response.status_code == 429:
            return
        count += 1
        logger.info(f"Sleeping for 5 seconds - {count}/100")
        time.sleep(5)
    return


def update_semantic_scholar_citation(pub, dry_run=True):
    semantic_scholar_pub = None
    if pub.doi:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{pub.doi}"
        params = {"fields": "title,citationCount"}
        headers = {"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY}
        semantic_scholar_pub = make_semantic_call(url, params, headers)
    if not semantic_scholar_pub:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        fields = [
            "title",
            "citationCount",
        ]
        params = {"query": pub.title, "limit": 1, "fields": ",".join(fields)}
        headers = {"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY}
        result = make_semantic_call(url, params, headers)
        result = result["data"]
        if len(result) > 0:
            result = result[0]
            sc_title = result.get("title")
            if sc_title and PublicationUtils.is_similar_str(
                sc_title.lower(), pub.title.lower()
            ):
                semantic_scholar_pub = result
    if semantic_scholar_pub:
        citation_cnt = semantic_scholar_pub.get("citationCount", 0)
        # Returns a tuple of (object, created)
        existing_sem_source = pub.sources.get_or_create(
            name=PublicationSource.SEMANTIC_SCHOLAR
        )[0]
        logger.info(
            (
                f"update semantic scholar citation number for "
                f"{pub.title} (id: {pub.id}) "
                f"from {existing_sem_source.citation_count} "
                f"to {citation_cnt}"
            )
        )
        if not dry_run:
            with transaction.atomic():
                existing_sem_source.citation_count = citation_cnt
                existing_sem_source.save()


def update_citation_numbers(dry_run=True):
    gscholar = GoogleScholarHandler()
    for pub in Publication.objects.filter(status=Publication.STATUS_APPROVED):
        try:
            update_scopus_citation(pub, dry_run)
        except Exception:
            logger.exception(
                f"failed to update scopus citation number for {pub.title} (id: {pub.id})"
            )
        try:
            update_semantic_scholar_citation(pub, dry_run)
        except Exception as e:
            logger.exception(
                f"failed to update semantic scholar citation number for {pub.title} (id: {pub.id})",
                exc_info=e,
            )
        try:
            gscholar.update_g_scholar_citation(pub, dry_run)
        except Exception:
            logger.exception(
                f"failed to update semantic scholar citation number for {pub.title} (id: {pub.id})"
            )
