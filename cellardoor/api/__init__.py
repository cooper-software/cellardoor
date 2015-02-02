"""
Provides a friendly interface for managing 
"""

from functools import partial
from .interface import Interface
from .. import errors
from ..spec.jsonschema import to_jsonschema


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
	
	
class API(StandardOptionsMixin):
	
	def __init__(self, model):
		StandardOptionsMixin.__init__(self, 'bypass_authorization')
		self.model = model
		self.Interface = type('Interface', (Interface,), {'api':self})
		self.interfaces = {}
		self.interfaces_by_entity = {}
		
		
	def add_interface(self, interface):
		if not self.model.is_frozen:
			self.model.freeze()
			
		if interface.entity not in self.model:
			raise Exception, "The %s entity is not defined in this API's model" % interface.entity.__name__
			
		interface_inst = interface()
		self.interfaces[interface.plural_name] = interface_inst
		if interface.entity.__name__ not in self.interfaces_by_entity:
			self.interfaces_by_entity[interface.entity.__name__] = []
		self.interfaces_by_entity[interface.entity.__name__].append(interface_inst)
		
		
	def refresh(self):
		for k, v in self.interfaces.items():
			self.interfaces[k] = v.__class__()
		
		
	def __getattr__(self, name):
		return InterfaceProxy(self.interfaces[name], self._options)
		
		
	def __getitem__(self, key):
		return self.__getattr__(key)
			
			
	def schema(self, base_url):
		return to_jsonschema(self, base_url)
		
		
	def get_interface_for_entity(self, entity):
		return self.interfaces_by_entity[entity.__name__][0]
		
		
class InterfaceProxy(StandardOptionsMixin):
	
	def __init__(self, interface, options=None):
		StandardOptionsMixin.__init__(self,
			'fields',
			'embed',
			'allow_embedding',
			'bypass_authorization',
			'show_hidden'
		)
		self._interface = interface
		self._api_options = options
		
		for when, events in self._interface.hooks.listeners.items():
			for event in events.keys():
				method_name = '%s_%s' % (when, event)
				setattr(self, method_name, getattr(self._interface.hooks, method_name))
		
		
	def __getattr__(self, name):
		return partial(self.link, name)
		
		
	def link(self, name, id, **kwargs):
		link = self._interface.entity.get_link(name)
		if not link:
			raise Exception, "No link called '%s'" % name
		return LinkProxy(self._interface, self._get_options(kwargs), name, id)
 		
 		
	def create(self, item, **kwargs):
		return self._interface.create(item, **self._get_options(kwargs))
 		
		
	def save(self, item, **kwargs):
		if '_id' in item:
			return self._interface.replace(item['_id'], item, **self._get_options(kwargs))
		return self._interface.create(item, **self._get_options(kwargs))
		
		
	def update(self, id, fields, **kwargs):
		return self._interface.update(id, fields, **self._get_options(kwargs))
		
		
	def delete(self, id, **kwargs):
		self._interface.delete(id, **self._get_options(kwargs))
		return self
		
		
	def get(self, id_or_filter, **kwargs):
		if isinstance(id_or_filter, dict):
			list_options = {
				'filter': id_or_filter,
				'limit': 1
			}
			list_options.update(self._options)
			list_options.update(kwargs)
			results = self._interface.list(**list_options)
			if len(results) == 0:
				raise errors.NotFoundError
			return results[0]
		else:
			return self._interface.get(id_or_filter, **self._get_options(kwargs))
		
		
	def find(self, filter=None, **kwargs):
		return FilterProxy(self._interface, self._get_options(kwargs), filter)
		
		
	def _get_options(self, options):
		return self._merge_options(self._api_options, self._options, options)
		
		
		
class FilterProxy(StandardOptionsMixin):
	
	def __init__(self, interface, options, filter):
		StandardOptionsMixin.__init__(self,
			'fields',
			'embed',
			'allow_embedding',
			'sort',
			'offset',
			'limit',
			'bypass_authorization',
			'show_hidden',
			'filter'
		)
		self._interface = interface
		self._base_options = options
		self._options['filter'] = filter
		
		
	def list(self):
		return list(iter(self))
		
		
	def __iter__(self):
		return iter(self._list(self._merge_options(self._base_options)))
		
		
	def __len__(self):
		return self.count()
		
		
	def count(self, **kwargs):
		return self._list(
			self._merge_options(self._base_options, kwargs, {'count': True})
		)
		
		
	def __contains__(self, item_or_id):
		id = item_or_id['_id'] if isinstance(item_or_id, dict) else item_or_id
		new_filter = {'_id': id}
		new_filter.update(self._options['filter'])
		options = self._merge_options(self._base_options)
		options['filter'] = new_filter
		options['limit'] = 1
		results = self._list(options)
		return len(results) != 0
		
	def _list(self, options):
		return self._interface.list(**options)
		
		
class LinkProxy(FilterProxy):
	
	def __init__(self, interface, options, name, id):
		super(LinkProxy, self).__init__(interface, options, {})
		self._name = name
		self._id = id
		
	def _list(self, options):
		return self._interface.link(self._id, self._name, **options)
		