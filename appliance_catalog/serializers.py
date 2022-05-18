from django.core.serializers.json import Serializer
from appliance_catalog.models import Appliance, Keyword


class ApplianceJSONSerializer(Serializer):
    def get_dump_object(self, obj):
        if isinstance(obj, Appliance):
            self._current["id"] = obj.pk
            self._current["documentation"] = (
                True if self._current["documentation"] else False
            )
            self._current["keywords"] = [k.name for k in obj.keywords.all()]

        return self._current


class KeywordJSONSerializer(Serializer):
    def get_dump_object(self, obj):
        if isinstance(obj, Keyword):
            self._current["id"] = obj.pk

        return self._current
