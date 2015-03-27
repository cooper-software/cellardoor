class Subject(object):
	
	def __init__(self, *event_names):
		self.allowed_events = set(event_names)
		self.listeners = dict([(x, []) for x in event_names])
		

	def __call__(self, event_name, handler):
		assert event_name in self.allowed_events, "%s is not a valid event for this subject" % event_name
		self.listeners[event_name].append(handler)
		
		
	def fire(self, event_name, *args, **kwargs):
		assert event_name in self.allowed_events, "%s is not a valid event for this subject" % event_name
		fns = self.listeners[event_name]
		for fn in fns:
			fn(*args, **kwargs)