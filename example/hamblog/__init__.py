from .api import api
from cellardoor.wsgi.falcon_app import FalconApp

def create_app():
	return FalconApp(api)