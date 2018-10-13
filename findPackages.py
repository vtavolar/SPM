import os,sys
from lib import tools

installdir = "/mnt/t3nfs01/data01/shome/cheidegg/d/SPM/"

args = sys.argv[1:]
if len(args)<1: sys.exit()
regions = args[0].split(",")
lumis   = args[1].split(",") if len(args)>1 else []
models  = args[2].split(",") if len(args)>2 else []

for package in os.listdir(installdir+"tmp/pool/"):
	if not os.path.exists(installdir+"tmp/pool/"+package+"/init"): continue
	init = tools.myInit(installdir+"tmp/pool/"+package+"/init")
	if not (len(regions)>0 and init.region in regions): continue
	if not (len(lumis  )>0 and init.lumi   in lumis  ): continue
	if not (len(models )>0 and init.model  in models ): continue
	print package
