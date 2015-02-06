import types
import collections
from copy import deepcopy
import inspect
from ..model import ListOf, Link, InverseLink
from ..events import EventManager
from .. import errors
from .methods import *


__all__ = [
	'Interface'
]


class RuleSet(object):
	
	def __init__(self, method_authorization):
		self.enabled_methods = set()
		self.item_rules = {}
		self.non_item_rules = {}
		
		if method_authorization:
			for k,v in method_authorization.items():
				if not isinstance(k, tuple):
					k = (k,)
				for method in k:
					self.enabled_methods.add(method)
					if v is None:
						continue
					if v.uses('item'):
						rules = self.item_rules
					else:
						rules = self.non_item_rules
					if method not in rules:
						rules[method] = []
					rules[method].append(v)
				
				
	def enforce_item_rules(self, method, item, context):
		rules = self.item_rules.get(method)
		if rules:
			if isinstance(item, (collections.Sequence, types.GeneratorType)):
				for i in item:
					self.enforce_rules(rules, i, context)
			else:
				self.enforce_rules(rules, item, context)
		
		
	def enforce_non_item_rules(self, method, context):
		rules = self.non_item_rules.get(method)
		if rules:
			self.enforce_rules(rules, None, context)
		
		
	def enforce_rules(self, rules, item, context):
		context = context if context else {}
		context['item'] = item
		no_identity = 'identity' not in context
		for rule in rules:
			if no_identity and rule.uses('identity'):
				raise errors.NotAuthenticatedError()
			if not rule(context):
				raise errors.NotAuthorizedError()
				
				
				
class OptionsFactory(object):
	
	
	def __init__(self, storage=None,
					   hidden_fields=(), 
					   hidden_field_authorization=None,
					   enabled_filters=(), 
					   enabled_sort=(), 
					   default_sort=(), 
					   default_limit=0, 
					   max_limit=0):
		self.storage = storage
		self.hidden_fields = set(hidden_fields)
		self.hidden_field_authorization = hidden_field_authorization
		self.enabled_filters = set(enabled_filters)
		self.enabled_filters_no_hidden = self.enabled_filters.difference(self.hidden_fields)
		self.enabled_sort = set(enabled_sort)
		self.enabled_sort_no_hidden = self.enabled_sort.difference(self.hidden_fields)
		self.default_sort = default_sort
		self.default_limit = default_limit
		self.max_limit = max_limit
		
		self.enabled_filters.update(('_id', '_type'))
		self.enabled_filters_no_hidden.update(('_id', '_type'))
		
		
	def create(self, options_dict, list=False):
		copied_options_dict = deepcopy(options_dict)
		if list:
			return ListOptions( self.process_list(copied_options_dict) )
		else:
			return BaseOptions( self.process(copied_options_dict) )
			
	
	def process(self, options):
		new_options = {}
		new_options['embed'] = options.get('embed', None)
		if new_options['embed']:
			new_options['embed'] = set(new_options['embed'])
		new_options['allow_embedding'] = options.get('allow_embedding', True)
		new_options['fields'] = options.get('fields', None)
		if new_options['fields']:
			new_options['fields'] = set(new_options['fields'])
		new_options['show_hidden'] = options.get('show_hidden', False)
		new_options['context'] = options.get('context', {})
		new_options['bypass_authorization'] = options.get('bypass_authorization', False)
		
		if new_options['bypass_authorization']:
			new_options['can_show_hidden'] = True
		else:
			new_options['can_show_hidden'] = self.can_show_hidden(new_options['context'])
		
		return new_options
			
			
	def can_show_hidden(self, context):
		if self.hidden_field_authorization:
			if self.hidden_field_authorization.uses('identity') and 'identity' not in context:
				return False
			elif not self.hidden_field_authorization(context):
				return False
		return True
		
		
	def process_list(self, options):
		new_options = self.process(options)
		new_options['filter'] = options.get('filter', None)
		new_options['sort'] = options.get('sort', None)
		new_options['sort'] = options['sort'] if options.get('sort') else self.default_sort
		new_options['offset'] = options.get('offset', 0)
		new_options['limit'] = options.get('limit', 0)
		new_options['limit'] = new_options['limit'] if new_options['limit'] else self.default_limit
		if not new_options['bypass_authorization']:
			new_options['limit'] = min(new_options['limit'], self.max_limit)
		new_options['count'] = options.get('count', False)
		
		self.check_filter(new_options)
		self.check_sort(new_options)
		
		return new_options
		
		
	def check_filter(self, options):
		if not options['filter'] or options['bypass_authorization']:
			return
		if not self.enabled_filters:
			raise errors.CompoundValidationError({'filter':'Filtering is disabled.'})
		if options['can_show_hidden']:
			allowed_fields = self.enabled_filters
		else:
			allowed_fields = self.enabled_filters_no_hidden
		self.storage.check_filter(options['filter'], allowed_fields, options['context'])
		
		
	def check_sort(self, options):
		if not options['sort'] or options['bypass_authorization']:
			return
		if not self.enabled_sort:
			raise errors.CompoundValidationError({'sort':'Sorting is disabled.'})
		if options['can_show_hidden']:
			allowed_fields = self.enabled_sort
		else:
			allowed_fields = self.enabled_sort_no_hidden
			
		for k in options['sort']:
			field_name = k[1:]
			if field_name not in allowed_fields:
				raise errors.DisabledFieldError('The "%s" field cannot be used for sorting.' % field_name)


