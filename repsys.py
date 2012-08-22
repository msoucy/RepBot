import operator

class ReputationSystem(object):
	__slots__=('reps', 'ignorelist', 'cached')
	
	def __init__(self):
		self.reps={}
		self.ignorelist=set()
		self.cached = [None,None]
		try:
			self.reps = eval(open("reps.txt").read())
			print "Read reputation file."
		except SyntaxError:
			print "Error: could not read reputation file. Contents: `{0}`".format(open("reps.txt").read())
		except IOError:
			print "Error: could not open reputation file"
		self.filter()
	
	def dump(self):
		self.filter()
		fi = open("reps.txt","w")
		fi.write(str(self.reps))
		fi.close()
	
	def incr(self, name):
		self.reps[name]=self.reps.get(name,0)+1
	
	def decr(self, name):
		self.reps[name]=self.reps.get(name,0)-1
	
	def get(self, name):
		return self.reps.get(name,0)
	
	def set(self, name, val):
		self.reps[name] = int(val)
	
	def clear(self, name):
		self.reps.pop(name.strip(),None)
	
	def filter(self):
		self.reps = {key:val for key, val in self.reps.items() if val != 0}
	
	def report(self):
		self.filter()
		sorted_reps = list(reversed(sorted(self.reps.iteritems(), key=operator.itemgetter(1))))
		highest = sorted_reps[:5]
		lowest = sorted_reps[-5:]
		ret = ""
		if highest != self.cached[0]:
			ret += "Top reps: {0}\n".format(highest)
			cached[0] = highest
		if lowest != self.cached[1]:
			ret += "Bottom reps: {0}\n".format(lowest)
			cached[1] = lowest
		return ret.strip()
	
	def tell(self, name):
		self.filter()
		return "Rep for {0}: {1}".format(name,self.get(name))
	
	def all(self):
		self.filter()
		return "All reps: {0}".format(self.reps)


