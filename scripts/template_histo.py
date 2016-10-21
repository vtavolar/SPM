## mostly based on Bruno's script

import ROOT, array, os, sys

histopath    = "[HISTO]"
summarypath  = "[SUMMARY]"
spmpath      = "[SPMDIR]"

limits       = ["obs", "exp", "ep1s", "em1s", "ep2s", "em2s", "op1s", "om1s"]

class Model():
	def __init__(self):
		self.name         = "[MODEL:name]"
		self.xsecpath     = spmpath+"/[MODEL:xsecfile]"
		self.brcorr       = eval("[MODEL:brcorr]")
		self.param1       = "[MODEL:paramX]".replace("mass1", "point.mass1").replace("mass2","point.mass2")
		self.param2       = "[MODEL:paramY]".replace("mass1", "point.mass1").replace("mass2","point.mass2")
		self.b1           = getBinning("[MODEL:binningX]")
		self.b2           = getBinning("[MODEL:binningY]")
		self.histoDeltaMs = [[MODEL:histoDeltaM]]
		self.histoDeltaMs = [int(d) for d in self.histoDeltaMs]
		self.histoDeltaMs += [0]
		self.interpol     = float([MODEL:interpolsize])

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
	def __init__(self, model):
		xslist      = [l.rstrip("\n").split(":") for l in open(model.xsecpath, "r").readlines()]
		xslist      = [[float(m.strip()),float(xs.strip()),float(err.strip())] for [m,xs,err] in xslist ]
		self.mass   = [p[0] for p in xslist]
		self.xs     = [p[1] for p in xslist]
		self.err    = [p[2] for p in xslist]
		self.brcorr = float(model.brcorr)
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


def getNbins(npx, graphintervall, histintervall):
	return int(npx * float(histintervall) / float(graphintervall))

def insertTH2(target, toCopy, useLowerEdge = False):
	for i in range(1,toCopy.GetXaxis().GetNbins()+1):
		for j in range(1,toCopy.GetYaxis().GetNbins()+1):
			x = toCopy.GetXaxis().GetBinLowEdge(i) if useLowerEdge else toCopy.GetXaxis().GetBinCenter(i)
			y = toCopy.GetYaxis().GetBinLowEdge(j) if useLowerEdge else toCopy.GetYaxis().GetBinCenter(j)
			xbin = target.GetXaxis().FindBin(x)
			ybin = target.GetYaxis().FindBin(y)
			target.SetBinContent(xbin, ybin, toCopy.GetBinContent(i,j))
			target.SetBinError  (xbin, ybin, toCopy.GetBinError  (i,j))
	return target

def getFirstFilledBin(histogram):
	for x in range(1,histogram.GetXaxis().GetNbins()+1):
		for y in range(1,histogram.GetYaxis().GetNbins()+1):
			if histogram.GetBinContent(x,y) > 0:
				return x,y
	return -1,-1

def getLastFilledBin(histogram):
	for x in reversed(range(1,histogram.GetXaxis().GetNbins()+1)):
		for y in reversed(range(1,histogram.GetYaxis().GetNbins()+1)):
			if histogram.GetBinContent(x,y) > 0:
				return x,y
	return -1,-1

def getLastFilledBinX(histogram, ybin):
	for x in reversed(range(1,histogram.GetXaxis().GetNbins()+1)):
		if histogram.GetBinContent(x,ybin) > 0:
			return x
	return -1

def getFirstFilledBinY(histogram, xbin):
	for y in range(1,histogram.GetYaxis().GetNbins()+1):
		if histogram.GetBinContent(xbin,y) > 0:
			return y
	return -1

def getLastFilledBinY(histogram, xbin):
	for y in reversed(range(1,histogram.GetYaxis().GetNbins()+1)):
		if histogram.GetBinContent(xbin,y) > 0:
			return y
	return -1

def hasLinearOffset(histogram):
	x1,y1 = getFirstFilledBin(histogram)
	x2,y2 = getLastFilledBin (histogram)
	extendX = [histogram.GetBinContent(x , y1)>0 for x in range(x1+1,histogram.GetXaxis().GetNbins()+1)].count(True) >= 2
	extendY = [histogram.GetBinContent(x1, y )>0 for y in range(y1+1,histogram.GetYaxis().GetNbins()+1)].count(True) >= 2
	backX   = [histogram.GetBinContent(x2, y )>0 for y in reversed(range(1,y2))                        ].count(True) >= 2
	return extendY, extendX, backX


