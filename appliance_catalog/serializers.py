from django.core.serializers.json import Serializer


class MyJSONSerialiser(Serializer):

    def get_dump_object(self, obj):
        self._current['id'] = obj.pk
        if 'documentation' in self._current:
            self._current['documentation'] = True if self._current['documentation'] is not None else False
        return self._current
