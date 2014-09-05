import falcon

from . import View
from ..serializers import JSONSerializer


class MinimalView(View):
	
	serializers = (
		('application/json', JSONSerializer())
	)
	
	def get_collection_response(self, objs):
		return {'items':objs}
		
		
	def get_individual_response(self, obj):
		return obj