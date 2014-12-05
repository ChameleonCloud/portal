from HTMLParser import HTMLParser

class Project:
    def __init__(self, username = "", project_title = "", project_id = "", abstract = "", manager_email = "", lead_email = "", is_pi = False):
        self.username = username
        self.title = project_title
        self.project_id = project_id
        self.chargeCode = project_id
        self.abstract = self.strip_tags(abstract)
        self.manager_email = manager_email
        self.lead_email = lead_email
        self.is_pi = is_pi

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
