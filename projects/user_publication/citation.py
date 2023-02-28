"""
Fill in the latest citation numbers for all publication
"""
import logging
import re
import time

import requests
from django.conf import settings
from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from pybliometrics.scopus.exception import Scopus404Error

from projects.models import Publication
from projects.user_publication.gscholar import GoogleScholarHandler
from projects.user_publication.utils import PublicationUtils

logger = logging.getLogger("projects")

# scholarly limits to 100 requests for 5 minutes
# https://researchguides.smu.edu.sg/api-list/scholarly-metadata-api
REQUESTS_IN_MINUTE = 20

DOI_RE = re.compile("(10.\d{4,9}\/[-._;()\/:\w]+)")

def update_scopus_citation(pub, dry_run=True):
    scopus_pub = None
    doi_re_result = DOI_RE.search(str(pub.doi))
    if doi_re_result:
        match = doi_re_result.group(1)
        try:
            scopus_pub = AbstractRetrieval(match, id_type="doi")
        except Scopus404Error:
            logger.info(f"Request resouce for doi: {pub.doi} not found - searching with title")
        else:
            if scopus_pub and pub.doi != match:
                logger.info(f"Updating id:{pub.id} doi {pub.doi} to {match}")
                pub.doi = match
                pub.save()
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
                    >= PublicationUtils.SIMILARITY
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
                logger.info(
                    (
                        f"update semantic scholar citation number for "
                        f"{pub.title} (id: {pub.id}) "
                        f"from {pub.semantic_scholar_citations} "
                        f"to {citation_cnt}"
                    )
                )
                pub.semantic_scholar_citations = citation_cnt
                pub.save()


def update_citation_numbers(dry_run=True):
    count = 0
    err_count = 0
    for pub in Publication.objects.all():
        count += 1

        # to not overload any system
        if count % REQUESTS_IN_MINUTE == 0:
            time.sleep(5)
        try:
            update_scopus_citation(pub, dry_run)
        except Exception:
            err_count += 1
            logger.exception(
                f"failed to update scopus citation number for {pub.title} (id: {pub.id})"
            )
        # try:
        #     update_semantic_scholar_citation(pub, dry_run)
        # except Exception:
        #     logger.exception(
        #         f"failed to update semantic scholar citation number for {pub.title} (id: {pub.id})"
        #     )
        # try:
        #     gscholar = GoogleScholarHandler()
        #     gscholar.update_g_scholar_citation(pub, dry_run)
        # except Exception:
        #     logger.exception(
        #         f"failed to update semantic scholar citation number for {pub.title} (id: {pub.id})"
        #     )
    print(err_count, "Number of errors")