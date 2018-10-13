import os, sys

pdir = "/afs/cern.ch/user/c/cheidegg/www/scans/2017-05-24_fullstatus/"

args = sys.argv[1:]

if len(args)<2:
	print "python publish.py bundle name"
	sys.exit()

def cmd(base):
	print base
	os.system(base)

pdir = pdir.rstrip("/")+"/"

for ext in [".C",".png",".pdf",".root"]:
	cmd("cp tmp/bundle/"+args[0]+"/plot/plot"+ext+" "+pdir+"/"+args[1]+"_"+args[0]+ext)

