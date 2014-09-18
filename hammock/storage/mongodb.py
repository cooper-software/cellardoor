import re
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
from . import Storage
from .. import errors


class MongoDBStorage(Storage):
	
	def __init__(self, db=None, *args, **kwargs):
		self.client = pymongo.MongoClient(*args, **kwargs)
		self.db = self.client[db]
		
	
	def get(self, entity, filter=None, fields=None, sort=None, offset=0, limit=0, versions=False):
		if versions:
			if not entity.versioned:
				return
			to_dict = self.versioned_document_to_dict
			if filter:
				if '_id' in filter:
					if isinstance(filter['_id'], basestring):
						filter['_id'] = ObjectId(filter['_id'])
					filter['_id._id'] = filter['_id']
					del filter['_id']
				if '_version' in filter:
					filter['_id._version'] = filter['_version']
					del filter['_version']
		else:
			to_dict = self.document_to_dict
			if filter and '_id' in filter and isinstance(filter['_id'], basestring):
				filter['_id'] = ObjectId(filter['_id'])
				
		if sort is not None:
			sort = [(field[1:], 1) if field[0] == '+' else (field[1:], -1) for field in sort]
		
		collection = self.get_collection(entity, shadow=versions)
		
		type_filter = self.get_type_filter(entity)
		if type_filter:
			if not filter:
				filter = type_filter
			else:
				filter.update(type_filter)
			
		results = collection.find(spec=filter, 
								  fields=fields, 
								  sort=sort, 
								  skip=offset, 
								  limit=limit)
			
		for result in results:
			yield to_dict(result)
			
			
	def get_by_ids(self, entity, ids, filter=None, fields=None, sort=None, offset=0, limit=0, versions=False):
		if versions and not entity.versioned:
			return []
			
		if not filter:
			filter = {}
		filter['_id'] = {'$in':map(ObjectId, ids)}
		return self.get(entity, filter=filter, fields=fields, sort=sort, offset=offset, limit=limit, versions=versions)
		
		
	def get_by_id(self, entity, id, fields=None):
		collection = self.get_collection(entity)
		filter = {'_id':ObjectId(id)}
		type_filter = self.get_type_filter(entity)
		if type_filter:
			filter.update(type_filter)
		result = collection.find_one(filter)
		
		if result is None:
			return None
		else:
			return self.document_to_dict(result)
		
		
	def create(self, entity, fields):
		if entity.versioned:
			fields['_version'] = 1
		collection = self.get_collection(entity)
		type_name = self.get_type_name(entity)
		if type_name:
			fields['_type'] = type_name
		obj_id = collection.insert(fields.copy())
		return str(obj_id)
		
		
	def update(self, entity, id, fields, replace=False):
		type_name = self.get_type_name(entity)
		if type_name:
			fields['_type'] = type_name
		if entity.versioned:
			return self._versioned_update(entity, id, fields, replace=replace)
		else:
			return self._unversioned_update(entity, id, fields, replace=replace)
			
			
	def _versioned_update(self, entity, id, fields, replace=None):
		if '_version' not in fields:
			raise errors.CompoundValidationError({'_version': 'This field is required.'})
		current_version = fields.pop('_version')
		collection = self.get_collection(entity)
		shadow_collection = self.get_collection(entity, shadow=True)
		obj_id = ObjectId(id)
		current_doc = collection.find_one(obj_id)
		
		if not current_doc and not replace:
			return None
				
		if current_doc['_version'] != current_version:
			raise errors.VersionConflictError(
				self.document_to_dict(current_doc)
			)
		
		current_doc['_id'] = {'_id':obj_id, '_version':current_version}
		shadow_collection.insert(current_doc)
		
		fields['_version'] = current_version + 1
		if replace:
			doc = fields
		else:
			doc = { '$set': fields }
		doc = collection.find_and_modify({'_id':obj_id, '_version':current_version}, doc, new=True)
		if doc:
			return self.document_to_dict(doc)
		else:
			current_doc = collection.find_one(obj_id)
			raise errors.VersionConflictError(self.document_to_dict(current_doc))
			
		
	def _unversioned_update(self, entity, id, fields, replace=None):
		collection = self.get_collection(entity)
		obj_id = ObjectId(id)
		if replace:
			doc = fields
		else:
			doc = { '$set': fields }
		doc = collection.find_and_modify({ '_id': obj_id }, doc, new=True)
		if doc:
			return self.document_to_dict(doc)
		
		
	def delete(self, entity, id, deleted_by=None):
		if entity.versioned:
			return self._versioned_delete(entity, id, deleted_by)
		else:
			return self._unversioned_delete(entity, id)
		
		
	def _versioned_delete(self, entity, id, deleted_by):
		collection = self.get_collection(entity)
		shadow_collection = self.get_collection(entity, shadow=True)
		obj_id = ObjectId(id)
		current_doc = collection.find_one(obj_id)
		current_doc['_id'] = {'_id':current_doc['_id'], '_version':current_doc['_version']}
		shadow_collection.insert(current_doc)
		new_version = current_doc['_version'] + 1
		delete_doc = {
			'_id':{'_id':current_doc['_id']['_id'], '_version':new_version}, 
			'_deleted_on':datetime.utcnow(),
			'_version':current_doc['_version'] + 1
		}
		if deleted_by:
			delete_doc['_deleted_by'] = deleted_by
		shadow_collection.insert(delete_doc)
		collection.remove(obj_id)
		
		
	def _unversioned_delete(self, entity, id):
		collection = self.get_collection(entity)
		obj_id = ObjectId(id)
		collection.remove(obj_id)
		
		
	def document_to_dict(self, doc):
		doc['_id'] = str(doc['_id'])
		return doc
		
		
	def versioned_document_to_dict(self, doc):
		doc['_id'] = str(doc['_id']['_id'])
		return doc
		
		
	def get_collection(self, entity, shadow=False):
		if len(entity.hierarchy) > 1:
			collection_name = entity.hierarchy[0].__name__
		else:
			collection_name = entity.__name__
			
		if shadow:
			return self.db[collection_name+'.vermongo']
		else:
			return self.db[collection_name]
			
			
	def get_type_name(self, entity):
		if len(entity.hierarchy) > 1:
			return '.'.join([x.__name__ for x in entity.hierarchy])
		else:
			return None
			
			
	def get_type_filter(self, entity):
		type_name = self.get_type_name(entity)
		if type_name:
			return {'_type':{'$regex':'^%s' % re.escape(type_name)}}
			
		
	def check_filter(self, filter, allowed_fields):
		allowed_fields = set(allowed_fields)
		return self._check_filter(filter, allowed_fields)
		
		
	def _check_filter(self, filter, allowed_fields):
		if not isinstance(filter, dict):
			return
		for k,v in filter.items():
			
			if k.startswith('$'):
				if k == '$where':
					continue
			elif k not in allowed_fields:
				raise errors.DisabledFieldError('You cannot filter by the "%s" field' % k)
				
			if isinstance(v, (list, tuple)):
				for x in v:
					self._check_filter(x, allowed_fields)
			elif isinstance(v, dict):
				self._check_filter(v, allowed_fields)
				