import pymongo
from bson.objectid import ObjectId
from . import Storage


class MongoDBStorage(Storage):
	
	def __init__(self, db=None, *args, **kwargs):
		self.client = pymongo.MongoClient(*args, **kwargs)
		self.db = self.client[db]
		
	
	def get(self, entity, filter=None, fields=None, sort=None, offset=0, limit=0):
		if sort is not None:
			sort = [(field[1:], 1) if field[0] == '+' else (field[1:], -1) for field in sort]
		
		if filter and 'id' in filter:
			filter['_id'] = ObjectId(filter['id'])
			del filter['id']
		
		collection = self.collection_for_entity(entity)
		results = collection.find(spec=filter, 
								  fields=fields, 
								  sort=sort, 
								  skip=offset, 
								  limit=limit)
			
		for result in results:
			yield self.document_to_dict(result)
			
			
	def get_by_ids(self, entity, ids, filter=None, fields=None, sort=None, offset=0, limit=0):
		if not filter:
			filter = {}
		filter['_id'] = {'$in':map(ObjectId, ids)}
		return self.get(entity, filter=filter, fields=fields, sort=sort, offset=offset, limit=limit)
		
		
	def create(self, entity, fields):
		collection = self.collection_for_entity(entity)
		obj_id = collection.insert(fields.copy())
		return str(obj_id)
		
		
	def update(self, entity, id, fields, replace=False):
		collection = self.collection_for_entity(entity)
		obj_id = ObjectId(id)
		if replace:
			doc = fields.copy()
			doc['_id'] = obj_id
			collection.save(doc)
		else:
			doc = collection.find_and_modify({ '_id': obj_id }, { '$set': fields }, new=True)
			if not doc:
				return None
		return self.document_to_dict(doc)
		
		
	def delete(self, entity, id):
		collection = self.collection_for_entity(entity)
		obj_id = ObjectId(id)
		collection.remove(obj_id)
		
		
	def document_to_dict(self, doc):
		doc['id'] = str(doc['_id'])
		del doc['_id']
		return doc
		
		
	def collection_for_entity(self, entity):
		return self.db[entity.__name__]
		
		
	def clean_filter(self, filter, allowed_fields):
		allowed_fields = set(allowed_fields)
		return self._clean_filter(filter, allowed_fields)
		
	def _clean_filter(self, filter, allowed_fields):
		new_filter = {}
		for k,v in filter.items():
			
			if k.startswith('$'):
				if k == '$where':
					continue
			elif k not in allowed_fields:
				continue
				
			if isinstance(v, (list, tuple)):
				new_v = []
				for x in v:
					new_x = self._clean_filter(x, allowed_fields)
					if new_x is not None and new_x != []:
						new_v.append(new_x)
			elif isinstance(v, dict):
				new_v = self._clean_filter(v, allowed_fields)
			else:
				new_v = v
			
			if new_v is not None and new_v != [] and new_v != {}:
				new_filter[k] = new_v
		
		if new_filter == {}:
			return None
		else:
			return new_filter
				
				