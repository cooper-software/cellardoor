import falcon
from hammock import Hammock
from hammock.falcon import add_to_falcon
from hammock.views import MinimalView
from . import collections
from .storage import storage


def create_app():
	app = falcon.API()
	api = Hammock(
			collections=collections
			storage=storage)

	add_to_falcon(app, api)
	return app