import datetime
import logging
import re

from django.conf import settings
from scholarly import ProxyGenerator, scholarly
from scholarly._proxy_generator import MaxTriesExceededException

from projects.models import ChameleonPublication, Publication
from projects.user_publication import utils
from projects.user_publication.utils import (PublicationUtils,
                                             add_to_all_sources)

logger = logging.getLogger(__name__)

MAX_RETRIES = 10


class GoogleScholarHandler(object):
    def __init__(self):
        """To make google scholar calls using proxy"""
        self.proxy = ProxyGenerator()
        self.scholarly = scholarly
        scraper_api_key = "16d20776cf0591e05d16a53874212107"
        if scraper_api_key:
            self.proxy.ScraperAPI(scraper_api_key)
            logger.info("Using scraper proxy")
        else:
            self.proxy.FreeProxies()
            logger.info("Using Free proxy")
        self.scholarly.use_proxy(self.proxy)
        self.retries = 0
        self.citations = []

    def _handle_proxy_reload(func):
        def inner_f(self, *args, **kwargs):
            while self.retries < MAX_RETRIES:
                try:
                    resp = func(self, *args, **kwargs)
                except MaxTriesExceededException:
                    # this occurs if Google blocks IP
                    logger.info(f"New free proxy retries : {self.retries} / {MAX_RETRIES}")
                    self.retries += 1
                    self.new_proxy()
                else:
                    self.retries = 0
                    break
            return resp
        return inner_f

    def _publication_id(self, pub: dict):
        m = re.search(r"cites=[\d+,]*", pub["citedby_url"])
        return m.group()[6:]

    def new_proxy(self):
        """sets a new proxy from free-proxy library"""
        if not self.proxy.proxy_mode.value == "FREE_PROXIES":
            return
        logger.info("Getting new free proxy")
        self.proxy.get_next_proxy()
        self.scholarly.use_proxy(self.proxy)

    @_handle_proxy_reload
    def get_one_pub(self, title: str):
        """To get one publication from google scholar
        Make sure the title is an exact match

        Args:
            title (str): Title of the publication
        """
        return self.scholarly.search_single_pub(title)

    @_handle_proxy_reload
    def get_cites(self, pub, year_low=2014, year_high=None):
        """Returns all the citations of the publication

        Args:
            pub (dict): return of the search_single_pub method
            year_low (int, optional): year to query from. Defaults to 2014
            year_high (int, optional): yaar to query till. Defaults to datetime.now().year

        Returns:
            list: list of publications that cited arg:pub
        """
        if not year_high:
            year_high = datetime.now().year
        pub_id = self._publication_id(pub)
        logger.info(f"Getting citations for {pub['bib']['title']}")
        num_citations = pub['num_citations']
        cites_gen = self.scholarly.search_citedby(
            pub_id, year_low=year_low, year_high=year_high
        )
        citations = []
        cite_count = 0
        while True:
            try:
                cited_pub = self.fill(self._get_next_cite(cites_gen))
                citations.append(cited_pub)
                cite_count += 1
                logger.info(f"Got {cite_count} / {num_citations}")
            except StopIteration:
                logger.info(f"End of iteration. Got {len(citations)} / {num_citations}")
                return citations

    @_handle_proxy_reload
    def _get_next_cite(self, cites_gen):
        return next(cites_gen)

    @_handle_proxy_reload
    def fill(self, pub):
        """fills the publication object with details from bibtex

        Args:
            pub (dict): scholarly return of the publication
        """
        return self.scholarly.fill(pub)

    def get_authors(self, pub):
        """returns a list of authors in a publication

        Args:
            pub (dict): scholarly return of the publication

        Returns:
            list: list of authors in ["firstname lastname",] format
        """
        authors = utils.decode_unicode_text(pub['bib']['author'])
        # substitute all charachter from text except
        # ',' , \w word charachter, \s whitespace charachter
        # - any other charachter
        # inspired from django.utils.text.slugify
        authors = re.sub(r"[^\,\w\s-]", "", authors)
        authors = authors.split(" and ")
        parsed_authors = [utils.parse_author(author) for author in authors]
        return parsed_authors

    def get_pub_model(self, pub):
        entry_type = []
        # bibtex ENTRYTYPE field
        if 'ENTRYTYPE' in pub['bib']:
            entry_type.append(pub['bib']['ENTRYTPE'])
        if 'pub_type' in pub['bib']:
            entry_type.append(pub['bib']['pub_type'])
        forum = ''
        if 'booktitle' in pub['bib']:
            forum = pub['bib']['booktitle']
        if 'journal' in pub['bib']:
            forum = pub['bib']['journal']
        pub_type = utils.get_pub_type(entry_type, forum)
        return Publication(
            title=utils.decode_unicode_text(pub["bib"]["title"]),
            year=pub["bib"]["pub_year"],
            author=" and ".join(self.get_authors(pub)),
            entry_created_date=datetime.date.today(),
            publication_type=pub_type,
            bibtex_source=pub['bib'],
            added_by_username="admin",
            forum=forum,
            link=pub.get("pub_url", ''),
            source="gscholar",
            status=Publication.STATUS_IMPORTED,
        )

    @staticmethod
    def get_num_citations(pub):
        """Returns the number of citations repoerted in google scholar

        Args:
            pub (dict): publication dict from scholarly

        Returns:
            int: number of citations
        """
        return pub.get("num_citations", 0)

    def update_g_scholar_citation(self, pub, dry_run=False):
        """Updates number of google scholar citations
        in publication model instance

        Args:
            pub (models.Publication): Publication model instance
            dry_run (bool, optional): to not save in DB. Defaults to False.
        """
        result_pub = self.get_one_pub(pub.title)
        similarity = PublicationUtils.how_similar(result_pub['bib']['title'].lower(), pub.title.lower())
        if similarity < PublicationUtils.SIMILARITY:
            return
        g_citations = self.get_num_citations(result_pub)
        existing_gcites = pub.google_citations
        if not dry_run:
            pub.google_citations = g_citations
            pub.save()
        logger.info(
            (
                f"update Google citation number for "
                f"{pub.title} (id: {pub.id}) "
                f"from {existing_gcites} "
                f"to {g_citations}"
            )
        )
        return


