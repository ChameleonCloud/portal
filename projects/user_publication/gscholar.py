import logging
import re
from datetime import datetime
from pathlib import Path

from scholarly import ProxyGenerator, scholarly
from scholarly._proxy_generator import MaxTriesExceededException

from projects.models import ChameleonPublication, Publication
from projects.user_publication import utils

logger = logging.getLogger("projects")

MAX_RETRIES = 10


def handle_scrapper():
    scraper_config = Path("scraper.config")
    scraper_api = ''
    if scraper_config.exists():
        with scraper_config.open('r') as s_config:
            logger.info("Using scraper.config file for API key")
            scraper_api = s_config.read()
    if not scraper_api:
        scraper_api = input("Enter the scraper API key, if you have one, else press enter: ")
    if scraper_api:
        with scraper_config.open('w') as s_config:
            s_config.write(scraper_api)
    return scraper_api


class GoogleScholarHandler(object):
    def __init__(self):
        """To make google scholar calls using proxy"""
        self.pg = ProxyGenerator()
        self.scholarly = scholarly
        scraper_api = handle_scrapper()
        if scraper_api:
            self.pg.ScraperAPI(scraper_api)
            logger.info("Using scrapper proxy")
        else:
            self.pg.FreeProxies()
            logger.info("Using Free proxy")
        self.scholarly.use_proxy(self.pg)
        self.retries = 0
        self.citations = []

    def _handle_proxy_reload(func):
        def inner_f(self, *args, **kwargs):
            while self.retries < MAX_RETRIES:
                try:
                    logger.info(f"Using Free proxy - {True if self.pg.has_proxy() else False}")
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
        if not self.pg.proxy_mode.value == "FREE_PROXIES":
            return
        logger.info("Getting new free proxy")
        self.pg.get_next_proxy()
        self.scholarly.use_proxy(self.pg)

    @_handle_proxy_reload
    def get_one_pub(self, title: str):
        """To get one publication from google scholar
        Make sure the title is an exact match

        Args:
            title (str): Title of the publication
        """
        return self.scholarly.search_single_pub(title)

    @_handle_proxy_reload
    def get_cites(
            self, pub, year_low=2014,
            year_high=datetime.now().year
    ):
        """Returns all the citations of the publication

        Args:
            pub (dict): return of the search_single_pub method
            year_low (int, optional): year to query from. Defaults to 2014
            year_high (int, optional): yaar to query till. Defaults to datetime.now().year

        Returns:
            list: list of publications that cited arg:pub
        """
        pub_id = self._publication_id(pub)
        logger.info(f"Getting citations for {pub['bib']['title']}")
        no_citations = pub['num_citations']
        cites_gen = self.scholarly.search_citedby(
            pub_id, year_low=year_low, year_high=year_high
        )
        citations = []
        cit_count = 0
        while True:
            try:
                cited_pub = self._get_bib(self._get_next_cite(cites_gen))
                citations.append(cited_pub)
                cit_count += 1
                logger.info(f"Got {len(cit_count)} / {no_citations}")
            except StopIteration:
                logger.info(f"End of iteration. Got {len(citations)} / {no_citations}")
                return citations

    @_handle_proxy_reload
    def _get_next_cite(self, cites_gen):
        return next(cites_gen)

    @_handle_proxy_reload
    def _get_bib(self, pub):
        bibt = self.scholarly.bibtex(pub)
        pub.update({"bibtex": bibt})
        return pub

    def get_authors(self, pub):
        """returns a list of authors in a publication

        Args:
            pub (dict): scholarly return of the publication

        Returns:
            list: list of authors in ["firstname lastname",] format
        """
        bibt = pub['bibtex']
        bibt = utils.decode_unicode_text(bibt)
        match = re.search(r'author\s*=\s*\{([\w\s-,]+)\}', bibt)
        if match:
            authors_t = match.groups()[0]
        else:
            # this mostly never happens - if it does - log it
            logger.info(f"cannot parse bibtex, so ignoring - {bibt}")
            return
        if "and" in authors_t:
            authors = authors_t.split(" and ")
        else:
            authors = [authors_t]
        parsed_authors = []
        for author in authors:
            parsed_authors.append(utils.parse_author(author))
        return authors

    def get_pub_model(self, pub):
        return Publication(
            title=utils.decode_unicode_text(pub["bib"]["title"]),
            year=pub["bib"]["pub_year"],
            author=" and ".join(self.get_authors(pub)),
            entry_created_date=datetime.date.today(),
            publication_type=utils.get_pub_type(pub["bib"]["ENTRYTYPE"]),
            bibtex_source="{}",
            added_by_username="admin",
            forum=pub["bib"]["booktitle"],
            link=pub["pub_url"],
            source="gscholar",
            status=Publication.STATUS_IMPORTED,
        )


def pub_import(
    dry_run=True, year_low=2014, year_high=datetime.now().year
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
    for chameleon_pub in ChameleonPublication.objects.filter(id=14):
        ch_pub = gscholar.get_one_pub(chameleon_pub.title)
        cited_pubs = gscholar.get_cites(ch_pub, year_low=year_low, year_high=year_high)
        for cited_pub in cited_pubs:
            authors = gscholar.get_authors(cited_pub)
            cited_pub_title = cited_pub['bib']['title']
            if not authors:
                continue
            proj = utils.guess_project_for_publication(
                authors, cited_pub["bib"]["pub_year"]
            )
            if not proj:
                continue
            if ChameleonPublication.objects.filter(title__iexact=cited_pub_title).exists():
                logger.info(f"{cited_pub_title} is a chameleon publication - ignoring")
                continue
            if Publication.objects.filter(title=cited_pub_title, project_id=proj).exists():
                logger.info(f"{cited_pub_title} is already is Publications table")
                continue
            pubs.append(gscholar.get_pub_model(cited_pub))
    return pubs
