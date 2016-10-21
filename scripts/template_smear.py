## mostly based on Bruno's script

import ROOT, sys, os

jobdir      = "[JOBDIR]"
jobid       = "[JOBID]"

histopath   = "[HISTO]" 
smearpath   = "[SMEAR]" 

limits      = ["obs", "exp", "ep1s", "em1s", "ep2s", "em2s", "op1s", "om1s"]

h_lims_mu   = {} # limits in signal-strength, interpolated 
h_lims_mu0  = {} # limits in signal-strength
g2_lims_mu  = {} # TGraph2D limits in signal-strength, automatic interpolation
theGraphs0  = [] # raw graphs
theGraphs1  = [] # smoothed graphs


class Model():
	def __init__(self):
		self.interpol          = float("[MODEL:interpolsize]")
		self.smoothAlgo        = "[MODEL:smoothAlgo]"
		self.preAlgo           = "[MODEL:preAlgo]"
		self.nSmooth           = int("[MODEL:nSmooth]")
		self.cutGraphsX        = float("[MODEL:cutGraphsX]")
		self.cutGraphsY        = float("[MODEL:cutGraphsY]")
		self.basis             = "[MODEL:basis]"
		self.skipContour       = [[MODEL:skipContour]]
		self.skipContourSmooth = [[MODEL:skipContourSmooth]]


class Line():
	def __init__(self, p1, p2):
		self.reset(p1, p2)
	def build(self):
		## s = delta y / delta x
		## d = y1 - (s*x1)
		if (self.x1 - self.x2)==0: 
			self.error = True
			return
		self.s     = float(self.y1 - self.y2)/(self.x1 - self.x2)
		self.d     = self.y1 - (self.s*self.x1)
		self.built = True
	def intersect(self, line):
		## now, f: y(x) = s1*x + d1 and g: y(x) = s2*x + d2
		## find intersection of those lines!
		if not line.built: line.build()
		if self.error or line.error: return (-1, -1) 
		if self.s - line.s == 0    : return (-1, -1)
		x = float(line.d - self.d)/(self.s - line.s)
		y = self.s * x + self.d
		return (x,y)	
	def reset(self, p1, p2):
		self.x1    = p1[0]
		self.x2    = p2[0]
		self.y1    = p1[1]
		self.y2    = p2[1]
		self.built = False
		self.error = False
		self.build()

class Graph():
	def __init__(self, tgraph):
		self.g = tgraph
		self.orientate()
		self.load()
	def addBack(self, p):
		self.points = self.points + [p]
		self.rebuild()
	def addFront(self, p):
		self.points = [p] + self.points
		self.rebuild()
	def addGraph(self, graph):
		self.points = self.points + graph.points
		self.rebuild()
	def between(self, p, p1, p2):
		if p1[0] <= p[0] <= p2[0] and p1[1] <= p[1] <= p2[1]: return True
		if p2[0] <= p[0] <= p1[0] and p2[1] <= p[1] <= p1[1]: return True
		return False
	def cutX(self, cutValue):
		if not self.g or cutValue <= 0: return
		thePoints = []
		for p in self.points:
			if p[0] < cutValue:
				thePoints.append(p)
		del self.points
		self.points = thePoints
		self.rebuild()
	def cutY(self, cutValue):
		if not self.g or cutValue <= 0: return
		thePoints = []
		for p in self.points:
			if p[1] < cutValue:
				thePoints.append(p)
		del self.points
		self.points = thePoints
		self.rebuild()
	def getFirstLine(self):
		return self.getLine(0,1)
	def getLastLine(self):
		return self.getLine(len(self.points)-1,len(self.points)-2)
	def getLine(self, p1, p2):
		if not hasattr(self, "line"): 
			self.line = Line(self.points[p1], self.points[p2])
		else:
			self.line.reset(self.points[p1], self.points[p2])
		return self.line
	def getNearbyPoint(self, p):
		## returns the point that comes right AFTER this point on the graph
		for i in range(1,len(self.points)):
			p1 = self.getPoint(i  )
			p2 = self.getPoint(i-1)
			if self.between(p, p1, p2): return i
		return -1
	def getPoint(self, pidx = 0):
		return self.points[pidx]
	def interpolate(self, graph):
		line1 = self.getLastLine ()
		line2 = self.getFirstLine()
		return line1.intersect(line2)
	def intersect(self, theGraph):
		for iidx1 in range(1,len(self.points)):
			line1 = self.getLine(iidx1,iidx1-1)
			for iidx2 in range(1,len(theGraph.points)):
				line2 = theGraph.getLine(iidx2, iidx2-1)
				ip    = line1.intersect(line2)
				if self.isOnGraph(ip) and theGraph.isOnGraph(ip):
					return ip
		return (-1, -1)
	def isOnGraph(self, p):
		if p == (-1, -1): return False
		return (self.getNearbyPoint(p) > -1)
	def isPoint(self, x, y):
		return ((x,y) in self.points)
	def load(self):
		if not self.g: return
		self.points = []
		for ipoint in range(self.g.GetN()):
			self.points.append((self.g.GetX()[ipoint], self.g.GetY()[ipoint]))
	def orientate(self):
		if not self.g: return
		self.load() ## get points
		if len(self.points) <= 1 : return
		if self.testOrientation(): return
		self.points.reverse()
		self.rebuild()
	def rebuild(self):
		for	i in range(self.g.GetN()):
			self.g.RemovePoint(i)
		for i,p in enumerate(self.points):
			self.g.SetPoint(i, p[0], p[1])
	def removeBack(self, ip):
		## remove points at the end, the point itself is also removed
		if ip == -1: return
		self.points = self.points[:ip]
		self.rebuild()
	def removeFront(self, ip):
		## remove points in front, the point itself stays
		if ip == -1: return
		self.points = self.points[ip:]
		self.rebuild()
	def testOrientation(self, i1 = -1, i2 = -1):
		if i1==-1 and i2==-1: 
			i1 = 0
			i2 = self.g.GetN()-1
		if i1 > i2:
			i2b = i2
			i2 = i1
			i1 = i2b
		if i2 >= len(self.points): return True
		return (self.points[i1][0] < self.points[i2][0] or self.points[i1][1] > self.points[i2][1])


