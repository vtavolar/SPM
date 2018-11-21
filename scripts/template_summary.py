import os, sys, ROOT

bundledir  = "[BUNDLEDIR]/[BUNDLE]"
exclude    = int("[MODEL:excludeDM]")
limitdir   = bundledir+"/limits"
summarydir = bundledir+"/summary"

def testDir(path, access):
	if not os.path.isdir(path) and not os.access(path, access): 
		print "ERROR: directory '"+path+"' does not exist"
		print "Exiting..."
		sys.exit()

testDir(limitdir  , os.R_OK)
testDir(summarydir, os.W_OK)

f    = open(summarydir+"/summary", "w")

for file in os.listdir(limitdir):

	if file.find(".root") == -1: continue
	if os.path.getsize(limitdir+"/"+file) < 500: continue

	rf = ROOT.TFile.Open(limitdir+"/"+file, "read")
	if not rf: continue

	lims = [0 for i in range(8)]
	ns = file.rstrip(".root").split(".")
	lims[0] = int(ns[-2].lstrip("mH"))
	lims[1] = int(ns[-1])

	if abs(lims[0]-lims[1])<=exclude: continue

	rt = rf.Get("limit")
	if not rt: continue
	for ev in rt:
		if abs(ev.quantileExpected + 1    ) < 0.02: lims[3] = ev.limit
		if abs(ev.quantileExpected - 0.5  ) < 0.02: lims[2] = ev.limit
		if abs(ev.quantileExpected - 0.16 ) < 0.02: lims[5] = ev.limit
		if abs(ev.quantileExpected - 0.84 ) < 0.02: lims[4] = ev.limit
		if abs(ev.quantileExpected - 0.025) < 0.02: lims[7] = ev.limit
		if abs(ev.quantileExpected - 0.975) < 0.02: lims[6] = ev.limit
	f.write(" : ".join(str(y) for y in lims)+"\n")
	rf.Close()

f.close()


