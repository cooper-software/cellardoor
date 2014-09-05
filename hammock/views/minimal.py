import falcon

from . import View
from ..serializers import JSONSerializer, MsgPackSerializer


class MinimalView(View):
	
	serializers = (
		('application/x-msgpack', MsgPackSerializer()),
		('application/json', JSONSerializer())
	)
	
	def get_collection_response(self, req, objs):
		return self.serialize(req, {'items':objs})
		
		
	def get_individual_response(self, req, obj):
		return self.serialize(req, obj)