from falcon.testing import create_environ
from falcon import Request

def create_fake_request(*args, **kwargs):
	environ = create_environ(*args, **kwargs)
	return Request(environ)
	