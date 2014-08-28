from .auth.errors import NotAuthorizedError

class ParameterException(Exception):
	pass


class Collection(object):
	"""
	A collection is a generic API for managing document instances.
	"""

	# The mongoengine.Document descendant managed by this collection
	document = None

	# The default number of objects returned at a time by list()
	default_limit = 10

	# The maximum number of objects returned at a time by list()
	max_limit = 20


	def __init__(self, identity=None):
		"""Create a new collection.

		The optional `identity` is a user-defined identity object used to control access to the 
		collection methods and modify their parameters."""
		self.identity = identity


	def list(self, filter=None, sort=None, include_fields=None, exclude_fields=None, skip=0, limit=0):
		"""Returns a list of objects, subject to filtering and limiting.

		:param :filter A mongodb query applied to the list
		:param :include_fields A list of fields to include
		:param :exclude_fields A list of fields to exclude
		:param :skip Skip this many results
		:param :limit Only return this many, subject to the `max_limit` restriction
		"""
		self._require_method_allowed('list')
		return self._list(filter, sort, include_fields, exclude_fields, skip, limit)


	def get(self, id, include_fields=None, exclude_fields=None):
		"""Get a single object.

		:param :include_fields A list of fields to include
		:param :exclude_fields A list of fields to exclude
		"""
		self._require_method_allowed('get')
		results = self._list(filter={'_id':id}, include_fields=include_fields, exclude_fields=exclude_fields)
		return results.first()


	def create(self, fields):
		"""Create a new object."""
		self._require_method_allowed('create')
		modified_fields = self.modify_update_fields(fields)
		instance = self.document(**modified_fields)
		return instance.save()


	def update(self, id, fields):
		"""Update an existing object. 

		Returns None if the specified object does not exist, otherwise it returns the updated object."""
		self._require_method_allowed('update')
		modified_fields = self.modify_update_fields(fields)
		return self.document.objects(id=id).modify(new=True, **modified_fields)


	def delete(self, id):
		"""Remove an object."""
		self._require_method_allowed('delete')
		self.document.objects(id=id).remove()


	def allowed_methods(self):
		"""Override to change which methods are allowed.

		MUST return a list or tuple containing zero or more method names. Methods that are in this list
		will be allowed. All other methods will raise `hammock.auth.NotAuthorizedException`.
		"""
		return ('list', 'get', 'create', 'update', 'delete')


	def modify_filter(self, filter):
		"""Override to change the filter for the `list()` and `get()` methods.

		:param :filter The requested filter

		MUST return a dict. Can be an empty dict."""
		return filter


	def modify_sort(self, sort):
		"""Override to change the requested sort.

		:param :sort a mongodb sort value
		"""
		return sort


	def modify_get_fields(self, include_fields, exclude_fields):
		"""Override to change which fields are included in returned objects"""
		return include_fields, exclude_fields


	def modify_update_fields(self, fields):
		"""Override to change which fields are used to create or update an object"""
		return fields


	def _require_method_allowed(self, method):
		if method not in self.allowed_methods():
			raise NotAuthorizedException


	def _list(self, filter=None, sort=None, include_fields=None, exclude_fields=None, skip=0, limit=0):
		modified_filter = self._get_modified_filter(filter)
		modified_sort = self.modify_sort(sort)
		modified_include_fields, modified_exclude_fields = self.modify_get_fields(include_fields, exclude_fields)

		results = self.document.objects(__raw__=modified_filter)
		results = self._apply_fields(results, include_fields, exclude_fields)
		results = self._apply_sort(results, sort)
		results = self._apply_limits(results, skip, limit)

		return results


	def _get_modified_filter(self, filter):
		filter = filter if filter else {}
		modified_filter = self.modify_filter(filter)

		if modified_filter is None:
			raise Exception, "%s.modify_filter() must return a dict, got None instead" % (self.__class__.__name__)
		else:
			return modified_filter


	def _apply_fields(self, queryset, include_fields, exclude_fields):
		if exclude_fields:
			for k in exclude_fields:
				queryset = queryset.exclude(k)

			if include_fields:
				exclude_fields = set(exclude_fields)
				for k in include_fields:
					if k not in exclude_fields:
						queryset = queryset.only(include_fields)
		
		elif include_fields:
			for k in include_fields:
				queryset = queryset.only(k)

		return queryset


	def _apply_limits(self, queryset, skip, limit):
		if skip > 0:
			queryset = queryset.skip(skip)

		if limit == 0:
			limit = self.default_limit

		queryset = queryset.limit(min(limit, self.max_limit))

		return queryset


	def _apply_sort(self, queryset, sort):
		sort = sort if sort else ()

		if not isinstance(sort, (list, tuple)):
			raise ParameterException, "Sort must be a list"

		for n in sort:
			if not isinstance(n, basestring):
				raise ParameterException, "Sort fields must be strings"

		sort = self.modify_sort(sort)

		if sort is not None:
			queryset = queryset.order_by(*sort)

		return queryset
