import falcon
from cellardoor import CellarDoor
from cellardoor.falcon import add_to_falcon
from cellardoor.views import MinimalView
from . import collections
from .storage import storage


def create_app():
	app = falcon.API()
	api = CellarDoor(
			collections=collections
			storage=storage)

	add_to_falcon(app, api)
	return app