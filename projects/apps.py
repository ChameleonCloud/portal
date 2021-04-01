from django.apps import AppConfig
from projects import monkey_patching


class ProjectsConfig(AppConfig):
    name = "projects"

    def ready(self):
        print("MONKEY PATCHING USER MODEL")
        monkey_patching.patch_user_model()
