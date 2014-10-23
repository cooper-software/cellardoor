Quick Start
===========

This short guide is here to help you get some of the **cellardoor** flavor. We'll be creating an API for the boring but obligatory and illustrative todo list application. Follow along to see how quickly you can get up and running. If this looks like something you want to invest a little more time in, have a look at the :doc:`tutorial` and :doc:`userguide`.

Install
+++++++

This quickstart assumes you have `MongoDB <http://www.mongodb.com>`_ installed, though it doesn't assume you know how to use it. You'll also need python 2.7, and pip.

We'll install **cellardoor** with MongoDB support and `httpie <https://github.com/jakubroztocil/httpie>`_ so we can play around with our API from the command line.

.. code-block:: bash
	
	$ pip install cellardoor[mongo]
	$ pip install httpie
	
	
Define the Model
++++++++++++++++

In **cellardoor**, we usually start by defining our data model. It's similar to ORM systems like in Django or SQLAlchemy or document mappers like MongoEngine, but it's designed to be independent of any particular storage system.

Let's create a ``todo-api.py`` file and in it we'll put this:

.. code-block:: python

	from cellardoor.model import *
	
	class Task(Entity):
		title = Text(maxlength=100, required=True)
		description = Text(maxlength=1000)
		is_done = Boolean(default=False)
		
	class List(Entity):
		title = Text(maxlength=100, required=True)
		tasks = ListOf(Reference(Task, embeddable=True))
		
		
That's it for our data model. We have tasks that each have a title, description and a flag telling us whether or not the task is done and we have named lists of tasks to help us group tasks together. Next we'll specify how we want users of our API to be able to access these things.

Create the collections
++++++++++++++++++++++

Entities don't have any operations in **cellardoor**. In order to be able to create, modify and search for lists and tasks, we need to create a couple of collections. Collections manage access to the instances of entities, in our case, the individual lists and tasks. In the same way that entities are not tied to any particular database or storage system, collections are independnet of any protocol. They don't speak WSGI or HTTP. They are regular python objects.

Let's update ``todo-api.py`` and create two collections, one for lists and one for tasks.

.. code-block:: python
	
	from cellardoor.collection import Collection
	from cellardoor.methods import LIST, GET, CREATE, UPDATE, DELETE, ALL
	
	class Tasks(Collection):
		entity = Task
		method_authorization = {
			ALL: None
		}
		
	class Lists(Collection):
		entity = List
		method_authorization = {
			ALL: None
		}


For completely open access, that's all we need. Through these collections, anyone will be able to find, create, modify and delete lists and tasks. Let's try it!

Run the app
+++++++++++

Now that we've defined our data model and operations we need to put everything together with some storage and a WSGI layer to make it real. As mentioned in the beginning, we'll use MongoDB for storage and to create a WSGI app, we'll use `Falcon <http://falconframework.org/>`_. Here is what the complete file should look like:

.. code-block:: python
	
	# Puts everything together
	from cellardoor import CellarDoor
	
	# Provides our data modeling objects
	from cellardoor.model import *
	
	# Provides our operation modeling classes
	from cellardoor.collection import Collection
	from cellardoor.methods import ALL
	
	# Data storage
	from cellardoor.storage.mongodb import MongoDBStorage
	
	# Adds our API to a Falcon app
	from cellardoor.falcon import add_to_falcon
	
	
	class Task(Entity):
		title = Text(maxlength=100, required=True)
		description = Text(maxlength=1000)
		is_done = Boolean(default=False)
		
	class List(Entity):
		title = Text(maxlength=100, required=True)
		tasks = ListOf(Reference(Task, embeddable=True))
	
	
	class Tasks(Collection):
		entity = Task
		method_authorization = {
			ALL: None
		}
		
	class Lists(Collection):
		entity = List
		method_authorization = {
			ALL: None
		}
		
	api = CellarDoor(storage=MongoDBStorage('todo'), collections=(Tasks, Lists))
	app = falcon.API()
	add_to_falcon(app, api)
	
	if __name__ == "__main__":
		from wsgiref.simple_server import make_server
		server = make_server('', 8000, app)
		server.serve_forever()