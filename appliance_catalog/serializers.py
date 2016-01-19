from django.core.serializers import json

class MyJSONSerialiser(json.Serializer):
	def get_dump_object(self, obj):
		self._current['id'] = obj.pk
		return self._current