def makeInterpolation(trigger, graph1, graph2):
	if trigger: return False
	p = graph1.interpolate(graph2)
	if p != (-1, -1): 
		graph1.addBack (p)
		graph2.addFront(p)
		return True
	return False

def makeIntersection(trigger, graph1, graph2):
	if not trigger: return False
	p = graph1.intersect(graph2)
	if p != (-1, -1):
		graph1.removeBack (graph1.getNearbyPoint(p))
		graph2.removeFront(graph2.getNearbyPoint(p))
		graph1.addBack (p)
		graph2.addFront(p)
		return True
	return False

def connectGraphs(graph1, graph2):
	if not graph1 or not graph2: return
	r = makeIntersection (True, graph1, graph2) 
	# calls below are not necessary since orientation and mergeGraphs does the job 
	#r = makeInterpolation(r   , graph1, graph2)
	#r = makeIntersection (r   , graph1, graph2) 
		
def mergeGraphs(graphlist, lim):
	TG = graphlist[0][lim].g.Clone()
	GR = Graph(TG)
	for i in range(1,len(files)):
		GR.addGraph(graphlist[i][lim])
	return GR

def firstFilledBinY(theHist, ix, fromTop = True):
	theRange = range(theHist.GetNbinsY(),0,-1) if fromTop else range(1,theHist.GetNbinsY()+1)
	for iy in theRange:
		if theHist.GetBinContent(ix,iy)!=0:
			return iy
	return -1

def fillFromBottom(check, hist, ix, value = None):
	## in addition to the filling from bottom it also fills the entire y if value is not None
	iy      = firstFilledBinY(check, ix, False)
	if iy == -1 and not value: return
	if iy == -1 : theRange = range(1,hist.GetNbinsY()+1)
	else        : theRange = range(1,iy)
	if not value: value    = hist.GetBinContent(ix, iy)
	for iyy in theRange:
		hist.SetBinContent(ix, iyy, value)

def fillFromTop(check, hist, ix, value = None):
	iy = firstFilledBinY(check, ix, True)
	if not value: value = hist.GetBinContent(ix, iy)
	if iy > -1:
		for iyy in range(iy+1, hist.GetNbinsY()+1):
			hist.SetBinContent(ix, iyy, value)

def extractSmoothedContour(model, hist, idx):
	## if name contains "mu" histogram is signal strenght limit, otherwise it's a Yes/No limit
	isMu = "mu" in hist.GetName()
	shist = hist.Clone(hist.GetName()+"_smoothed")
	
	## if smoothing a limit from mu, we need to modify the zeros outside the diagonal, 
	## otherwise the smoothing fools us in the diagonal transition
	if isMu:
		for ix in range(1, shist.GetNbinsX()+1):
			fillFromTop   (hist, shist, ix)
			fillFromBottom(hist, shist, ix)


	## smooth the histogram
	if model.preAlgo: shist.Smooth(1,model.preAlgo)
	for s in range(model.nSmooth):
		if not model.smoothAlgo: shist.Smooth()
		else                   : shist.Smooth(1,model.smoothAlgo)

	## after smoothing a limit from mu, we need to modify the zeros outside the diagonal, 
	## otherwise the contours come wrong for the diagonal
	if isMu:
		for ix in range(1, shist.GetNbinsX()+1):
			fillFromTop   (hist, shist, ix, 1.1)
			fillFromBottom(hist, shist, ix, 1.1)

	###f = ROOT.TFile("hehehe"+idx+".root","recreate")
	###f.cd()
	###shist.Write()
	###f.Close()
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
	graph = None
	max_points = -1
	for l in range(list.GetSize()):
		gr = list.At(l).Clone()
		n_points = gr.GetN()
		if n_points > max_points:
			graph = gr
			max_points = n_points
	if not graph: return None
	name = "gr_"+shist.GetName()
	graph.SetName(name)
	graph.Draw("sameC")
	del canvas
	del shist
	del obj
	del list
	return graph

