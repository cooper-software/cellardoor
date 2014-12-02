from functools import partial


class EventManager(object):
	
	def __init__(self, *event_names):
		self.listeners = {
			'before': dict([(k, []) for k in event_names]), 
			'after': dict([(k, []) for k in event_names])
		}
		
		for when, events in self.listeners.items():
			for event in events.keys():
				setattr(self, '%s_%s' % (when, event), partial(self.register, when, event))
				setattr(self, 'fire_%s_%s' % (when, event), partial(self.fire, when, event))
		
		
	def register(self, when, event_name, fn):
		self.listeners[when][event_name].append(fn)
		
		
	def fire(self, when, event_name, *args, **kwargs):
		fns = self.listeners[when][event_name]
		for fn in fns:
			fn(*args, **kwargs)
			
			
	def update_from(self, other):
		for when, events in other.listeners.items():
			for event, listeners in events.items():
				for fn in listeners:
					self.register(when, event, fn)