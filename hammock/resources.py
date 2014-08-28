class Resource(object):

	def __init__(self, collection_cls):
		self.collection_cls = collection_cls


class AllResource(Resource):
	
	def on_get(self, req, resp):
		pass

	def on_post(self, req, resp):
		pass

	def on_delete(self, req, resp):
		pass



class SingleResource(Resource):
	pass


def create_api(collections):
	pass