def fillBoundary(histo, buffer):
	alongX, alongY, backX = hasLinearOffset(buffer)
	slope = 1 # 1 bin in y for 1 bin in x
	if alongX: histo = fillBoundaryAlongX(histo, buffer, True , slope)
	if alongY: histo = fillBoundaryAlongY(histo, buffer, True , slope)
	if backX : histo = fillBoundaryBackX (histo, histo , False, slope)
	return histo

def fillBoundaryBackX(histo, buffer, useLowerEdge = True, slope = 1):

	maxXbin, maxYbin = getLastFilledBin(buffer)
	if maxXbin==-1: return histo ## nothing in there

	minYbin = getFirstFilledBinY(buffer, maxXbin)
	maxXval = buffer.GetXaxis().GetBinLowEdge(maxXbin) if useLowerEdge else buffer.GetXaxis().GetBinCenter(maxXbin)
	maxYval = buffer.GetYaxis().GetBinLowEdge(maxYbin) if useLowerEdge else buffer.GetYaxis().GetBinCenter(maxYbin)

	sep     = histo.GetXaxis().GetBinWidth(1) # assume uniform binning
	
	for x in range(1,histo.GetXaxis().GetNbins()+1):
		if histo.GetXaxis().GetBinCenter(x) < maxXval: continue
		for y in range(1,histo.GetYaxis().GetNbins()+1):
			if histo.GetBinContent(x, y)        >  0      : continue
			if histo.GetYaxis().GetBinCenter(y) >= maxYval: break
			ybin = buffer.GetYaxis().FindBin(histo.GetYaxis().GetBinCenter(y))
			histo.SetBinContent(x, y, buffer.GetBinContent(x-1, ybin))
	return histo

def fillBoundaryAlongX(histo, buffer, useLowerEdge = True, slope = 1):

	minXbin, minYbin = getFirstFilledBin(buffer)
	if minXbin==-1: return histo ## nothing in there

	maxYbin = getLastFilledBinY(buffer, minXbin)
	minXval = buffer.GetXaxis().GetBinLowEdge(minXbin) if useLowerEdge else buffer.GetXaxis().GetBinCenter(minXbin)
	minYval = buffer.GetYaxis().GetBinLowEdge(minYbin) if useLowerEdge else buffer.GetYaxis().GetBinCenter(minYbin)
	maxYval = buffer.GetYaxis().GetBinLowEdge(maxYbin) if useLowerEdge else buffer.GetYaxis().GetBinCenter(maxYbin)

	sep     = histo.GetXaxis().GetBinWidth(1) # assume uniform binning
	
	for x in range(1,histo.GetXaxis().GetNbins()+1):
		dist = int(int(minXval-histo.GetXaxis().GetBinCenter(x))/sep*slope) # distance in terms of bins
		if dist <= 0: break
		for y in range(1,histo.GetYaxis().GetNbins()+1):
			if histo.GetBinContent(x, y + dist)        >  0      : continue
			if histo.GetYaxis().GetBinCenter(y + dist) >= maxYval: break
			ybin = buffer.GetYaxis().FindBin(histo.GetYaxis().GetBinCenter(y)) + dist
			histo.SetBinContent(x, y, buffer.GetBinContent(minXbin, ybin))

	return histo

