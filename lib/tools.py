import os
from functions import *

class myInit():
	def __init__(self, path):
		self.path = path
		if not os.path.exists(path): return
		f = open(path)
		lines = f.readlines()
		f.close()
		for line in lines:
			sl = [s.strip().rstrip("\n").strip() for s in line.split(":")]
			if sl[0][-1]=="+": setattr(self, sl[0][:-1], sl[1].split(","))
			else             : setattr(self, sl[0]     , sl[1]           )
	def write(self, dictionary = {}):
		f = open(self.path, "a")
		for key, val in dictionary.iteritems():
			f.write(key +" : "+ val +"\n")
			setAttrFromLine(self, key +" : "+ val)
		f.close()
