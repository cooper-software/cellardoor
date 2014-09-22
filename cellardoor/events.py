class EventManager(object):
	
	def __init__(self, *event_names):
		self.listeners = {
			'pre': dict([(k, []) for k in event_names]), 
			'post': dict([(k, []) for k in event_names])
		}
		
		
	def pre(self, event_name, fn):
		self.add('pre', event_name, fn)
		
		
	def post(self, event_name, fn):
		self.add('post', event_name, fn)
		
		
	def trigger_pre(self, event_name, *args, **kwargs):
		self.trigger('pre', event_name, *args, **kwargs)
		
		
	def trigger_post(self, event_name, *args, **kwargs):
		self.trigger('post', event_name, *args, **kwargs)
		
		
	def add(self, when, event_name, fn):
		self.listeners[when][event_name].append(fn)
		
		
	def trigger(self, when, event_name, *args, **kwargs):
		fns = self.listeners[when][event_name]
		for fn in fns:
			fn(*args, **kwargs)