def pub_import(
    dry_run=True, year_low=2014, year_high=None
):
    """Returns Publication models of all publicationls that ref chameleon
    and are not in database already
    - Checks if there is a project associated with the publication

    Args:
        dry_run (bool, optional): Defaults to True.
        year_low (int, optional): Defaults to 2014.
        year_high (int, optional): Defaults to datetime.now().year.
    """
    gscholar = GoogleScholarHandler()
    pubs = []
    if not year_high:
        year_high = datetime.date.today().year
    for chameleon_pub in ChameleonPublication.objects.exclude(ref__isnull=True):
        ch_pub = gscholar.get_one_pub(chameleon_pub.title)
        cited_pubs = gscholar.get_cites(ch_pub, year_low=year_low, year_high=year_high)
        for cited_pub in cited_pubs:
            authors = gscholar.get_authors(cited_pub)
            cited_pub_title = cited_pub['bib']['title']
            project = utils.guess_project_for_publication(
                authors, cited_pub["bib"]["pub_year"]
            )
            if not project:
                continue
            if ChameleonPublication.objects.filter(title__iexact=cited_pub_title).exists():
                logger.info(f"{cited_pub_title} is a chameleon publication - ignoring")
                continue
            # this is to find if there is a publication already in database matching to
            # this title and project however this needs to be changed after looking
            # at some examples and how to better handle these dumplicates
            pub_exists = Publication.objects.filter(title=cited_pub_title, project_id=project)
            if pub_exists:
                add_to_all_sources(pub_exists[0], Publication.G_SCHOLAR)
                logger.info(f"{cited_pub_title} is already in Publications table - This check might be outdated.")
                continue
            pub_model = gscholar.get_pub_model(cited_pub)
            pub_model.project = project
            pubs.append(pub_model)
    return pubs
