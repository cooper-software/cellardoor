import falcon

from . import View
from ..serializers import JSONSerializer, MsgPackSerializer


class MinimalView(View):
	
	serializers = (
		('application/json', JSONSerializer()),
		('application/x-msgpack', MsgPackSerializer())
	)
	
	def get_collection_response(self, req, objs):
		return self.serialize(req, objs)
		
		
	def get_individual_response(self, req, obj):
		return self.serialize(req, obj)