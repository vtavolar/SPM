## mostly based on Bruno's script

import ROOT, sys, os

jobdir      = "[JOBDIR]"
jobid       = "[JOBID]"

histopath   = "[HISTO]" 
smearpath   = "[SMEAR]" 
interpols   = [[MODEL:interpolsize]]
smoothalgo  = "[MODEL:smoothAlgo]"
nSmooth     = int("[MODEL:nSmooth]")

limits      = ["obs", "exp", "ep1s", "em1s", "ep2s", "em2s", "op1s", "om1s"]

h_lims_mu   = {} # limits in signal-strength, interpolated 
h_lims_mu0  = {} # limits in signal-strength
g2_lims_mu  = {} # TGraph2D limits in signal-strength, automatic interpolation
graphs0     = {} # raw graph
graphs1     = {} # smoothed graph


def extractSmoothedContour(hist, nSmooth=1, algo="k3a"):
	## if name contains "mu" histogram is signal strenght limit, otherwise it's a Yes/No limit
	isMu = "mu" in hist.GetName()
	shist = hist.Clone(hist.GetName()+"_smoothed")
	
	## if smoothing a limit from mu, we need to modify the zeros outside the diagonal, 
	## otherwise the smoothing fools us in the diagonal transition
	if isMu:
		for ix in range(1, shist.GetNbinsX()):
			for iy in range(shist.GetNbinsY(),0,-1):
				if shist.GetBinContent(ix,iy)==0:
					for iyy in range(iy, shist.GetNbinsY()):
						shist.SetBinContent(ix,iyy, shist.GetBinContent(ix,iy-1))
				else:
					continue

	## smooth the histogram
	for s in range(nSmooth):
		if not algo: shist.Smooth()
		else       : shist.Smooth(1,algo)

	## after smoothing a limit from mu, we need to modify the zeros outside the diagonal, 
	## otherwise the contours come wrong for the diagonal
	if isMu:
		for ix in range(1,shist.GetNbinsX()):
		    for iy in range(1,shist.GetNbinsY()):
		    	if hist.GetBinContent(ix,iy)==0:
		    		shist.SetBinContent(ix,iy, 1.1)

	## extract contour        
	shist.SetMinimum(0)
	shist.SetMaximum(2 if isMu else 1)
	shist.SetContour(4 if isMu else 2)
	canvas = ROOT.TCanvas()
	shist.Draw("contz list")
	ROOT.gPad.Update()
	obj = ROOT.gROOT.GetListOfSpecials().FindObject("contours")
	list = obj.At(1 if isMu else 0)
	
	## take largest graph
	max_points = -1
	for l in range(list.GetSize()):
		gr = list.At(l).Clone()
		n_points = gr.GetN()
		if n_points > max_points:
			graph = gr
			max_points = n_points
	
	name = "gr_"+shist.GetName()
	graph.SetName(name)
	graph.Draw("sameC")
	del canvas
	del shist
	del obj
	del list
	return graph



## get list of points

files = []
for f in os.listdir(histopath):
	if f.find("histo_")==-1 or f.find(".root")==-1: continue
	if f.find("HADD")>-1: continue
	files.append(f)



## separate smoothing for every region

for f in files:

	idx = f.rstrip(".root").lstrip("histo_")


	## read histos from file
	interpol = float(interpols[int(idx)]) if len(interpols)>int(idx) else float(interpols[0])

	fin = ROOT.TFile(histopath+"/"+f, "READ")
	for lim in limits:
		h_lims_mu [lim] = fin.Get(lim+"_mu") ; h_lims_mu [lim].SetDirectory(0)
		h_lims_mu0[lim] = fin.Get(lim+"_mu0"); h_lims_mu0[lim].SetDirectory(0)
		g2_lims_mu[lim] = ROOT.TGraph2D(h_lims_mu0[lim]) # unfortunately, we need to redo the TGraph2D
		g2_lims_mu[lim].SetName("g2_"+lim+"_mu0")
		g2_lims_mu[lim].SetNpx( int((g2_lims_mu[lim].GetXmax()-g2_lims_mu[lim].GetXmin())/interpol) )
		g2_lims_mu[lim].SetNpy( int((g2_lims_mu[lim].GetYmax()-g2_lims_mu[lim].GetYmin())/interpol) )
		g2_lims_mu[lim].GetHistogram()
	
	
	## write histos to new file
	
	fout = ROOT.TFile(smearpath+"/smear_"+idx+".root", "RECREATE")
	fout.cd()
	
	# get contour list
	for lim in limits:
		g_list = g2_lims_mu[lim].GetContourList(1.0)
		if not g_list: 
			fout.Close()
			fin.Close()
			print "ERROR: Cannot get contour for this mass scan."
			os.system("touch "+jobdir+"/err_"+jobid)
			sys.exit(1)
		max_points = -1
		for il in range(g_list.GetSize()):
			gr = g_list.At(il)
			n_points = gr.GetN()
			if n_points > max_points:
				graphs0[lim] = gr
				max_points = n_points
		graphs0[lim].SetName("gr_"+lim)
		graphs0[lim].Write()
	
	
	## smoothing the contour list
	    
	for lim in limits:
		graphs1[lim] = extractSmoothedContour(h_lims_mu[lim], nSmooth, smoothalgo)
		graphs1[lim].SetName( graphs1[lim].GetName().replace("_mu","") ) 
		graphs1[lim].Write()
	
	fout.Close()
	fin.Close()


## HADD the individual files
if len(files) > 1:
	if os.path.exists(smearpath+"/smear_HADD.root"): os.system("rm "+smearpath+"/smear_HADD.root")
	os.system("hadd "+smearpath+"/smear_HADD.root "+smearpath+"/smear_*.root")
else:
	os.system("cp "+smearpath+"/smear_0.root "+smearpath+"/smear_HADD.root")

