from HTMLParser import HTMLParser

class Project:
    def __init__(self, username = "", project_title = "", project_id = "", abstract = "", is_pi = False, pi_email = ""):
        self.username = username
        self.title = project_title
        self.chargeCode = project_id
        self.abstract = self.strip_tags(abstract)
        self.is_pi = is_pi
        self.pi_email = pi_email

    def strip_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
