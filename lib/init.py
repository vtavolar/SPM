import os
from functions import *


class Init():
	def __init__(self, obj, path):
		self.obj  = obj
		self.mm   = obj.master if hasattr(obj, "master") else obj
		self.path = path
		self.load()
	def append(self, key, value):
		if not self.importdir: return
		f = open(self.path, "a")
		f.write(key +" : "+ value +"\n")
		f.close()
	def load(self):
		if not os.path.exists(self.path): return
		for line in [l.strip("\n") for l in open(self.path,"r").readlines()]:
			if line[0]=="#" or len(line.strip())==0: continue
			setAttrFromLine(self.obj, line)
	def read(self, key):
		fl = open(self.path, "r").readlines()
		for line in fl:
			if key in line:
				return line
		return ""
	def update(self, key, value):
		replaced = False
		f = open(self.path+"2","w")
		for line in [l.rstrip("\n") for l in open(self.path, "r").readlines()]:
			if line.find(":") > -1:
				sl = [s.strip() for s in line.split(":")]
				if sl[0] == key: 
					line = key +" : "+ value +"\n"
					setAttrFromLine(self.obj, line)
					replaced = True
				else:
					line = line+"\n"
			f.write(line)
		if not replaced: f.write(key +" : "+ value +"\n")
		f.close()
		mv(self.mm, self.path+"2", self.path)
	def write(self, dictionary = {}):
		f = open(self.path, "a")
		for key, val in dictionary.iteritems():
			f.write(key +" : "+ val +"\n")
			setAttrFromLine(self.obj, key +" : "+ val)
		f.close()
