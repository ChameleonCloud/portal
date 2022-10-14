import datetime
from difflib import SequenceMatcher
import re


class PublicationUtils:
    @staticmethod
    def get_month(bibtex_entry):
        month = bibtex_entry.get("month")
        m = None
        try:
            m = int(month)
        except Exception:
            pass
        try:
            m = datetime.datetime.strptime(month, "%b").month
        except Exception:
            pass
        try:
            m = datetime.datetime.strptime(month, "%B").month
        except Exception:
            pass

        return m

    @staticmethod
    def get_forum(bibtex_entry):
        forum = []
        if "journal" in bibtex_entry:
            forum.append(bibtex_entry["journal"])
        if "booktitle" in bibtex_entry:
            forum.append(bibtex_entry["booktitle"])
        if "series" in bibtex_entry:
            forum.append(bibtex_entry["series"])
        if "publisher" in bibtex_entry:
            forum.append(bibtex_entry["publisher"])
        if "school" in bibtex_entry:
            forum.append(bibtex_entry["school"])
        if "institution" in bibtex_entry:
            forum.append(bibtex_entry["institution"])
        if "address" in bibtex_entry:
            forum.append(bibtex_entry["address"])
        return ",".join(forum)

    @staticmethod
    def get_link(bibtex_entry):
        if "url" in bibtex_entry:
            return bibtex_entry.get("url")
        if "doi" in bibtex_entry:
            return "https://doi.org/" + bibtex_entry.get("doi")
        if "note" in bibtex_entry:
            m = re.search("^\\\\url{(.+?)}$", bibtex_entry["note"])
            if m:
                return m.group(1)
        if "howpublished" in bibtex_entry:
            m = re.search("^\\\\url{(.+?)}$", bibtex_entry["howpublished"])
            if m:
                return m.group(1)
        return None

    @staticmethod
    def get_pub_type(bibtex_entry):
        bibtex_type = bibtex_entry.get("ENTRYTYPE")
        if not bibtex_type:
            return "other"
        bibtex_entry.pop("abstract", None)
        bibtex_as_str = str(bibtex_entry).lower()

        if "arxiv" in bibtex_as_str:
            return "preprint"
        if "poster" in bibtex_as_str:
            return "poster"
        if "thesis" in bibtex_as_str:
            if "ms" in bibtex_as_str or "master thesis" in bibtex_as_str:
                return "ms thesis"
            if "phd" in bibtex_as_str:
                return "phd thesis"
            return "thesis"
        if "github" in bibtex_as_str:
            return "github"
        if "patent" in bibtex_as_str:
            return "patent"
        if bibtex_type == "incollection":
            return "book chapter"
        if (
            "techreport" in bibtex_as_str
            or "tech report" in bibtex_as_str
            or "internal report" in bibtex_as_str
        ):
            return "tech report"
        if bibtex_type == "article":
            return "journal article"
        if bibtex_type == "inproceedings" or "proceeding" in bibtex_as_str:
            return "conference paper"

        return "other"

    @staticmethod
    def how_similar(str1, str2):
        return SequenceMatcher(None, str1, str2).ratio()
