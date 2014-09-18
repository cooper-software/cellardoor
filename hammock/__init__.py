import types
from version import __version__
from .model import Model
from .collection import Collection


class Hammock(object):
	
	def __init__(self, collections=(), authenticators=(), storage=None):
		if type(collections) == types.ModuleType:
			collection_classes = []
			for k,v in collections.__dict__.items():
				try:
					if issubclass(v, Collection) and v != Collection:
						collection_classes.append(v)
				except TypeError:
					pass
		else:
			collection_classes = collections
		entities = set()
		self.collections_by_class_name = {}
		
		for collection_cls in collection_classes:
			entities.add(collection_cls.entity)
			collection = collection_cls(storage)
			self.collections_by_class_name[collection_cls.__name__] = collection
			setattr(self, collection_cls.plural_name, collection)
			
		self.model = Model(storage, entities)
		
		for collection in self.collections_by_class_name.values():
			new_links = {}
			if collection.links:
				for k, v in collection.links.items():
					if not isinstance(v, basestring):
						v = v.__name__
					referenced_collection = self.collections_by_class_name.get(v)
					new_links[k] = referenced_collection
			collection.links = new_links