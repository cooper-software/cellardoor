from .methods import ALL, LIST, CREATE, GET, REPLACE, UPDATE, DELETE
from .model import CompoundValidationError, ListOf, Reference, Link
from . import errors

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
	
	# A list or tuple of `hammock.methods` that are enabled through this collection.
	#
	# Note that just because a method is enabled, does not mean it will be available
	# to any request. Methods are subject to authorization rules.
	enabled_methods = ()
	
	# A list or tuple of fields that are allowed to be used in filters.
	enabled_filters = ()
	
	# A list or tuple of fields that can be used in sorting.
	enabled_sort = ()
	
	# A list or tuple of fields that is a subset of `enabled_sort` that will be
	# used to sort results when no sort is supplied in the request.
	default_sort = ()
	
	# A list or tuple of authorization rules. An authorization rule is a 2-tuple. The first item is a tuple
	# of `hammock.methods` that the rule applies to. The second item is a `hammock.auth.AuthenticationExpression`.
	method_authorization = ()
	
	# A `hammock.auth.AuthenticationExpression` that must be met for hidden fields to be shown.
	hidden_field_authorization = ()
	
	
	def __init__(self, storage):
		self.storage = storage
		self.authorization = {}
		self.entity = self.entity()
		
		enabled_methods = set(self.enabled_methods)
		for method in ALL:
			if method not in enabled_methods:
				setattr(self, method, self.disabled_method_error)
		
		for methods, rule in self.method_authorization:
			for method in methods:
				if method not in self.authorization:
					self.authorization[method] = []
				self.authorization[method].append(rule)
		
		if self.hidden_field_authorization:
			assert not self.hidden_field_authorization.uses('item'), \
				"Hidden field authorization rules must not use `auth.item`"
			self.authorization['allow_hidden'] = [self.hidden_field_authorization]
			
			
	def list(self, filter=None, sort=None, offset=0, limit=0, show_hidden=False, context={}):
		self.pre(LIST, context)
		sort = sort if sort else self.default_sort
		self.check_for_disabled_fields(filter, sort, context)
		items = self.storage.get(self.entity.__class__, filter=filter, sort=sort, offset=offset, limit=limit)
		return self.post(LIST, items, context, show_hidden=show_hidden)
		
		
	def create(self, fields, show_hidden=False, context={}):
		self.pre(CREATE, context)
		self.entity.hooks.trigger_pre('create', fields)
		item = self.entity.validator.validate(fields)
		item['_id'] = self.storage.create(self.entity.__class__, item)
		item = self.post(CREATE, item, context, show_hidden=show_hidden)
		self.entity.hooks.trigger_post('create', item)
		return item
		
		
	def get(self, id, show_hidden=False, context=None):
		self.pre(GET, context)
		item = self.storage.get_by_id(self.entity.__class__, id)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		else:
			return self.post(GET, item, context, show_hidden=show_hidden)
		
		
	def update(self, id, fields, show_hidden=False, context=None):
		self.pre(UPDATE, context)
		self.entity.hooks.trigger_pre('update', id, fields, replace=False)
		fields = self.entity.validator.validate(fields, enforce_required=False)
		item = self.storage.update(self.entity.__class__, id, fields)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		item = self.post(UPDATE, item, context, show_hidden=show_hidden)
		self.entity.hooks.trigger_post('update', item)
		return item
		
		
	def replace(self, id, fields, show_hidden=False, context=None):
		self.pre(REPLACE, context)
		self.entity.hooks.trigger_pre('update', id, fields, replace=True)
		fields = self.entity.validator.validate(fields)
		item = self.storage.update(self.entity.__class__, id, fields, replace=True)
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		item = self.post(REPLACE, item, context, show_hidden=show_hidden)
		self.entity.hooks.trigger_post('update', item)
		return item
		
		
	def delete(self, id, context=None):
		self.pre(DELETE, context)
		self.entity.hooks.trigger_pre('delete', id)
		self.storage.delete(self.entity.__class__, id)
		self.post(DELETE, None, context)
		self.entity.hooks.trigger_post('delete', id)
		
		
	def link(self, id, reference_name, filter=None, sort=None, offset=0, limit=0, show_hidden=False, context=None):
		self.pre(GET, context)
		
		item = self.storage.get_by_id(self.entity.__class__, id)
		
		if item is None:
			raise errors.NotFoundError("No %s with id '%s' was found" % (self.singular_name, id))
		
		self.post(GET, item, context)
			
		target_collection = self.links.get(reference_name)
		
		if target_collection is None:
			raise errors.NotFoundError("The %s collection has no link '%s' defined" % (self.plural_name, reference_name))
		
		reference_field = getattr(self.entity.__class__, reference_name)
		
		return target_collection.resolve_link_or_reference(item, reference_name, reference_field,
						filter=filter, sort=sort, offset=offset, limit=limit, show_hidden=show_hidden, context=context)
		
		
	def resolve_link_or_reference(self, source_item, reference_name, reference_field, filter=None, sort=None, 
								  offset=0, limit=0, show_hidden=False, context=None):
		"""Get the item(s) pointed to by a link or reference"""
		sort = sort if sort else self.default_sort
		self.check_for_disabled_fields(filter, sort, context)
		if isinstance(reference_field, Link):
			return self.resolve_link(source_item, reference_field, filter=filter, sort=sort, offset=offset, 
				                     limit=limit, show_hidden=show_hidden, context=context)
		else:
			return self.resolve_reference(source_item, reference_name, reference_field,
							filter=filter, sort=sort, offset=offset, limit=limit, context=context)
		
		
	def resolve_link(self, source_item, link_field, filter=None, sort=None, offset=0, 
				     limit=0, show_hidden=False, context=None):
		"""
		Get the items for a single or multiple link
		"""
		filter = filter if filter else {}
		filter[link_field.field] = source_item['_id']
		
		if link_field.multiple:
			self.pre(LIST, context)
			items = list(self.storage.get(self.entity.__class__, filter=filter, sort=sort, offset=offset, limit=limit))
			return self.post(LIST, items, context, embed=False, show_hidden=show_hidden)
		else:
			try:
				self.pre(GET, context)
				item = next(iter(self.storage.get(self.entity.__class__, filter=filter, limit=1)))
				return self.post(GET, item, context, embed=False, show_hidden=show_hidden)
			except StopIteration:
				pass
		
	
	def resolve_reference(self, source_item, reference_name, reference_field, filter=None, sort=None, 
						  offset=0, limit=0, show_hidden=False, context=None):
		"""Get the items for a single or multiple reference"""
		reference_value = source_item.get(reference_name)
		
		if reference_value is None:
			return None
		
		if isinstance(reference_field, ListOf):
			self.pre(LIST, context)
			items = list(self.storage.get_by_ids(self.entity.__class__, reference_value,
						filter=filter, sort=sort, offset=offset, limit=limit))
			return self.post(LIST, items, context, embed=False, show_hidden=show_hidden)
		else:
			self.pre(GET, context)
			item = self.storage.get_by_id(self.entity.__class__, reference_value)
			return self.post(GET, item, context, embed=False, show_hidden=show_hidden)
			
			
	def check_for_disabled_fields(self, filter, sort, context):
		can_show_hidden = self.can_show_hidden(context)
		self.check_filter(filter, can_show_hidden)
		self.check_sort(sort, can_show_hidden)
			
			
	def check_filter(self, filter, can_show_hidden):
		if filter is None:
			return None
		if not self.enabled_filters:
			raise CompoundValidationError({'filter':'Filtering is disabled.'})
		allowed_fields = set(self.enabled_filters)
		if not can_show_hidden:
			allowed_fields.difference_update(self.entity.hidden_fields)
		try:
			self.storage.check_filter(filter, allowed_fields)
		except errors.DisabledFieldError, e:
			raise CompoundValidationError({'filter':'The "%s" field cannot be used as a filter.' % e.message})
		return filter
		
		
	def check_sort(self, sort, can_show_hidden):
		if not sort:
			return None
		if not self.enabled_sort:
			raise CompoundValidationError({'sort':'Sorting is disabled.'})
		allowed_fields = set(self.enabled_sort)
		if not can_show_hidden:
			allowed_fields.difference_update(self.entity.hidden_fields)
		for k in sort:
			field_name = k[1:]
			if field_name not in allowed_fields:
				raise CompoundValidationError({'sort':'The "%s" field cannot be used for sorting.' % field_name})
			
			
	def can_show_hidden(self, context):
		hidden_auth_rules = self.authorization.get('allow_hidden')
		if hidden_auth_rules:
			does_not_have_identity = 'identity' not in context
			for rule in hidden_auth_rules:
				if rule.uses('identity') and does_not_have_identity:
					return False
				elif not rule(context):
					return False
		return True
		
		
	def prepare_items(self, items, embed=True, show_hidden=False):
		"""Do post-processing on items.
		
		For example, adding embedded references, removing hidden fields, etc.
		
		:param items: A list of items or a single item to prepare.
		:returns: A list of prepared items or a single prepared item.
		"""
		prepared_items = []
		for item in items:
			prepared_items.append(self.prepare_item(item, embed=embed, show_hidden=False))
		return prepared_items
		
		
	def prepare_item(self, item, embed=True, show_hidden=False):
		if not show_hidden:
			pass
		if embed:
			self.add_embedded_references(item)
		if not show_hidden:
			for k in self.entity.hidden_fields:
				item.pop(k, None)
		return item
		
		
	def add_embedded_references(self, item, show_hidden=False, context=None):
		"""Add embedded references and links to an item"""
		for reference_name, reference_field in self.entity.links_and_references:
			if not reference_field.embedded:
				continue
				
			if not show_hidden and reference_field.hidden:
				continue
				
			referenced_collection = self.links.get(reference_name)
			if not referenced_collection:
				raise Exception, "No link defined in '%s' collection for embedded reference '%s'" % (self.plural_name, reference_name)
				
			result = referenced_collection.resolve_link_or_reference(item, reference_name, getattr(self.entity.__class__, reference_name), context=context)
			
			if result:
				item[reference_name] = result
				
		return item
		
		
	def pre(self, method, context):
		"""Perform pre-method hooks, including authorization that does not require access to fetched items."""
		context = context if context else {}
		auth_rules = self.authorization.get(method)
		does_not_have_identity = 'identity' not in context
		if auth_rules:
			for rule in auth_rules:
				if not rule.uses('result'):
					if rule.uses('identity') and does_not_have_identity:
						raise errors.NotAuthenticatedError()
					elif not rule(context):
						raise errors.NotAuthorizedError()
		
		
	def post(self, method, result, context, embed=True, show_hidden=False):
		"""Perform post-method hooks including authentication that requires fetched items."""
		context = context if context else {}
		auth_rules = self.authorization.get(method)
		does_not_have_identity = 'identity' not in context
		context['result'] = result
		if auth_rules:
			for rule in auth_rules:
				if rule.uses('identity') and does_not_have_identity:
					raise errors.NotAuthenticatedError()
				elif not rule(context):
					raise errors.NotAuthorizedError()
						
		if result is None:
			return
			
		show_hidden = self.can_show_hidden(context) and show_hidden
		
		if method == LIST:
			result = self.prepare_items(result, embed=embed, show_hidden=show_hidden)
		else:
			result = self.prepare_item(result, embed=embed, show_hidden=show_hidden)
		return result
		
		
	def disabled_method_error(self, *args, **kwargs):
		raise errors.DisabledMethodError, "This method is not enabled."
		