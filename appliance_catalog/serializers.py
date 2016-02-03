from django.core.serializers.json import Serializer


class MyJSONSerialiser(Serializer):

    def get_dump_object(self, obj):
        self._current['id'] = obj.pk
        return self._current
