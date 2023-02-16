import re

from scholarly import ProxyGenerator, scholarly
from scholarly._proxy_generator import MaxTriesExceededException



class GoogleScholarHandler(object):
    def __init__(self):
        """To make google scholar calls using proxy
        """
        self.pg = ProxyGenerator()
        self.pg.Freeproxies()
        self.scholarly = scholarly
        self.scholarly.use_proxy(self.pg)
        self.retries = 0
        self.citations = []
    
    def _handle_proxy_reload(func):
        def inner_f(self, *args, **kwargs):
            while self.retries < 5:
                try:
                    print("calling function from decorator")
                    func(self, *args, **kwargs)
                except MaxTriesExceededException:
                    # this occurs if Google blocks IP
                    self.retries += 1
                    self.new_proxy()
                else:
                    self.retries = 0
                    break
        return inner_f
    
    def _publication_id(self, pub: dict):
        m = re.search("cites=[\d+,]*", pub["citedby_url"])
        return m.group()[6:]
    
    def new_proxy(self):
        """sets a new proxy from free-proxy library
        """
        if not self.pg.proxy_mode.value  == 'FREE_PROXIES':
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
        print("function getting executed")
        return self.scholarly.search_single_pub(title)
    
    @_handle_proxy_reload
    def get_cites(self, pub: dict, year: int=2014) -> list:
        """Returns all the citations of the publication

        Args:
            pub (dict): return of the search_single_pub method
            year (int, optional): year to query from defaults to 2014.

        Returns:
            list: list of publications that cited arg:pub
        """
        pub_id = self._publication_id(pub)
        cites_gen = self.scholarly.search_citedby(pub_id)
        citations = []
        while True:
            try:
                citations.append(
                    self._get_next_cite(cites_gen, year)
                )
            except StopIteration:
                return citations
        
    @_handle_proxy_reload
    def _get_next_cite(self, cites_gen, year):
        return next(cites_gen, year_low=year)

