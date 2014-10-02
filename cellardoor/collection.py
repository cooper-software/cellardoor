from copy import deepcopy
from .methods import ALL, LIST, CREATE, GET, REPLACE, UPDATE, DELETE
from .model import ListOf, Reference, Link
from .events import EventManager
from . import errors


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
			if isinstance(item, list):
				for i in item:
					self.enforce_rules(rules, i, context)
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
		
		
	def create(self, options_dict, list=False):
		if list:
			return ListOptions( self.process_list(options_dict) )
		else:
			return BaseOptions( self.process(options_dict) )
			
	
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
		new_options['limit'] = min(new_options['limit'] if new_options['limit'] else self.default_limit, self.max_limit)
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
		
		
	def __deepcopy__(self, memo):
		options = BaseOptions(deepcopy(self._options, memo))
		options._embed_by_class = deepcopy(self._embed_by_class, memo)
		
		
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


class CollectionMeta(type):
	
	def __new__(cls, name, bases, attrs):
		singular_name = attrs.get('singular_name')
		plural_name = attrs.get('plural_name')
		entity = attrs.get('entity')
		if entity:
			entity_name = entity.__name__.lower()
		else:
			entity_name = 'unknown'
		
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
				
		
		attrs['singular_name'] = singular_name
		attrs['plural_name'] = plural_name
		
		hidden_field_authorization = attrs.get('hidden_field_authorization')
		if hidden_field_authorization and hidden_field_authorization.uses('item'):
			raise Exception, "Hidden field authorization cannot use `authorization.item`"
		
		return super(CollectionMeta, cls).__new__(cls, name, bases, attrs)


