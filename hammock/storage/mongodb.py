import pymongo
from bson.objectid import ObjectId
from . import Storage


class MongoDBStorage(Storage):
	
	def __init__(self, *args, **kwargs):
		self.client = pymongo.MongoClient(*args, **kwargs)
		self.db = None
		self.resolvers = None
		
		
	def setup(self, model):
		self.db = self.client[model.name]
		
	
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
		