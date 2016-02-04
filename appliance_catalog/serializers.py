from django.core.serializers.json import Serializer


class MyJSONSerialiser(Serializer):

    def get_dump_object(self, obj):
        self._current['id'] = obj.pk
        if 'documentation' in self._current:
            del self._current['documentation']
        return self._current
