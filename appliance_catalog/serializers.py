from django.core.serializers.json import Serializer


class MyJSONSerialiser(Serializer):

    def get_dump_object(self, obj):
        self._current['id'] = obj.pk
        if 'documentation' in self._current and self._current['documentation']:
            self._current['documentation'] = True
        else:
            self._current['documentation'] = False
        return self._current
