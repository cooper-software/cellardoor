import re
import json
from datetime import datetime
import collections

from . import Serializer


class CellarDoorJSONEncoder(json.JSONEncoder):
	
	def default(self, obj):
		if isinstance(obj, collections.Iterable):
			return list(obj)
		
		if isinstance(obj, datetime):
			return obj.isoformat()
		
		return super(CellarDoorJSONEncoder, self).default(obj)
		
		
def as_date(obj):
	if '_date' in obj:
		return datetime(*map(int, re.split('[^\d]', obj['_date'])[:-1]))
	else:
		return obj
		


class JSONSerializer(Serializer):
	
	mimetype = 'application/json'
	
	def serialize(self, obj):
		return json.dumps(obj, cls=CellarDoorJSONEncoder)
		
		
	def unserialize(self, stream):
		return json.load(stream, object_hook=as_date)
		
		
	def unserialize_string(self, data):
		return json.loads(data, object_hook=as_date)