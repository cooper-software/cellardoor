from version import __version__
from .model import Model
from .resource import Resource

class Hammock(object):
	
	def __init__(self, api, resources=(), views=(), authenticators=(), storage=None):
		entities = set()
		resource_instances = {}
		
		for resource_cls in resources:
			entities.add(resource_cls.entity)
			resource = resource_cls(storage, views)
			resource.add_to_api(api)
			resource_instances[resource_cls.__name__] = resource
			
		model = Model(*entities)
		storage.set_model(model)
		
		for resource in resource_instances.values():
			new_link_resources = {}
			if resource.link_resources:
				for k, v in resource.link_resources.items():
					if not isinstance(v, basestring):
						v = v.__name__
					referenced_resource = resource_instances.get(v)
					new_link_resources[k] = referenced_resource
			resource.link_resources = new_link_resources