##def insertPointInFront(graph, x, y):
##	for i in reversed(range(graph.GetN())):
##		graph.SetPoint(i+1, graph.GetX()[i], graph.GetY()[i])
##	graph.SetPoint(0, x, y)
##	return graph
##
##def getFirstTwoPoints(graph):
##	return getPoint(graph, 1), getPoint(graph, 0)
##
##def getLastTwoPoints(graph):
##	return getPoint(graph, graph.GetN()-1), getPoint(graph, graph.GetN()-2)
##
##def getPoint(graph, pidx = 1):
##	return graph.GetX()[pidx], graph.GetY()[pidx]
##
##def getLinearParams(twoPoints):
##	## s = delta y / delta x
##	## d = y1 - (s*x1)
##	s = float(twoPoints[0][1] - twoPoints[1][1])/(twoPoints[0][0] - twoPoints[1][0])
##	d = twoPoints[0][1] - (s*twoPoints[0][0])
##	return s, d
##
##def intersection(points1, points2):
##	s1, d1 = getLinearParams(points1)
##	s2, d2 = getLinearParams(points2)
##	## now, f: y(x) = s1*x + d1 and g: y(x) = s2*x + d2
##	## find intersection of those lines!
##	x = float(d2-d1)/(s1-s2)
##	y = s1*x+d1
##	return x,y 
##
##def findGraphIntersect(graph1, graph2):
##	for i in range(1,graph1.GetN()):
##		p1, p2 = getPoint(graph1, i), getPoint(graph1, i-1)
##		for j in range(1,graph2.GetN()):
##			p3, p4 = getPoint(graph2, j), getPoint(graph2, j-1)
##			x,y    = intersection([p1, p2], [p3, p4])
##			if betweenPoints((x,y), p1, p2) and betweenPoints((x,y), p3, p4):
##				return x,y
##	return -1, -1
##
##def betweenPoints(thePoint, lower, upper):
##	if lower[0] <= thePoint[0] <= upper[0] and lower[1] <= thePoint[1] <= upper[1]: return True
##	return False
##
##def isPoint(graph, xpos, ypos):
##	points = []
##	for x in graph.GetX():
##		for y in graph.GetY():
##			points.append((x,y))
##	return ((xpos,ypos) in points)
##
##def findPoint(graph, x, y):
##	for i in range(1,graph.GetN()):
##		x1, y1 = getPoint(graph, i-1)
##		x2, y2 = getPoint(graph, i  )
##		if betweenPoints((x,y), (x1,y1), (x2, y2)):
##			return i
##	return -1
##
##def removePointsBefore(graph, nPoint):
##	## the point itself stays
##	if nPoint==-1: return graph
##	for i in range(0,nPoint):
##		graph.RemovePoint(i)
##	return graph
##
##def removePointsAfter(graph, nPoint):
##	## the point itself is also removed
##	if nPoint==-1: return graph
##	for i in range(nPoint,graph.GetN()):
##		graph.RemovePoint(i)
##	return graph
##
##def makeInterpolation(trigger, graph1, graph2):
##	## fixme: first find direction, then do insert and picking points accordingly
##	if trigger: return graph1, graph2, False
##	p1, p2 = getLastTwoPoints(graph1)
##	p3, p4 = getLastTwoPoints(graph2)
##	x, y   = intersection([p1, p2], [p3, p4])
##	#graph1 = insertPointInFront(graph1, x, y)
##	graph1.SetPoint(graph1.GetN(), x, y)
##	graph2.SetPoint(graph2.GetN(), x, y)
##	return graph1, graph2, True
##
##def makeIntersection(trigger, graph1, graph2):
##	if not trigger: return graph1, graph2, False
##	ix, iy = findGraphIntersect(graph1, graph2)
##	if ix > -1 and iy > -1:
##		print "found intersection at "+str(ix)+" "+str(iy)
##		print "corresponding to point "+str(findPoint(graph1, ix, iy))+" of "+str(graph1.GetN())+" in graph 1"
##		print "corresponding to point "+str(findPoint(graph2, ix, iy))+" of "+str(graph2.GetN())+" in graph 2"
##		graph1 = removePointsAfter(graph1, findPoint(graph1, ix, iy))
##		graph2 = removePointsAfter (graph2, findPoint(graph2, ix, iy))
##		##if not isPoint(graph1, ix, iy):
##		##	#graph1 = insertPointInFront(graph1, ix, iy)
##		##	graph1.SetPoint(graph1.GetN(), ix, iy)
##		##if not isPoint(graph2, ix, iy):
##		##	graph2.SetPoint(graph2.GetN(), ix, iy)
##		return graph1, graph2, True
##	return graph1, graph2, False
##
##def connectGraphs(graph1, graph2):
##	graph1, graph2, r = makeIntersection (True, graph1, graph2) 
##	graph1, graph2, r = makeInterpolation(r   , graph1, graph2) 
##	graph1, graph2, r = makeIntersection (r   , graph1, graph2) 
##	return graph1, graph2

