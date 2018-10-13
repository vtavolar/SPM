import os,sys
from lib import tools

args = sys.argv[1:]
if len(args)<1: sys.exit()
model = args[0]

for bundle in os.listdir("tmp/bundle/"):
	if not os.path.exists("tmp/bundle/"+bundle+"/init"): continue
	init = tools.myInit("tmp/bundle/"+bundle+"/init")
	if init.model==model:
		print bundle, init.mode, sorted(list(set(init.lumis))), sorted(init.regions)