class BaseOptions(object):
	
	def __init__(self, options):
		self._options = options
		self._embed_by_class = {}
		
		
	def __getitem__(self, key):
		return self._options[key]
		
		
	def __getattr__(self, key):
		return self.__getitem__(key)
		
		
	def get_embed_for_type(self, base_entity, type):
		type = type.split('.')[-1]
		
		if type in self._embed_by_class:
			return self._embed_by_class[type]
		
		entity = None
		
		if type == base_entity.__name__:
			entity = base_entity
		else:
			for c in base_entity.children:
				if c.__name__ == type:
					entity = c
					break
		
		if entity is None:
			raise Exception, "Can't find the entity for '%s'" % type
		
		if self._options['embed']:
			embed = self._options['embed'].intersection(entity.embeddable)
		else:
			embed = entity.embed_by_default
		
		if self._options['fields']:
			embed.update( entity.embeddable.intersection( self._options['fields'] ) )
		
		if not self._options['show_hidden'] or not self._options['can_show_hidden']:
			embed.difference_update(entity.hidden_fields)
		
		self._embed_by_class[type] = (entity, embed)
		return entity, embed
		
		
		
class ListOptions(BaseOptions):
	pass



class InterfaceType(type):
	
	def __init__(cls, name, bases, attrs):
		if name == 'Interface':
			return
		
		members = dict(inspect.getmembers(cls))
		singular_name = members.get('singular_name')
		plural_name = members.get('plural_name')
		entity = members.get('entity')
		if entity:
			entity_name = entity.__name__.lower()
		else:
			raise Exception, "An interface must specify an entity to manage"
		
		if not singular_name and not plural_name:
			singular_name = entity_name
			plural_name = entity_name + 's'
		
		elif not singular_name:
			if plural_name[-1] == 's':
				singular_name = plural_name[:-1]
			else:
				singular_name = plural_name
		
		elif not plural_name:
			plural_name = singular_name + 's'
		
		storage = None
		for b in bases:
			if b.__name__ == 'Interface':
				storage = b.api.model.storage
				break
		
		cls.singular_name = singular_name
		cls.plural_name = plural_name
		cls.hooks = EventManager('create', 'update', 'delete')
		cls.rules = RuleSet(members.get('method_authorization'))
		cls.storage = storage
		
		hidden_fields = set(entity.hidden_fields.copy())
		for c in entity.children:
			hidden_fields.update(c.hidden_fields)
		
		cls.options_factory = OptionsFactory(
			storage=storage,
		    hidden_fields=hidden_fields, 
		    hidden_field_authorization=members.get('hidden_field_authorization'),
		    enabled_filters=members.get('enabled_filters', ()),
		    enabled_sort=members.get('enabled_sort', ()),
		    default_sort=members.get('default_sort', ()),
		    default_limit=members.get('default_limit', 0),
		    max_limit=members.get('max_limit', 100)
		)
		
		cls.api.add_interface(cls)
		
		
		
