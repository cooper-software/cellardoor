import json
from datetime import datetime

from . import Serializer


class CellarDoorJSONEncoder(json.JSONEncoder):
	
	def default(self, obj):
		try:
			iterable = iter(obj)
		except TypeError:
			pass
		else:
			return list(iterable)
		
		if isinstance(obj, datetime):
			return obj.isoformat()
		
		return super(CellarDoorJSONEncoder, self).default(obj)
		


class JSONSerializer(Serializer):
	
	mimetype = 'application/json'
	
	def serialize(self, obj):
		return json.dumps(obj, cls=CellarDoorJSONEncoder)
		
		
	def unserialize(self, stream):
		return json.load(stream)