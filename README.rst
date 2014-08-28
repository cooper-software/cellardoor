Hammock
=======

|Build Status| |Coverage Status|

Hammock generates a `falcon API <http://falconframework.org/>`_ from a set of `mongoengine <http://mongoengine.org/>`_ documents. Its goal is to enhance DRY and a declarative mode without sacrificing flexibility.

Example
~~~~~~~

.. code:: python

	import mongoengine as me
	import hammock

	class Swallow(me.Document):
		is_laden = me.BooleanField()
		air_speed_velocity = me.FloatField()


	class Swallows(hammock.Collection):
		document = Swallow


	app = hammock.create_api([Swallows])

.. code:: bash
	
	$ gunicorn swallows:app

.. code:: bash

	$ http GET localhost:8000

	HTTP/1.1 200 OK
	Cache-Control: max-age=20
	Connection: keep-alive
	Content-Length: 88
	Content-Type: application/json
	Date: Wed, 27 Aug 2014 14:51:23 GMT
	Expires: Wed, 27 Aug 2014 14:51:43 GMT
	Server: gunicorn/19.1.1
	
	{
		"_links": [
			{
				"href": "localhost:8000/swallows",
				"title": "swallows"
			}
		]
	}

	$ http GET localhost:8000/swallows

	HTTP/1.1 200 OK
	Cache-Control: max-age=20
	Connection: keep-alive
	Content-Length: 178
	Content-Type: application/json
	Date: Wed, 27 Aug 2014 14:54:12 GMT
	Expires: Wed, 27 Aug 2014 14:54:32 GMT
	Server: gunicorn/19.1.1

	{
		"_items": [],
		"_links": {
			"parent": {
				"href": "localhost:8000",
				"title": "home"
			},
			"self": {
				"href": "localhost:8000/swallows",
				"title": "swallows"
			}
		}
	}

	$ http POST localhost:8000/swallows is_laden=true air_speed_velocity=9.9

	HTTP/1.1 201 CREATED
	Connection: keep-alive
	Content-Length: 219
	Content-Type: application/json
	Date: Wed, 27 Aug 2014 15:02:27 GMT
	Server: gunicorn/19.1.1

	{
	    "_id": "53fdf303e1e2e40002c5396f", 
	    "_links": {
	        "self": {
	            "href": "localhost:8000/swallows/53fdf303e1e2e40002c5396f", 
	            "title": "swallow"
	        }
	    }, 
	    "_status": "OK"
	}


Of course, this doesn't actually work yet (see the following section).

Project Status
~~~~~~~~~~~~~~

Hammock is in the planning and pre-alpha stages. There are high expectations of open source projects these days and that's a good thing. However, good software does not spring, fully formed from the forehead of a sleep deprived genius. Rather, it is (or should be, in this person's humble opinion) the result of continuous design and testing. The whole messy business, starting from day one, is on display here as an invitation to get your hands dirty.

Acknowledgements
~~~~~~~~~~~~~~~~
This project is basically some sugar on top of `falcon <http://falconframework.org/>`_ and `mongoengine <http://mongoengine.org/>`_. Massive credit to those teams. In additon, `eve <http://python-eve.org/>`_ was a big inspiration. In fact, hammock aspires to produce essentially the same ReST APIs. Why not just use eve? A few reasons: performance, tighter mongoengine integration, simpler API.

.. |Build Status| image:: https://travis-ci.org/cooper-software/hammock.svg
   :target: https://travis-ci.org/cooper-software/hammock

.. |Coverage Status| image:: https://img.shields.io/coveralls/cooper-software/hammock.svg
   :target: https://coveralls.io/r/cooper-software/hammock
