from django.core.serializers.json import Serializer
from projects.models import ProjectExtras


class ProjectExtrasJSONSerializer(Serializer):

    def get_dump_object(self, obj):
        if isinstance(obj, ProjectExtras):
            self._current['project_id'] = obj.project_id
            self._current['nickname'] = obj.nickname
        return self._current

