"""
Provides a friendly interface for managing 
"""

from functools import partial
from .interface import Interface
from .. import errors
from ..spec.jsonschema import to_jsonschema


class API(object):
	
	def __init__(self, model):
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
		return self.interfaces[name]
		
		
	def __getitem__(self, key):
		return self.interfaces[name]
			
			
	def schema(self, base_url):
		return to_jsonschema(self, base_url)
		
		
	def get_interface_for_entity(self, entity):
		return self.interfaces_by_entity[entity.__name__][0]
		