## get the model information

model = Model()


## get list of points

files = []
for f in os.listdir(histopath):
	if f.find("histo_")==-1 or f.find(".root")==-1: continue
	if f.find("HADD")>-1: continue
	files.append(f)

files.sort()


## separate smoothing for every region

for f in files:

	idx     = f.rstrip(".root").lstrip("histo_")
	graphs0 = {} # raw graph
	graphs1 = {} # smoothed graph


	## read histos from file
	fin = ROOT.TFile(histopath+"/"+f, "READ")
	for lim in limits:
		h_lims_mu [lim] = fin.Get(lim+"_mu") ; h_lims_mu [lim].SetDirectory(0)
		h_lims_mu0[lim] = fin.Get(lim+"_mu0"); h_lims_mu0[lim].SetDirectory(0)
		# unfortunately, we need to redo the TGraph2D
		g2_lims_mu[lim] = ROOT.TGraph2D(h_lims_mu0[lim] if model.basis == "mu0" else h_lims_mu[lim])
		g2_lims_mu[lim].SetName("g2_"+lim+"_mu0")
		g2_lims_mu[lim].SetNpx( int((g2_lims_mu[lim].GetXmax()-g2_lims_mu[lim].GetXmin())/model.interpol) )
		g2_lims_mu[lim].SetNpy( int((g2_lims_mu[lim].GetYmax()-g2_lims_mu[lim].GetYmin())/model.interpol) )
		g2_lims_mu[lim].GetHistogram()
	
	
	## get contour list
	for lim in limits:
		theGraph = None
		if not lim in model.skipContour: 
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
					theGraph = gr
					max_points = n_points
		if theGraph:
			theGraph.SetName("gr_"+lim)
		graphs0[lim] = Graph(theGraph)
		graphs0[lim].cutX(model.cutGraphsX)
		graphs0[lim].cutY(model.cutGraphsY)
	theGraphs0.append(graphs0)
	
	
	## smoothing the contour list
	    
	for lim in limits:
		theGraph = None
		if not lim in model.skipContourSmooth: 
			theGraph = extractSmoothedContour(model, h_lims_mu[lim], idx)
		if theGraph: 
			theGraph.SetName( theGraph.GetName().replace("_mu", "") )
		graphs1[lim] = Graph(theGraph)
		graphs1[lim].cutX(model.cutGraphsX)
		graphs1[lim].cutY(model.cutGraphsY)
	theGraphs1.append(graphs1)

	fin.Close()


## prepare graphs for HADDing, either: (1) add a few points via linear interpolation
## or (2) remove unnecessary points if an intersection of the graphs is found
for i,f in enumerate(files):
	if i == 0: continue
	for lim in limits:
		connectGraphs(theGraphs0[i-1][lim], theGraphs0[i][lim])
		connectGraphs(theGraphs1[i-1][lim], theGraphs1[i][lim])


## saving all to the files
for i,f in enumerate(files):

	idx = f.rstrip(".root").lstrip("histo_")

	fout = ROOT.TFile(smearpath+"/smear_"+idx+".root", "RECREATE")
	for lim in limits:
		if theGraphs0[i][lim].g: theGraphs0[i][lim].g.Write()
		if theGraphs1[i][lim].g: theGraphs1[i][lim].g.Write()
	fout.Close()


## merge the individual graphs
if len(files) > 1:
	fout = ROOT.TFile(smearpath+"/smear_HADD.root", "RECREATE")
	for lim in limits:
		merged0 = mergeGraphs(theGraphs0, lim)
		merged1 = mergeGraphs(theGraphs1, lim)
		merged0.g.Write()
		merged1.g.Write()
	fout.Close()
else:
	print "cp "+smearpath+"/smear_0.root "+smearpath+"/smear_HADD.root"
	os.system("cp "+smearpath+"/smear_0.root "+smearpath+"/smear_HADD.root")

