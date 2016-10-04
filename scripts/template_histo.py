## mostly based on Bruno's script

import ROOT, array, os, sys

histopath    = "[HISTO]"
summarypath  = "[SUMMARY]"
spmpath      = "[SPMDIR]"
xsecpath     = spmpath+"/[MODEL:xsecfile]"
brcorr       = eval("[MODEL:brcorr]")
binning1     = "[MODEL:binningX]"
binning2     = "[MODEL:binningY]"
model        = "[MODEL:name]"
histoDeltaMs = [[MODEL:histoDeltaM]] + ['0']
interpols    = [[MODEL:interpolsize]]

limits       = ["obs", "exp", "ep1s", "em1s", "ep2s", "em2s", "op1s", "om1s"]


class Limit():
	def __init__(self, xslist, line, separator = ":"):
		line = line.rstrip("\n")
		split = line.split(separator)
		self.xslist    = xslist
		self.line      = line
		self.separator = separator
		self.mass1     = float(split[0].strip())
		self.mass2     = float(split[1].strip())
		self.obs       = float(split[3].strip())
		self.exp       = float(split[2].strip())
		self.ep1s      = float(split[4].strip())
		self.em1s      = float(split[5].strip())
		self.ep2s      = float(split[6].strip())
		self.em2s      = float(split[7].strip())
		self.xs        = xslist.getXS (self.mass1)
		self.xe        = xslist.getErr(self.mass1)
		self.op1s      = self.obs * self.xs / (self.xs - self.xe)
		self.om1s      = self.obs * self.xs / (self.xs + self.xe)

class XSlist():
	def __init__(self, path, brcorr):
		xslist      = [l.rstrip("\n").split(":") for l in open(path, "r").readlines()]
		xslist      = [[float(m.strip()),float(xs.strip()),float(err.strip())] for [m,xs,err] in xslist ]
		self.mass   = [p[0] for p in xslist]
		self.xs     = [p[1] for p in xslist]
		self.err    = [p[2] for p in xslist]
		self.brcorr = float(brcorr)
	def getBin(self, mass):
		lowerbin = int(round(mass / 25)) * 25
		if not lowerbin in self.mass: return -1
		return self.mass.index(lowerbin)	
	def getErr(self, mass):
		bin = self.getBin(mass)
		if bin == -1: return 0
		return self.err[bin]*self.brcorr
	def getXS(self, mass):
		bin = self.getBin(mass)
		if bin == -1: return 0
		return self.xs[bin]*self.brcorr

def getSubset(already, alllimits, deltaM, binningY):
	if deltaM <= 0: return filter(lambda x: not any([x in a for a in already]), alllimits)
	subset = []
	for limit in alllimits:
		if abs(limit.mass1-limit.mass2) > deltaM: continue
		if any([limit in R for R in already]): continue
		subset.append(limit)
	subset = fillHoles(subset, deltaM, binningY)
	return subset

def fillHoles(theList, deltaM, binningY):
	m1s = [l.mass1 for l in theList]
	for m1 in m1s:
		lims  = [l for l in theList if l.mass1 == m1]
		maxM2 = 0; theMax = None
		for l in lims:
			if l.mass2 <= maxM2: continue
			maxM2  = l.mass2
			theMax = l
		insertM2 = getInsertMasses(binningY, deltaM, maxM2)
		for m in insertM2:
			theList.append(Limit(theMax.xslist, theMax.line, theMax.separator))
	return theList

def getInsertMasses(binningY, deltaM, maxM2):
	theBins = filter(lambda x: x <= deltaM and x > maxM2, binningY)
	masses  = []
	for b in range(1,len(theBins)):
		masses.append(theBins[b-1]+float(theBins[b]-theBins[b-1])/2)
	return masses

def getBinning(binning):
	if "[" in binning:
		b1 = [float(b) for b in binning.rstrip("]").lstrip("[").split(",")]
		print "ERROR: Irregular binning not supported"
		sys.exit(1)
	s = [float(b) for b in binning.split(",")]
	return s
	##else:
	##	s  = [float(b) for b in binning.split(",")]
	##	d  = (s[2]-s[1])/s[0]
	##	b1 = [s[1]+d*i for i in range(int(s[0]))] + [s[2]]
	##return b1

def getLimitYN ( h_lim_mu, r_exluded=1):
	name = h_lim_mu.GetName().replace("mu","yn")
	h_lim_yn = h_lim_mu.Clone(name)
	for ix in range(1,h_lim_yn.GetNbinsX()+1):
		for iy in range(1,h_lim_yn.GetNbinsY()+1):
			r = h_lim_yn.GetBinContent(ix,iy)
			h_lim_yn.SetBinContent(ix, iy, 1e-3 if r>r_exluded else 1 if r>0 else 0)
	return h_lim_yn
    
