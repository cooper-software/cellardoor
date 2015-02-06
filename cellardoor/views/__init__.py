class View(object):
	
	serializers = None
	
	def get_list_response(self, accept_header, objs):
		raise NotImplementedError
		
		
	def get_individual_response(self, accept_header, obj):
		raise NotImplementedError
		
		
	def serialize(self, accept_header, obj):
		content_type, serializer = self.get_serializer(accept_header)
		return content_type, serializer.serialize(obj)
		
		
	def get_serializer(self, accept_header):
		return self.choose(accept_header, self.serializers)
		
		
	@classmethod
	def choose(cls, accept_header, views):
		if accept_header:
			accept = accept_header.split(';')[0].split(',')
			for a in accept:
				for k,v in views:
					if a == k:
						return k, v
		return views[0]
		
		
from minimal import MinimalView