def fillBoundaryAlongY(histo, buffer, useLowerEdge = True, slope = 1):

	minXbin, minYbin = getFirstFilledBin(buffer)
	if minXbin==-1: return histo ## nothing in there

	maxXbin = getLastFilledBinX(buffer, minYbin)
	minYval = buffer.GetYaxis().GetBinLowEdge(minYbin) if useLowerEdge else buffer.GetYaxis().GetBinCenter(minYbin)
	minXval = buffer.GetXaxis().GetBinLowEdge(minXbin) if useLowerEdge else buffer.GetXaxis().GetBinCenter(minXbin)
	maxXval = buffer.GetXaxis().GetBinLowEdge(maxXbin) if useLowerEdge else buffer.GetXaxis().GetBinCenter(maxXbin)

	sep     = histo.GetYaxis().GetBinWidth(1) # assume uniform binning

	for y in range(1,histo.GetYaxis().GetNbins()+1):
		dist = int(minYval-histo.GetYaxis().GetBinCenter(y))/(sep*slope) # distance in terms of bins
		if dist <= 0: break
		for x in range(1,histo.GetXaxis().GetNbins()+1):
			if histo.GetBinContent(x, y)        >  0      : continue
			if histo.GetXaxis().GetBinCenter(x) <  minXval: continue
			if histo.GetXaxis().GetBinCenter(x) >= maxXval: break
			xbin = buffer.GetXaxis().FindBin(histo.GetXaxis().GetBinCenter(x)) # + dist
			histo.SetBinContent(x, y, buffer.GetBinContent(xbin, minYbin))

	return histo


def makeHistFromGraph(model, graph, name, deltaM = 0):
	deltaM  = int(deltaM)
	npx     = getNbins(graph.GetNpx(), graph.GetXmax()-graph.GetXmin(), model.b1[2]-model.b1[1])
	npy     = getNbins(graph.GetNpy(), graph.GetYmax()-graph.GetYmin(), model.b2[2]-model.b2[1])
	binsize = (model.b2[2]-model.b2[1])/npy
	theHist = ROOT.TH2F(name, model.name, npx, model.b1[1], model.b1[2], npy, model.b2[1], model.b2[2])
	theHist.SetXTitle("massX")
	theHist.SetYTitle("massY")
	buffer  = graph.GetHistogram()
	theHist = insertTH2(theHist, buffer, True) # use lower edge of the bin due to offset. CRUCIAL!
	theHist = fillBoundary(theHist, buffer)
	#theHist = fillHolesHisto(theHist, deltaM, binsize)
	return theHist

##def copyTH2(base, points):
##	new = base.Clone(); new.Reset()
##	for point in points:
##		new = copyPoint(new, base, point)
##	return new
##
##def copyPoint(target, toCopy, point):
##	iOld = toCopy.GetXaxis().FindBin(point.mass1)
##	jOld = toCopy.GetYaxis().FindBin(point.mass2)
##	iNew = target.GetXaxis().FindBin(point.mass1)
##	jNew = target.GetYaxis().FindBin(point.mass2)
##	target.SetBinContent(iNew, jNew, toCopy.GetBinContent(iOld, jOld))
##	target.SetBinError  (iNew, jNew, toCopy.GetBinError  (iOld, jOld))
##	return target

def getSubset(already, alllimits, deltaM, binningY):
	if deltaM <= 0: return filter(lambda x: not any([x in a for a in already]), alllimits)
	subset = []
	for limit in alllimits:
		if abs(limit.mass1-limit.mass2) > deltaM: continue
		if any([limit in R for R in already]): continue
		subset.append(limit)
	subset = fillHolesSubset(subset, deltaM, binningY)
	return subset

def fillHolesHisto(theHisto, deltaM, binningY):
	if deltaM==0: return theHisto
	for xbin in range(1,theHisto.GetXaxis().GetNbins()+1):
		ybin   = getFirstFilledBinY(theHisto, xbin)
		yfirst = theHisto.GetYaxis().GetBinCenter(ybin)
		ydiag  = theHisto.GetXaxis().GetBinCenter(xbin)-deltaM
		binsToFill = int((ydiag-yfirst)/binningY)
		print "binsToFill = "+str(binsToFill)
		value  = theHisto.GetBinContent(xbin,ybin) 
		for theB in range(1,binsToFill):
			theHisto.SetBinContent(xbin, ybin-theB, value)
	return theHisto

def fillHolesSubset(theList, deltaM, binningY):
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
	s = [int(b) if ib==0 else float(b) for ib,b in enumerate(binning.split(","))]
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
model  = Model()
xslist = XSlist(model)

allpoints = []
for line in open(summarypath+"/summary","r").readlines():
	allpoints.append(Limit(xslist, line))
	

## splitting phase space according to deltaMs

thePointList = []
for DM in model.histoDeltaMs:
	thePointList.append(getSubset(thePointList, allpoints, DM, model.b2))


