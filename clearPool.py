import os,sys
from lib import functions, tools

for package in os.listdir("tmp/pool/"):
	if not os.path.exists("tmp/pool/"+package+"/init"): continue
	init = tools.myInit("tmp/pool/"+package+"/init")
	ncards = int(functions.bash(None, "find tmp/pool/"+package+"/cards -type f | wc -l"))
	nfiles = int(functions.bash(None, "find tmp/pool/"+package+"/files -type f | wc -l"))
	if ncards==0 or nfiles==0:
		print "rm -r tmp/pool/"+package
		#print package, init.model, sorted(list(set(init.lumis))), sorted(init.regions)