def getLimitXS ( h_lim_mu, xslist):
	name = h_lim_mu.GetName().replace("mu","xs")
	h_lim_xs = h_lim_mu.Clone(name)
	for ix in range(1, h_lim_xs.GetNbinsX()+1):
		m  = h_lim_xs.GetXaxis().GetBinCenter(ix)
		xs = xslist.getXS(m)
		for iy in range(1,h_lim_xs.GetNbinsY()+1):
			r  = h_lim_xs.GetBinContent(ix,iy)
			h_lim_xs.SetBinContent(ix, iy, r*xs)
	return h_lim_xs
    

## retrieving limits	

b1     = getBinning(binning1)
b2     = getBinning(binning2)
xslist = XSlist(xsecpath, brcorr)

allpoints = []
for line in open(summarypath+"/summary","r").readlines():
	allpoints.append(Limit(xslist, line))
	

## splitting phase space according to deltaMs

thePointList = []
for DM in histoDeltaMs:
	thePointList.append(getSubset(thePointList, allpoints, int(DM), b2))


## making histogram for every subset

for idx,points in enumerate(thePointList):


	## reserving dictionaries
	
	h_lims_mu0   = {} # limits in signal-strength, original binning
	h_lims_yn0   = {} # limits in excluded/non-exluded, original binning
	h_lims_xs0   = {} # limits in cross-section, original binning
	
	h_lims_mu    = {} # limits in signal-strength, interpolated
	h_lims_yn    = {} # limits in excluded/non-exluded, interpolated
	h_lims_xs    = {} # limits in cross-section, interpolated
	g2_lims_mu   = {} # TGraph2D limits in signal-strength, automatic interpolation


	## making histograms
	
	for lim in limits:
		h_lims_mu0[lim] = ROOT.TH2F(lim+"_mu0", model, b1[0], b1[1], b1[2], b2[0], b2[1], b2[2])
		#h_lims_mu0[lim] = ROOT.TH2F(lim+"_mu0", model, len(b1)-1, array.array('d',b1), len(b2)-1, array.array('d', b2))
		h_lims_mu0[lim].SetXTitle("massX")    
		h_lims_mu0[lim].SetYTitle("massY")
		h_lims_yn0[lim] = h_lims_mu0[lim].Clone(h_lims_mu0[lim].GetName().replace("mu","yn"))
		h_lims_xs0[lim] = h_lims_mu0[lim].Clone(h_lims_mu0[lim].GetName().replace("mu","xs"))
	
	
	## fill histograms
	
	for point in points:
		for lim in limits:
			binX=h_lims_mu0[lim].GetXaxis().FindBin(point.mass1)
			binY=h_lims_mu0[lim].GetYaxis().FindBin(point.mass2)
			h_lims_mu0[lim].SetBinContent(binX, binY, getattr(point, lim))
			h_lims_xs0[lim].SetBinContent(binX, binY, getattr(point, lim)*xslist.getXS(point.mass1))
			h_lims_yn0[lim].SetBinContent(binX, binY, 1 if getattr(point, lim)<1 else 1e-3)
	
	
	## interpolating
	interpol = interpols[idx] if len(interpols)>idx else interpols[0]
	interpol = float(interpol)	

	for lim in limits:
		g2_lims_mu[lim] = ROOT.TGraph2D(h_lims_mu0[lim])
		g2_lims_mu[lim].SetName("g2_"+lim+"_mu0")
		g2_lims_mu[lim].SetNpx( int((g2_lims_mu[lim].GetXmax()-g2_lims_mu[lim].GetXmin())/interpol) )
		g2_lims_mu[lim].SetNpy( int((g2_lims_mu[lim].GetYmax()-g2_lims_mu[lim].GetYmin())/interpol) )
		h_lims_mu[lim] = g2_lims_mu[lim].GetHistogram()
		h_lims_mu[lim].SetName( h_lims_mu0[lim].GetName().replace("mu0","mu") )
		h_lims_yn[lim] = getLimitYN ( h_lims_mu[lim] )
		h_lims_xs[lim] = getLimitXS ( h_lims_mu[lim], xslist )
	
	
	## saving histograms to disk
	
	fout = ROOT.TFile(histopath+"/histo_"+str(idx)+".root", "RECREATE")
	fout.cd()
	
	for lim in limits:    
		g2_lims_mu[lim].Write()
		h_lims_mu0[lim].Write()
		h_lims_xs0[lim].Write()
		h_lims_yn0[lim].Write()
		h_lims_mu [lim].Write()
		h_lims_xs [lim].Write()
		h_lims_yn [lim].Write()
	
	fout.Close()
		


## HADD the individual files
if len(thePointList) > 1:
	if os.path.exists(histopath+"/histo_HADD.root"): os.system("rm "+histopath+"/histo_HADD.root")
	os.system("hadd "+histopath+"/histo_HADD.root "+histopath+"/histo_*.root")
else:
	os.system("cp "+histopath+"/histo_0.root "+histopath+"/histo_HADD.root")


