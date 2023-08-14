from django.test import SimpleTestCase
from ..views import GitUrlParser, construct_issues_url

github_urls = [
    "git@github.com:ChameleonCloud/chi-in-a-box.git",
    "https://github.com/ChameleonCloud/chi-in-a-box.git",
    "https://github.com/ChameleonCloud/chi-in-a-box",
    "https://github.com/ChameleonCloud/chi-in-a-box/blob/master/sharing_chi-in-a-box/views.py",
]

gitlab_urls = [
    "https://gitlab.com/fdroid/fdroidclient",
    "https://gitlab.com/fdroid/fdroidclient.git",
    "git@gitlab.com:fdroid/fdroidclient.git",
    "https://gitlab.com/fdroid/fdroidclient/-/blob/master/app/build.gradle",
]


class GitParserTest(SimpleTestCase):
    def test_github_urls(self):
        gp = GitUrlParser()
        for url in github_urls:
            parsed_info = gp.parse(url)
            self.assertEqual(parsed_info["domain"], "github.com")
            self.assertEqual(parsed_info["owner"], "ChameleonCloud")
            self.assertEqual(parsed_info["repo"], "chi-in-a-box")

    def test_gitlab_urls(self):
        gp = GitUrlParser()
        for url in github_urls:
            parsed_info = gp.parse(url)
            self.assertEqual(parsed_info["domain"], "gitlab.com")
            self.assertEqual(parsed_info["owner"], "fdroid")
            self.assertEqual(parsed_info["repo"], "fdroidclient")


class GitIssuesUrl(SimpleTestCase):
    def test_construct_url(self):
        for url in github_urls:
            issue_url = construct_issues_url(url)
            self.assertEqual(
                issue_url, "https://github.com/ChameleonCloud/chi-in-a-box/issues"
            )
        for url in gitlab_urls:
            issue_url = construct_issues_url(url)
            self.assertEqual(
                issue_url, "https://gitlab.com/fdroid/fdroidclient/-/issues"
            )