## running first over all allpoints
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
		h_lims_mu0[lim] = ROOT.TH2F(lim+"_mu0", model.name, model.b1[0], model.b1[1], model.b1[2], model.b2[0], model.b2[1], model.b2[2])
		h_lims_mu0[lim].SetXTitle("massX")    
		h_lims_mu0[lim].SetYTitle("massY")
		h_lims_yn0[lim] = h_lims_mu0[lim].Clone(h_lims_mu0[lim].GetName().replace("mu","yn"))
		h_lims_xs0[lim] = h_lims_mu0[lim].Clone(h_lims_mu0[lim].GetName().replace("mu","xs"))
	
	
	## fill histograms
	
	for point in points:
		for lim in limits:
			binX=h_lims_mu0[lim].GetXaxis().FindBin(eval(model.param1))
			binY=h_lims_mu0[lim].GetYaxis().FindBin(eval(model.param2))
			h_lims_mu0[lim].SetBinContent(binX, binY, getattr(point, lim))
			h_lims_xs0[lim].SetBinContent(binX, binY, getattr(point, lim)*xslist.getXS(point.mass1))
			h_lims_yn0[lim].SetBinContent(binX, binY, 1 if getattr(point, lim)<1 else 1e-3)
	
	
	## interpolating
	for lim in limits:
		g2_lims_mu[lim] = ROOT.TGraph2D(h_lims_mu0[lim])
		g2_lims_mu[lim].SetName("g2_"+lim+"_mu0")
		g2_lims_mu[lim].SetNpx( int((g2_lims_mu[lim].GetXmax()-g2_lims_mu[lim].GetXmin())/model.interpol) )
		g2_lims_mu[lim].SetNpy( int((g2_lims_mu[lim].GetYmax()-g2_lims_mu[lim].GetYmin())/model.interpol) )
		newname = h_lims_mu0[lim].GetName().replace("mu0","mu")
		h_lims_mu[lim] = makeHistFromGraph(model, g2_lims_mu[lim], newname, model.histoDeltaMs[idx])
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


## merge the individual histograms
if len(thePointList) > 1:
	if os.path.exists(histopath+"/histo_HADD.root"): os.system("rm "+histopath+"/histo_HADD.root")
	os.system("hadd "+histopath+"/histo_HADD.root "+histopath+"/histo_*.root")
else:
	os.system("cp "+histopath+"/histo_0.root "+histopath+"/histo_HADD.root")


#### making histogram for every subset
##
##for idx,points in enumerate(thePointList):
##
##	## reserving dictionaries
##	
##	copyh_lims_mu0   = {} # limits in signal-strength, original binning
##	copyh_lims_yn0   = {} # limits in excluded/non-exluded, original binning
##	copyh_lims_xs0   = {} # limits in cross-section, original binning
##	copyh_lims_mu    = {} # limits in signal-strength, interpolated
##	copyh_lims_yn    = {} # limits in excluded/non-exluded, interpolated
##	copyh_lims_xs    = {} # limits in cross-section, interpolated
##
##	for lim in limits:
##		copyh_lims_mu0[lim] = copyTH2(h_lims_mu0[lim], points)
##		copyh_lims_yn0[lim] = copyTH2(h_lims_yn0[lim], points)
##		copyh_lims_xs0[lim] = copyTH2(h_lims_xs0[lim], points)
##		copyh_lims_mu [lim] = copyTH2(h_lims_mu [lim], points)
##		copyh_lims_yn [lim] = copyTH2(h_lims_yn [lim], points)
##		copyh_lims_xs [lim] = copyTH2(h_lims_xs [lim], points)
##	
##	
##	## saving histograms to disk
##	
##	fout = ROOT.TFile(histopath+"/histo_"+str(idx)+".root", "RECREATE")
##	fout.cd()
##	
##	for lim in limits:    
##		copyh_lims_mu0[lim].Write()
##		copyh_lims_xs0[lim].Write()
##		copyh_lims_yn0[lim].Write()
##		copyh_lims_mu [lim].Write()
##		copyh_lims_xs [lim].Write()
##		copyh_lims_yn [lim].Write()
##	
##	fout.Close()
##
##
