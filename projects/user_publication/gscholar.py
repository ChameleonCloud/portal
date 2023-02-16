import re

from datetime import datetime
from projects.user_publication import utils
from scholarly import ProxyGenerator
from scholarly import scholarly
from scholarly._proxy_generator import MaxTriesExceededException

from projects.models import ChameleonPublication
from projects.models import Publication

MAX_RETRIES = 10

class GoogleScholarHandler(object):
    def __init__(self):
        """To make google scholar calls using proxy"""
        self.pg = ProxyGenerator()
        self.pg.FreeProxies()
        self.scholarly = scholarly
        self.scholarly.use_proxy(self.pg)
        self.retries = 0
        self.citations = []
        self.tries = 0

    def _handle_proxy_reload(func):
        def inner_f(self, *args, **kwargs):
            while self.retries < MAX_RETRIES:
                try:
                    print("calling function from decorator")
                    print(f"has proxy - {True if self.pg.has_proxy() else False}")
                    resp = func(self, *args, **kwargs)
                except MaxTriesExceededException:
                    # this occurs if Google blocks IP
                    print(f"max retires expception - new proxy retries : {self.retries}")
                    self.retries += 1
                    self.new_proxy()
                else:
                    self.retries = 0
                    break
            return resp
        return inner_f

    def _publication_id(self, pub: dict):
        m = re.search("cites=[\d+,]*", pub["citedby_url"])
        return m.group()[6:]

    def new_proxy(self):
        """sets a new proxy from free-proxy library"""
        if not self.pg.proxy_mode.value == "FREE_PROXIES":
            return
        self.pg.get_next_proxy()
        self.scholarly.use_proxy(self.pg)

    @_handle_proxy_reload
    def get_one_pub(self, title: str):
        """To get one publication from google scholar
        Make sure the title is an exact match

        Args:
            title (str): Title of the publication
        """
        print(title)
        return self.scholarly.search_single_pub(title)

    @_handle_proxy_reload
    def get_cites(
            self, pub, year_low=2014, year_high=datetime.now().year
        ) -> list:
        """Returns all the citations of the publication

        Args:
            pub (dict): return of the search_single_pub method
            year_low (int, optional): year to query from. Defaults to 2014
            year_high (int, optional): yaar to query till. Defaults to datetime.now().year


        Returns:
            list: list of publications that cited arg:pub
        """
        pub_id = self._publication_id(pub)
        print(f"citatios for {pub_id}")
        no_citations = pub['num_citations']
        cites_gen = self.scholarly.search_citedby(
            pub_id, year_low=year_low, year_high=year_high
        )
        citations = []
        while True:
            try:
                cited_pub = self._get_bib(self._get_next_cite(cites_gen))
                citations.append(cited_pub)
                print(len(citations), no_citations)
            except StopIteration:
                return citations

    @_handle_proxy_reload
    def _get_next_cite(self, cites_gen):
        if self.tries == 5:
            self.tries = 0
            raise StopIteration
        self.tries += 1
        return next(cites_gen)
    
    @_handle_proxy_reload
    def _get_bib(self, pub):
        bibt = self.scholarly.bibtex(pub)
        pub.update({"bibtex": bibt})
        return pub

    def get_authors(self, pub):
        bibt = pub['bibtex']
        match = re.search(r'author\s*=\s*\{([\w\s,]+)\}', bibt)
        if match:
            authors_t = match.groups()[0]
        else:
            print(f"cannot parse - {bibt}")
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
    dry_run=True, scraper_api_key="", year_low=2014, year_high=datetime.now().year
):
    """Returns Publication models of all publicationls that ref chameleon
    and are not in database already
    - Checks if there is a project associated with the publication

    Args:
        dry_run (bool, optional): _description_. Defaults to True.
        scraper_api_key (str, optional): _description_. Defaults to ''.
        year_low (int, optional): _description_. Defaults to 2014.
    """
    gscholar = GoogleScholarHandler()
    pubs = []
    for chameleon_pub in ChameleonPublication.objects.exclude(ref__isnull=True):
        ch_pub = gscholar.get_one_pub(chameleon_pub.title)
        print(ch_pub)
        cited_pubs = gscholar.get_cites(ch_pub, year_low=year_low, year_high=year_high)
        for cited_pub in cited_pubs:
            authors = gscholar.get_authors(cited_pub)
            if not authors:
                continue
            proj = utils.guess_project_for_publication(
                authors, cited_pub["bib"]["pub_year"]
            )
            if proj:
                pubs.append(gscholar.get_pub_model(cited_pub))
            if len(pubs) == 5:
                return pubs
    return pubs
