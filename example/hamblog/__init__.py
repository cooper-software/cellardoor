from .api import api
from cellardoor.wsgi.falcon_integration import FalconApp

def create_app():
	return create_falcon_app(api)