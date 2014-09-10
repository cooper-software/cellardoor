Hammock
=======

|Build Status| |Coverage Status|

Hammock generates a `falcon API <http://falconframework.org/>`_ from a declarative data model. It aims for DRY, performance and flexibility.

Example
~~~~~~~

.. code:: python

	from hammock import create_api
	from hammock.storage.mongodb import MongoDBStorage
	from hammock.model import Model, Reference, Link, ListOf, Text, DateTime, Boolean
	from hammock.resource import Resource
	from hammock.methods import ALL
	from hammock.views import MinimalView, SirenView
	
	storage = MongoDBStorage()

	class Project(Model):
		name = Text(maxlength=50, required=True)
		tasks = Link('Task', field='project')
		
		
	class Task(Model):
		summary = Text(maxlength=150, required=True)
		due = DateTime()
		is_done = Boolean(default=False)
		project = Reference(Project, embeddable=True, storage=storage)
		
		
	class ProjectsResource(Resource):
		model = Project
		model_links = {
			'tasks': 'TasksResource'
		}
		enabled_methods = ALL
		enabled_filters = ('name',)
		enabled_sort = ('name',)
		default_sort = ('+name',)
		
		
	class TasksResource(Resource):
		model = Task
		model_links = {
			'project': 'ProjectsResource'
		}
		enabled_methods = ALL,
		enabled_filters = ('name', 'due', 'is_done')
		enabled_sort = ('name', 'due', 'is_done')
		default_sort = ('-is_done', '+due')
		
		
	app = create_api(
		storage=storage,
		resources=(ProjectsResource, TasksResource),
		views=(MinimalView, SirenView)
	)

.. code:: bash
	
	$ gunicorn hammock_todo:app

.. code:: bash

	$ http GET localhost:8000 Accept:application/json

	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 48
	Content-Type: application/json
	Server: gunicorn/19.1.1
	
	{
		"projects": "/projects",
		"tasks": "/tasks"
	}
	
	$ http GET localhost:8000 Accept:application/x-msgpack

	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 33
	Content-Type: application/x-msgpack
	Server: gunicorn/19.1.1
	
	\x82\xa5tasks\xa6/tasks\xa8projects\xa9/projects

	$ http GET localhost:8000 Accept:application/vnd.siren+json

	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 103
	Content-Type: application/vnd.siren+json
	Server: gunicorn/19.1.1

	{
		"links": [
			{"rel": ["projects"], "href": "/projects"},
			{"rel": ["tasks"], "href": "/tasks"}
		]
	}
	
	$ http GET localhost:8000/projects Accept:application/json

	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 16
	Content-Type: application/json
	Server: gunicorn/19.1.1

	{
		"items": []
	}
	
	$ http POST localhost:8000/projects name=Hammock Accept:application/json

	HTTP/1.1 201 CREATED
	Connection: keep-alive
	Content-Length: 60
	Content-Type: application/json
	Server: gunicorn/19.1.1

	{
		"id": "5405dfd4d7abd1118345565a",
	    "name": "Hammock"
	}
	
	$ http GET localhost:8000/projects Accept:application/json

	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 87
	Content-Type: application/json
	Server: gunicorn/19.1.1

	{
		"items": [
			{
				"id": "5405dfd4d7abd1118345565a",
			    "name": "Hammock"
			}
		]
	}

Of course, this doesn't actually work yet (see the next section).

Project Status
~~~~~~~~~~~~~~

Hammock is in the planning and pre-alpha stages. There are high expectations of open source projects these days and that's a good thing. However, good software does not spring, fully formed from the forehead of a sleep deprived genius. Rather, it is (or should be, in this person's humble opinion) the result of continuous design and testing. The whole messy business, starting from day one, is on display here as an invitation to get your hands dirty.

Track progress here: https://www.pivotaltracker.com/n/projects/1158082

Planned Feature Overview
~~~~~~~~~~~~~~~~~~~~~~~~

We want to create a powerful library for developing ReST APIs that supports a lot of use cases. Here is what we think that needs to look like.

Declarative API
+++++++++++++++

Most everything is defined declaratively. That includes the data model, endpoints, filters, sorting and authorization.

Easily extensible
+++++++++++++++++

Data storage, authentication, authorization, serializaton and exchange format are strictly decoupled. Extending functionality in one of these areas requires implementing a small, targeted API.

Self-documenting
++++++++++++++++

By using one of the hypermedia exchange formats and/or a generated spec.

Batteries included
++++++++++++++++++

Comes with quite a few options:

* **Data storage:** MongoDB and SQLAlchemy
* **Authentication:** Basic, HMAC and Token
* **Serialization:** JSON, MessagePack, XML
* **Exchange formats:** A custom, minimalist format as well as the Siren and HAL hypermedia formats.
* **HTTP Caching:** ETags and If-Modified-Since


Acknowledgements
~~~~~~~~~~~~~~~~
This project makes heavy use of `falcon <http://falconframework.org/>`_. Massive credit to that team. As well, `Eve <http://python-eve.org/>`_ was a big inspiration, philosophically and to a lesser extent `flask-mongorest <https://github.com/elasticsales/flask-mongorest>`_.

.. |Build Status| image:: https://travis-ci.org/cooper-software/hammock.svg
   :target: https://travis-ci.org/cooper-software/hammock

.. |Coverage Status| image:: https://img.shields.io/coveralls/cooper-software/hammock.svg
   :target: https://coveralls.io/r/cooper-software/hammock
