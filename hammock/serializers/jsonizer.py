import json
from datetime import datetime


class HammockJSONEncoder(json.JSONEncoder):
	
	def default(self, obj):
		try:
			iterable = iter(obj)
		except TypeError:
			pass
		else:
			return list(iterable)
		
		if isinstance(obj, datetime):
			return obj.isoformat()
		
		return super(HammockJSONEncoder, self).default(obj)


def serialize(obj):
	return json.dumps(obj, cls=HammockJSONEncoder)
	
	
def unserialize(data):
	return json.loads(data)