class Interface(object):
	
	__metaclass__ = InterfaceType
	
	
	# The entity class that will be exposed through this interface.
	entity = None
	
	# A dict of authorization rules. The key is a `cellardoor.method` or a tuple of methods 
	# and the value is an authorization rule.
	method_authorization = None
	
	# A `cellardoor.authorization.AuthenticationExpression` that must be met for hidden fields to be shown.
	hidden_field_authorization = None
	
	# A list or tuple of fields that are allowed to be used in filters.
	enabled_filters = ()
	
	# A list or tuple of fields that can be used in sorting.
	enabled_sort = ()
	
	# A list or tuple of fields that is a subset of `enabled_sort` that will be
	# used to sort results when no sort is supplied in the request.
	default_sort = ()
	
	default_limit = 0
	max_limit = 100
	
	
	def __init__(self):
		for method in ALL:
			if method not in self.rules.enabled_methods:
				setattr(self, method, self.disabled_method_error)
			
			
	def set_storage(self, storage):
		self.storage = storage
		self.options_factory.storage = storage
			
			
	def list(self, **kwargs):
		options = self.options_factory.create(kwargs, list=True)
		
		if not options['bypass_authorization']:
			self.rules.enforce_non_item_rules(LIST, options['context'])
		
		result = self.storage.get(self.entity, 
							filter=options.filter, sort=options.sort, 
							offset=options.offset, limit=options.limit,
							count=options.count)
		
		if options.count:
			return result
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(LIST, result, options.context)
				
		return self.post(LIST, options, result)
		
		
	def create(self, fields, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(CREATE, options.context)
		
		self.entity.hooks.fire_before_create(fields, options.context)
		self.hooks.fire_before_create(fields, options.context)
		
		item = self.entity.validator.validate(fields)
		item['_id'] = self.storage.create(self.entity, item)
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(CREATE, item, options.context)
		
		item = self.post(CREATE, options, item)
		
		self.entity.hooks.fire_after_create(item, options.context)
		self.hooks.fire_after_create(item, options.context)
		
		return item
		
		
	def get(self, id, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(GET, options.context)
		
		item = self.storage.get_by_id(self.entity, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(GET, item, options.context)
		
		return self.post(GET, options, item)
		
		
	def update(self, id, fields, _replace=False, _method=UPDATE, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(_method, options.context)
		
		self.entity.hooks.fire_before_update(id, fields, options.context)
		self.hooks.fire_before_update(id, fields, options.context)
		
		if not options.bypass_authorization and UPDATE in self.rules.item_rules:
			item = self.storage.get_by_id(self.entity, id)
			if item is None:
				raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
			self.rules.enforce_item_rules(_method, item, options.context)
		
		new_fields = self.entity.validator.validate(fields, enforce_required=_replace)
		fields = new_fields
		item = self.storage.update(self.entity, id, fields, replace=_replace)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		item = self.post(_method, options, item)
		
		self.entity.hooks.fire_after_update(item, options.context)
		self.hooks.fire_after_update(item, options.context)
		
		return item
		
		
	def replace(self, id, fields, **kwargs):
		return self.update(id, fields, _replace=True, _method=REPLACE, **kwargs)
		
		
	def delete(self, id, inverse_delete=True, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(DELETE, options.context)
		
		item = self.storage.get_by_id(self.entity, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(DELETE, item, options.context)
		
		self.entity.hooks.fire_before_delete(id, options.context)
		self.hooks.fire_before_delete(id, options.context)
		
		if inverse_delete:
			self.inverse_delete(id)
		
		self.storage.delete(self.entity, id)
		self.post(DELETE, options)
		
		options.context['item'] = item
		self.entity.hooks.fire_after_delete(id, options.context)
		self.hooks.fire_after_delete(id, options.context)
		
		
	def inverse_delete(self, id):
		cascade = self.entity.inverse_links.get(Link.CASCADE)
		if cascade:
			for link in cascade:
				link_interface = self.api.get_interface_for_entity(link.entity)
				items = link_interface.list(filter={link.field:id}, fields=[])
				for item in items:
					link_interface.delete(item['_id'])
		nullify = self.entity.inverse_links.get(Link.NULLIFY)
		if nullify:
			for link in nullify:
				link_interface = self.api.get_interface_for_entity(link.entity)
				items = link_interface.list(filter={link.field:id}, fields=[link.field])
				if link.multiple:
					for item in items:
						new_ids = filter(lambda x: x != id, item[link.field])
						link_interface.update(item['_id'], {link.field:new_ids})
				else:
					for item in items:
						link_interface.update(item['_id'], {link.field:None})
		
		
	def link(self, id, link_name, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(GET, options.context)
		
		item = self.storage.get_by_id(self.entity, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(GET, item, options.context)
			
		target_interface = self.get_linked_interface(link_name)
		if target_interface is None:
			raise errors.NotFoundError("The %s interface has no link '%s' defined" % (self.plural_name, link_name))
		link_field = getattr(self.entity, link_name)
		
		return target_interface.resolve_link(item, link_name, link_field, kwargs)
		
		
	def resolve_link(self, source_item, link_name, link_field, options):
		"""Get the item(s) pointed to by a link or link"""
		options = self.options_factory.create(options, list=True)
		
		if isinstance(link_field, InverseLink):
			return self._resolve_inverse_link(source_item, link_field, options)
		else:
			return self._resolve_link(source_item, link_name, link_field, options)
		
		
	def _resolve_inverse_link(self, source_item, link_field, options):
		"""
		Get the items for a single or multiple link
		"""
		options.filter = options.filter if options.filter else {}
		options.filter[link_field.field] = source_item['_id']
		
		if link_field.multiple:
			self.rules.enforce_non_item_rules(LIST, options.context)
			result = self.storage.get(self.entity, 
							filter=options.filter, sort=options.sort, 
							offset=options.offset, limit=options.limit,
							count=options.count)
			if options.count:
				return result
			self.rules.enforce_item_rules(LIST, result, options.context)
			return self.post(LIST, options, result)
		else:
			try:
				if not options.bypass_authorization:
					self.rules.enforce_non_item_rules(GET, options.context)
				item = next(iter(self.storage.get(self.entity, filter=options.filter, limit=1)))
				if not options.bypass_authorization:
					self.rules.enforce_item_rules(GET, item, options.context)
				return self.post(GET, options, item)
			except StopIteration:
				pass
		
	
	def _resolve_link(self, source_item, link_name, link_field, options):
		"""Get the items for a single or multiple link"""
		link_value = source_item.get(link_name)
		if link_value is None:
			return None
		
		if isinstance(link_field, ListOf):
			if not options.bypass_authorization:
				self.rules.enforce_non_item_rules(LIST, options.context)
			result = self.storage.get_by_ids(self.entity, link_value,
								filter=options.filter, sort=options.sort, 
								offset=options.offset, limit=options.limit,
								count=options.count)
			if options.count:
				return result
			if not options.bypass_authorization:
				self.rules.enforce_item_rules(LIST, result, options.context)
			
			if not options.sort and len(result) > 1:
				results_by_id = {}
				for r in result:
					results_by_id[r['_id']] = r
				new_result = []
				for id in link_value:
					item = results_by_id.get(id)
					if item:
						new_result.append(item)
				result = new_result
			return self.post(LIST, options, result)
		else:
			self.rules.enforce_non_item_rules(GET, options.context)
			item = self.storage.get_by_id(self.entity, link_value)
			self.rules.enforce_item_rules(GET, item, options.context)
			return self.post(GET, options, item)
			
			
	def get_linked_interface(self, link_name):
		link = None
		entities = [self.entity] + self.entity.children
		for entity in entities:
			link = entity.get_link(link_name)
			if link:
				break
		if not link:
			raise Exception, "Entity '%s' nor its children have a link called '%s'" % (self.entity.__name__, link_name)
			
		if isinstance(link, ListOf):
			linked_entity = link.field.entity
		else:
			linked_entity = link.entity
		return self.api.get_interface_for_entity(linked_entity)
		
		
	def prepare_item(self, item, options):
		self.remove_hidden_fields(item, options)
		self.add_embedded_links(item, options)
		return item
		
		
	def remove_hidden_fields(self, item, options):
		if not options.show_hidden or not options.can_show_hidden:
			for k in self.entity.hidden_fields:
				item.pop(k, None)
		if options.fields is not None:
			for k in item.keys():
				if k not in options.fields and not k.startswith('_'):
					item.pop(k, None)
			
		
	def add_embedded_links(self, item, options):
		"""Add embedded links and links to an item"""
		if not options.allow_embedding:
			return
		
		entity, embed = options.get_embed_for_type(self.entity, item.get('_type', self.entity.__name__))
		
		for link_name in embed:
			linked_interface = self.get_linked_interface(link_name)
			if not linked_interface:
				raise Exception, "No link defined in '%s' interface for embedded link '%s'" % (self.plural_name, link_name)
			
			link_field = getattr(entity, link_name)
			
			link_options = {
				'context': options.context,
				'allow_embedding': False,
				'show_hidden': options.show_hidden
			}
			
			embedded_fields = link_field.field.embedded_fields if isinstance(link_field, ListOf) else link_field.embedded_fields
			if embedded_fields:
				link_options['fields'] = embedded_fields
			
			result = linked_interface.resolve_link(item, link_name, link_field, link_options)
			
			if result:
				item[link_name] = result
				
		return item
		
		
	def post(self, method, options, result=None):
		"""Perform post-method hooks including authentication that requires fetched items."""
		if result is None:
			return
			
		if method == LIST:
			new_results = []
			for item in result:
				new_results.append(
					self.prepare_item(item, options)
				)
			options.context['item'] = result
			return new_results
		else:
			options.context['item'] = result
			return self.prepare_item(result, options)
		
		
	def disabled_method_error(self, *args, **kwargs):
		raise errors.DisabledMethodError, "This method is not enabled."
		
		