class Collection(object):
	"""
	A collection exposes an entity through HTTP
	"""
	
	__metaclass__ = CollectionMeta
	
	# The entity class that will be exposed through this collection.
	entity = None
	
	# Collections that should be used to expose the entity's references and links.
	#
	# This is a dictionary where the keys are the name of a reference 
	# field on the entity and the values are a collection or the name 
	# of a collection.
	links = None
	
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
	
	
	def __init__(self, storage):
		self.storage = storage
		self.entity = self.entity()
		self.hooks = EventManager('create', 'update', 'delete')
		self.rules = RuleSet(self.method_authorization)
		
		hidden_fields = set(self.entity.hidden_fields.copy())
		for c in self.entity.children:
			hidden_fields.update(c.hidden_fields)
		
		self.options_factory = OptionsFactory(
			storage=self.storage,
		    hidden_fields=hidden_fields, 
		    hidden_field_authorization=self.hidden_field_authorization,
		    enabled_filters=self.enabled_filters,
		    enabled_sort=self.enabled_sort,
		    default_sort=self.default_sort,
		    default_limit=self.default_limit,
		    max_limit=self.max_limit
		)
		
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
		
		result = self.storage.get(self.entity.__class__, 
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
		
		self.entity.hooks.trigger_pre('create', fields, options.context)
		self.hooks.trigger_pre('create', fields, options.context)
		
		item = self.entity.validator.validate(fields)
		item['_id'] = self.storage.create(self.entity.__class__, item)
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(CREATE, item, options.context)
		
		item = self.post(CREATE, options, item)
		
		self.entity.hooks.trigger_post('create', item, options.context)
		self.hooks.trigger_post('create', item, options.context)
		
		return item
		
		
	def get(self, id, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(GET, options.context)
		
		item = self.storage.get_by_id(self.entity.__class__, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(GET, item, options.context)
		
		return self.post(GET, options, item)
		
		
	def update(self, id, fields, _replace=False, _method=UPDATE, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(_method, options.context)
		
		self.entity.hooks.trigger_pre('update', id, fields, options.context)
		self.hooks.trigger_pre('update', id, fields, options.context)
		
		if not options.bypass_authorization and UPDATE in self.rules.item_rules:
			item = self.storage.get_by_id(self.entity.__class__, id)
			if item is None:
				raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
			self.rules.enforce_item_rules(_method, item, options.context)
		
		version = fields.pop('_version', None)
		fields = self.entity.validator.validate(fields, enforce_required=_replace)
		if version:
			fields['_version'] = version
		item = self.storage.update(self.entity.__class__, id, fields, replace=_replace)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		item = self.post(_method, options, item)
		
		self.entity.hooks.trigger_post('update', item, options.context)
		self.hooks.trigger_post('update', item, options.context)
		
		return item
		
		
	def replace(self, id, fields, **kwargs):
		return self.update(id, fields, _replace=True, _method=REPLACE, **kwargs)
		
		
	def delete(self, id, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(DELETE, options.context)
		
		item = self.storage.get_by_id(self.entity.__class__, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(DELETE, item, options.context)
		
		self.entity.hooks.trigger_pre('delete', id, options.context)
		self.hooks.trigger_pre('delete', id, options.context)
		
		self.storage.delete(self.entity.__class__, id)
		self.post(DELETE, options)
		
		options.context['item'] = item
		self.entity.hooks.trigger_post('delete', id, options.context)
		self.hooks.trigger_post('delete', id, options.context)
		
		
	def link(self, id, reference_name, **kwargs):
		options = self.options_factory.create(kwargs)
		
		if not options.bypass_authorization:
			self.rules.enforce_non_item_rules(GET, options.context)
		
		item = self.storage.get_by_id(self.entity.__class__, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		if not options.bypass_authorization:
			self.rules.enforce_item_rules(GET, item, options.context)
			
		target_collection = self.links.get(reference_name)
		if target_collection is None:
			raise errors.NotFoundError("The %s collection has no link '%s' defined" % (self.plural_name, reference_name))
		reference_field = getattr(self.entity.__class__, reference_name)
		
		return target_collection.resolve_link_or_reference(item, reference_name, reference_field, kwargs)
		
		
	def resolve_link_or_reference(self, source_item, reference_name, reference_field, options):
		"""Get the item(s) pointed to by a link or reference"""
		options = self.options_factory.create(options, list=True)
		
		if isinstance(reference_field, Link):
			return self.resolve_link(source_item, reference_field, options)
		else:
			return self.resolve_reference(source_item, reference_name, reference_field, options)
		
		
	def resolve_link(self, source_item, link_field, options):
		"""
		Get the items for a single or multiple link
		"""
		options.filter = options.filter if options.filter else {}
		options.filter[link_field.field] = source_item['_id']
		
		if link_field.multiple:
			self.rules.enforce_non_item_rules(LIST, options.context)
			result = self.storage.get(self.entity.__class__, 
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
				item = next(iter(self.storage.get(self.entity.__class__, filter=options.filter, limit=1)))
				if not options.bypass_authorization:
					self.rules.enforce_item_rules(GET, item, options.context)
				return self.post(GET, options, item)
			except StopIteration:
				pass
		
	
	def resolve_reference(self, source_item, reference_name, reference_field, options):
		"""Get the items for a single or multiple reference"""
		reference_value = source_item.get(reference_name)
		if reference_value is None:
			return None
		
		if isinstance(reference_field, ListOf):
			if not options.bypass_authorization:
				self.rules.enforce_non_item_rules(LIST, options.context)
			result = self.storage.get_by_ids(self.entity.__class__, reference_value,
								filter=options.filter, sort=options.sort, 
								offset=options.offset, limit=options.limit,
								count=options.count)
			if options.count:
				return result
			if not options.bypass_authorization:
				self.rules.enforce_item_rules(LIST, result, options.context)
			return self.post(LIST, options, result)
		else:
			self.rules.enforce_non_item_rules(GET, options.context)
			item = self.storage.get_by_id(self.entity.__class__, reference_value)
			self.rules.enforce_item_rules(GET, item, options.context)
			return self.post(GET, options, item)
		
		
	def prepare_item(self, item, options):
		self.remove_hidden_fields(item, options)
		self.add_embedded_references(item, options)
		return item
		
		
	def remove_hidden_fields(self, item, options):
		if not options.show_hidden or not options.can_show_hidden:
			for k in self.entity.hidden_fields:
				item.pop(k, None)
		if options.fields is not None:
			for k in item.keys():
				if k not in options.fields and not k.startswith('_'):
					item.pop(k, None)
			
		
	def add_embedded_references(self, item, options):
		"""Add embedded references and links to an item"""
		if not options.allow_embedding:
			return
		
		entity, embed = options.get_embed_for_type(self.entity.__class__, item.get('_type', self.entity.__class__.__name__))
		
		for reference_name in embed:
			referenced_collection = self.links.get(reference_name)
			if not referenced_collection:
				raise Exception, "No link defined in '%s' collection for embedded reference '%s'" % (self.plural_name, reference_name)
			
			reference_field = getattr(entity, reference_name)
			
			link_options = {
				'context': options.context,
				'allow_embedding': False,
				'show_hidden': options.show_hidden
			}
			
			embedded_fields = reference_field.field.embedded_fields if isinstance(reference_field, ListOf) else reference_field.embedded_fields
			if embedded_fields:
				link_options['fields'] = embedded_fields
			
			result = referenced_collection.resolve_link_or_reference(item, reference_name, reference_field, link_options)
			
			if result:
				item[reference_name] = result
				
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
		