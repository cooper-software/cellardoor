import types
from functools import partial
from version import __version__
from .model import Model
from .collection import Collection
from .spec.jsonschema import to_jsonschema
from . import errors


class StandardOptionsMixin(object):
	
	def __init__(self, *accessors):
		self._options = {}
		for a in accessors:
			self._add_accessor(a)
		
		
	def identity(self, *args):
		if len(args) == 0:
			return self._options.get('context', {}).get('identity')
		elif args[0] is None:
			if 'context' in self._options:
				self._options['context'].pop('identity', None)
		else:
			if 'context' not in self._options:
				self._options['context'] = {}
			self._options['context']['identity'] = args[0]
		return self
		
		
	def _add_accessor(self, name):
		setattr(self, name, partial(self._accessor, name))
		
		
	def _accessor(self, name, *args):
		if len(args) == 0:
			return self._options.get(name)
		else:
			self._options[name] = args[0]
			return self
			
			
	def _merge_options(self, *options):
		new_options = {}
		for o in options:
			if o:
				new_options.update(o)
		new_options.update(self._options)
		return new_options
	
	
class CellarDoor(StandardOptionsMixin):
	
	def __init__(self, collections=(), authenticators=(), storage=None):
		StandardOptionsMixin.__init__(self, 'bypass_authorization')
		
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
		collections_by_class_name = {}
		collections = {}
		
		for collection_cls in collection_classes:
			entities.add(collection_cls.entity)
			collection = collection_cls(storage)
			collections_by_class_name[collection_cls.__name__] = collection
			collections[collection_cls.plural_name] = collection
			
		self.model = Model(storage, entities)
		
		for collection in collections_by_class_name.values():
			new_links = {}
			if collection.links:
				for k, v in collection.links.items():
					if not isinstance(v, basestring):
						v = v.__name__
					referenced_collection = collections_by_class_name.get(v)
					new_links[k] = referenced_collection
			collection.links = new_links
		
		self.collections = collections
		self.entities = entities
		
		
	def __getattr__(self, name):
		return CollectionProxy(self.collections[name], self._options)
		
		
	def __getitem__(self, key):
		return self.__getattr__(key)
			
			
	def schema(self, base_url):
		return to_jsonschema(self, base_url)
		
		
		
class CollectionProxy(StandardOptionsMixin):
	
	def __init__(self, collection, options=None):
		StandardOptionsMixin.__init__(self,
			'fields',
			'embed',
			'bypass_authorization',
			'show_hidden'
		)
		self._collection = collection
		self._api_options = options
		
		
	def _get_options(self):
		return self._merge_options(self._api_options, self._options)
		
		
	def save(self, item):
		if '_id' in item:
			try:
				return self._collection.replace(item['_id'], item, **self._get_options())
			except errors.NotFoundError:
				pass
			else:
				return
		return self._collection.create(item, **self._get_options())
		
		
	def update(self, id, fields):
		return self._collection.update(id, fields, **self._get_options())
		
		
	def delete(self, id):
		self._collection.delete(id, **self._get_options())
		return self
		
		
	def get(self, id_or_filter):
		if isinstance(id_or_filter, dict):
			list_options = {
				'filter': id_or_filter,
				'limit': 1
			}
			list_options.update(self._options)
			results = self._collection.list(**list_options)
			if len(results) == 0:
				raise errors.NotFoundError
			return results[0]
		else:
			return self._collection.get(id_or_filter, **self._get_options())
		
		
	def find(self, filter=None):
		return ListProxy(self._collection, self._options, filter)
		
		
		
class ListProxy(StandardOptionsMixin):
	
	def __init__(self, collection, options, filter):
		StandardOptionsMixin.__init__(self,
			'fields',
			'embed',
			'sort',
			'offset',
			'limit',
			'bypass_authorization',
			'show_hidden'
		)
		self._collection = collection
		self._base_options = options
		self._options['filter'] = filter
		
		
	def __iter__(self):
		return iter(self._collection.list(**self._merge_options(self._base_options)))
		
		
	def __len__(self):
		return self.count()
		
		
	def count(self):
		return self._collection.list(
			**self._merge_options(self._base_options, {'count': True})
		)
		
		
	def __contains__(self, item_or_id):
		id = item_or_id['_id'] if isinstance(item_or_id, dict) else item_or_id
		new_filter = {'_id': id}
		new_filter.update(self._options['filter'])
		options = self._merge_options(self._base_options)
		options['filter'] = new_filter
		options['limit'] = 1
		results = self._collection.list(**options)
		return len(results) != 0
	