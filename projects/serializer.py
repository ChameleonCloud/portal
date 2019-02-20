from django.core.serializers.json import Serializer
from projects.models import ProjectExtras


class ProjectExtrasJSONSerializer(Serializer):

    def get_dump_object(self, obj):
        if isinstance(obj, ProjectExtras):
            self._current['tas_project_id'] = obj.tas_project_id
            self._current['charge_code'] = obj.charge_code
            self._current['nickname'] = obj.nickname
        return self._current

