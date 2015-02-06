import falcon

from . import View
from ..serializers import JSONSerializer, MsgPackSerializer


class MinimalView(View):
	
	serializers = (
		('application/json', JSONSerializer()),
		('application/x-msgpack', MsgPackSerializer())
	)
	
	def get_list_response(self, accept_header, objs):
		return self.serialize(accept_header, objs)
		
		
	def get_individual_response(self, accept_header, obj):
		return self.serialize(accept_header, obj)