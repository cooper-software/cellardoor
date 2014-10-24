cellardoor
==========

Create CRUD APIs like you've always wanted.

**cellardoor** is a framework that generates CRUD services. It aims to make this task less soul-crushingly repetitive while still providing clear, simple ways for the developer to integrate all the non-CRUDy parts of her or his API. In a nutshell, you declare your data model and how it should be accessed and **cellardoor** generates nice APIs for you.

Some features of **cellardoor**

* **Declarative everything:** entities, operations, authorization, data validation
* **Pluggable everything:** storage, serializers, authentication, protocols
* A simple but powerful system of **hooks**
* Generate **JSON schema** from your API

A taste
~~~~~~~

This is to give you a basic idea of what working with cellardoor looks like. For more detailed examples checkout the :doc:`quickstart` and :doc:`tutorial`.

1. Define your model
#################

.. code-block:: python
	
	from cellardoor.model import *
	
	class Todo(Entity):
		title = Text()
		is_done = Boolean()
		
		
2. Create authorization rules
#############################

.. code-block:: python
	
	from cellardoor.collection import Collection
	from cellardoor.methods import ALL
	
	class Todos(Collection):
		entity = Todo
		method_authorization = {
			ALL: None
		}
		enabled_filters = ('title','is_done')
		enabled_sort = ('title','is_done')
		
		

3. Decide how to store data 
###########################

.. code-block:: python
	
	from cellardoor import CellarDoor
	from cellardoor.storage.mongodb import MongoDBStorage
	
	api = CellarDoor(
		storage=MongoDBStorage('todo'), 
		collections=(Todos,)
	)
	
	
4. Profit
#########

Everyone gets a nice, pythonic API

.. code-block:: python
	
	> item = api.todos.create({'title':'Write more documentation', 'is_done': False})
	> print item['title']
	'Write more documentation'
	
	> list(api.todos.find({'is_done':False}).limit(1))
	[{
		'_id':'54493977b4dabb82679efbd6',
		'title': 'Write more documentation',
		'is_done': False
	}]
	
	> item['is_done'] = True
	> api.todos.save(item)
	> list(api.todos.find({'is_done':False}).limit(1))
	[]
	
If you need it, create a ReST API

.. code-block:: python
	
	import falcon
	from cellardoor.falcon import add_to_falcon
	
	app = falcon.API()
	add_to_falcon(app, api)


Need more? Flask? SQLAlchemy? Protocol Buffers? We're working on other storage backends and protocols and you can also :doc:`get involved <development>`.

Documentation
~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2
   
   quickstart
   tutorial
   userguide
   api
   development
   
