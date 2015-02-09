import re
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
from . import Storage
from .. import errors

find_dupe_index_pattern = re.compile(r'\$([a-zA-Z0-9_]+)\s+')

class MongoDBStorage(Storage):
	
	special_fields = { '$where', '$text' }
	
	def __init__(self, db=None, *args, **kwargs):
		self.client = pymongo.MongoClient(*args, **kwargs)
		self.db = self.client[db]
		self.unique_fields_by_index = {}
		
		
	def setup(self, model):
		for e in model.entities.values():
			collection = self.get_collection(e)
			for k,v in e.fields.items():
				if v.unique:
					index_name = collection.ensure_index(k, unique=True, sparse=True)
					self.unique_fields_by_index[index_name] = k
		
	
	def get(self, entity, filter=None, fields=None, sort=None, offset=0, limit=0, count=False):
		to_dict = self.document_to_dict
		if filter and '_id' in filter and isinstance(filter['_id'], basestring):
			filter['_id'] = self._objectid(filter['_id'])
		
		sort_pairs = []
		if filter and '$text' in filter:
			sort_pairs.append(('score', {'$meta':'textScore'}))
			if not fields:
				fields = {}
			fields['score'] = {'$meta':'textScore'}
		if sort:
			sort_pairs.extend([(field[1:], 1) if field[0] == '+' else (field[1:], -1) for field in sort])
		
		collection = self.get_collection(entity)
		
		type_filter = self.get_type_filter(entity)
		if type_filter:
			if not filter:
				filter = type_filter
			else:
				filter.update(type_filter)
		
		results = collection.find(spec=filter, 
								  fields=fields, 
								  sort=sort_pairs, 
								  skip=offset, 
								  limit=limit)
		
		if count:
			return results.count()
		else:
			return map(to_dict, results)
			
			
	def get_by_ids(self, entity, ids, filter=None, fields=None, sort=None, offset=0, limit=0, count=False):
		if not filter:
			filter = {}
		filter['_id'] = {'$in':map(self._objectid, ids)}
		return self.get(entity, filter=filter, fields=fields, sort=sort, offset=offset, limit=limit, count=count)
		
		
	def get_by_id(self, entity, id, filter=None, fields=None):
		collection = self.get_collection(entity)
		filter = filter if filter else {}
		filter['_id'] = self._objectid(id)
		type_filter = self.get_type_filter(entity)
		if type_filter:
			filter.update(type_filter)
		result = collection.find_one(filter, fields=fields)
		
		if result is None:
			return None
		else:
			return self.document_to_dict(result)
		
		
	def create(self, entity, fields):
		collection = self.get_collection(entity)
		type_name = self.get_type_name(entity)
		if type_name:
			fields['_type'] = type_name
		if '_id' in fields:
			fields['_id'] = self._objectid(fields['_id'])
		try:
			obj_id = collection.insert(fields.copy())
		except pymongo.errors.DuplicateKeyError, e:
			self._raise_dupe_error(e)
			
		return self._from_objectid(obj_id)
		
		
	def update(self, entity, id, fields, replace=False):
		type_name = self.get_type_name(entity)
		if type_name:
			fields['_type'] = type_name
		try:
			collection = self.get_collection(entity)
			obj_id = self._objectid(id)
			if replace:
				doc = fields
			else:
				doc = { '$set': fields }
			doc = collection.find_and_modify({ '_id': obj_id }, doc, new=True)
			if doc:
				return self.document_to_dict(doc)
		except pymongo.errors.DuplicateKeyError, e:
			self._raise_dupe_error(e)
			
			
	def delete(self, entity, id):
		collection = self.get_collection(entity)
		collection.remove(self._objectid(id))
		
		
	def document_to_dict(self, doc):
		doc['_id'] = self._from_objectid(doc['_id'])
		return doc
		
		
	def get_collection(self, entity):
		if len(entity.hierarchy) > 0:
			collection_name = entity.hierarchy[0].__name__
		else:
			collection_name = entity.__name__
			
		# We use getattr here instead of __getitem__ to
		# make it easier to inject mock collections objects
		# for testing
		return getattr(self.db, collection_name)
			
			
	def get_type_name(self, entity):
		if len(entity.hierarchy) > 0:
			return '.'.join([x.__name__ for x in entity.hierarchy]) + '.' + entity.__name__
		else:
			return None
			
			
	def get_type_filter(self, entity):
		type_name = self.get_type_name(entity)
		if type_name:
			return {'_type':{'$regex':'^%s' % re.escape(type_name)}}
			
		
	def check_filter(self, filter, allowed_fields, context):
		allowed_fields = set(allowed_fields)
		return self._check_filter(filter, allowed_fields, context)
		
		
	def _check_filter(self, filter, allowed_fields, context):
		if not isinstance(filter, dict):
			return
		for k,v in filter.items():
			
			if k.startswith('$'):
				if k in self.special_fields:
					continue
			elif k not in allowed_fields:
				raise errors.DisabledFieldError('You cannot filter by the "%s" field' % k)
			
			identity_value = self._get_identity_value(v, context)
			if identity_value:
				filter[k] = identity_value
			elif isinstance(v, (list, tuple)):
				new_v = []
				for x in v:
					identity_value = self._get_identity_value(x, context)
					if identity_value:
						new_v.append(identity_value)
					else:
						new_v.append(x)
					self._check_filter(x, allowed_fields, context)
					filter[k] = new_v
			elif isinstance(v, dict):
				self._check_filter(v, allowed_fields, context)
				
	def _get_identity_value(self, key, context):
		if isinstance(key, basestring):
			if key.startswith('$identity'):
				try:
					return reduce(dict.get, key[1:].split("."), context)
				except:
					raise errors.CompoundValidationError({'filter': 'Attempting to use a non-existent context variable: %s' % key})
				
				
	def _raise_dupe_error(self, orig_exc):
		m = find_dupe_index_pattern.search(orig_exc.message)
		if m:
			index_name = m.group(1)
			key_name = self.unique_fields_by_index.get(index_name)
		else:
			key_name = 'unknown'
		
		raise errors.DuplicateError(key_name)
			
		
	def _objectid(self, id):
		try:
			return ObjectId(id)
		except:
			return str(id)
			
	def _from_objectid(self, id):
		if isinstance(id, ObjectId):
			return str(id)
		else:
			return id