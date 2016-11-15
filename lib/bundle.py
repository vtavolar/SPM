import ROOT, os
from init import *
from functions import *

class Mode():
	def __init__(self, name):
		self.name = name
		self.limitCmd = "-M Asymptotic"
		if self.name == "sens":
			self.limitCmd = "-M ProfileLikelihood  --uncapped 1 --significance -rMin -5"
		elif self.name == "braz":
			self.limitCmd = ""

class Bundle():
	def __init__(self, master, name, packages = []):
		self.status     = "init"
		self.master     = master
		self.base       = self.master.bundledir
		self.name       = name
		self.dir        = self.base +"/"+ self.name
		self.srcdir     = self.dir  +"/src"
		self.logdir     = self.dir  +"/log"
		self.cardsdir   = self.dir  +"/cards"
		self.limitsdir  = self.dir  +"/limits"
		self.summarydir = self.dir  +"/summary"
		self.histodir   = self.dir  +"/histo"
		self.smeardir   = self.dir  +"/smear"
		self.plotdir    = self.dir  +"/plot"
		self.inspectdir = self.dir  +"/inspect"
		self.pool       = self.master.pool
		self.packages   = packages
		self.points     = []
		if not self.load():
			self.mode     = self.master.mode
			self.modeinst = Mode(self.master.mode)
	def selectPoints(self):
		self.points = []
		for point in self.packages[0].points:
			inAll = True
			for p in range(1,len(self.packages)):
				if not point in self.packages[p].points:
					inAll = False
			if inAll: self.points.append(point)
	def build(self):
		## doing the combination and writing init
		self.combine()
		self.limits()
		self.summary()
		self.histo()
		self.smear()
		self.plot()
		self.publish()
	def combine(self):
		if "combine" in self.master.options.excludeTiers: return
		if not "combine" in self.master.options.redoTiers and self.status in ["combine","limits","summary","histo","smear","plot"]: return
		self.master.clearJobs()
		self.master.tier("combine")
		cleandir(self.master, self.cardsdir)
		if len(self.packages)==1:
			self.combineTrivial()
		else:
			for point in self.points:
				self.combineCards(point)
			self.master.runJobs()
			self.master.clearJobs()
		self.init.update("status", "combine")
		self.inspect("combine")
	def combineTrivial(self):
		for point in self.points:
			cp(self.master, self.packages[0].cardsdir+"/"+point+".txt", self.cardsdir)
	def combineCards(self, point):
		if point.strip()=="": return
		self.master.registerJob(self, "combine_"+point, "combine.sh", {"packages": [p.name for p in self.packages], "card": point+".txt"}, False, 20)
	def create(self, packages = []):
		if len(self.packages)==0: self.master.error("I cannot create the bundle '"+self.name+"' without any packages!")
		self.selectPoints()
		if not self.isGood()    : self.master.error("I cannot combine the packages for bundle '"+self.name+"'")
		self.model   = self.packages[0].model
		self.master.talkBundle(self)
		self.lumis   = [p.lumi   for p in self.packages]
		self.regions = [p.region for p in self.packages]
		mkdir(self.master, self.dir)
		mkdir(self.master, self.srcdir)
		mkdir(self.master, self.logdir)
		mkdir(self.master, self.cardsdir)
		mkdir(self.master, self.limitsdir)
		mkdir(self.master, self.summarydir)
		mkdir(self.master, self.histodir)
		mkdir(self.master, self.smeardir)
		mkdir(self.master, self.plotdir)
		mkdir(self.master, self.inspectdir)
		self.register()
		self.build()
	def getTuningOptions(self, tier, modeloptions, additionals = {}):
		opts = additionals
		for opt in modeloptions:
			opts[opt] = self.master.getModelParam(opt)
		self.master.talk("Enter the name of the parameter you want to tune for tier '"+tier+"' or enter 'q' to continue with the next tier:")
		maxLength = max([len(k) for k in opts.keys()])
		self.master.addToTalk("  name"+" "*(maxLength-4)+" = value")
		for k,v in opts.iteritems():
			self.master.addToTalk("  "+k+" "*(maxLength-len(k)) +" = "+v)
		chosen = raw_input(">> ").strip()
		if chosen == "q": return False
		if not chosen in opts.keys():
			self.master.addToTalk("The parameter '"+chosen+"' does not exist. Try again:")
			return self.getTuningOptions(tier, modeloptions, additionals)
		value = askForInput(self.master, "Give the new value to use for parameter '"+chosen+"':")
		setattr(self.master.options, chosen, value) 
		return True
	def histo(self):
		## make the histograms and interpolate them
		if "histo" in self.master.options.excludeTiers: return
		if self.master.options.stopAtTier in ["combine", "limits", "summary"]: return
		if not "histo" in self.master.options.redoTiers and self.status in ["histo","smear","plot"]: return
		self.master.tier("histo")
		cleandir(self.master, self.histodir)
		self.master.runJob(self, "histo", "histo.py", {}, not self.master.options.qall)
		self.init.update("status", "histo")
		if self.inspect("histo"): self.histo()
	def inspect(self, tier):
		if not self.master.options.inspect: return False
		if tier in ["limits"]: return False
		if self.master.options.queue and tier in ["combine"]: return False
		if self.master.options.queue and self.master.options.qall and tier in ["summary","histo","smear","plot"]: return False
		return eval("self.inspect"+tier.title()+"()")
	def inspectCombine(self, cardIdx = 0):
		self.master.talk("Inspecting COMBINE:")
		cards = os.listdir(self.cardsdir)
		cards = filter(lambda x: x.find(".txt")>-1, cards)
		if cardIdx>= 0 and cardIdx < len(cards):
			self.master.talk("Inspecting card "+str(cardIdx)+"/"+str(len(cards))+":")
			self.master.addToTalk("".join(open(cards[cardIdx],"r").readlines()))
			newId = askForInput(self.master, "Give the index of the next card to inspect or enter 'q' to continue:")
			if newId.isdigit(): self.inspectCombine(int(newId))
		return False
	def inspectHisto(self, histIdx = 0):
		self.master.talk("Inspecting HISTO (enter 'edit' to tune parameters of this tier):")
		newId = self.inspectRoot(self.histodir+"/histo_HADD.root", histIdx)
		while newId.isdigit():
			newId = self.inspectRoot(self.histodir+"/histo_HADD.root", int(newId))
		if newId == "edit": return self.tuneHisto()
		return False
	def inspectLimit(self, mass1 = "", mass2 = ""):
		theFile   = open(self.summarydir+"/summary","r")
		theLimits = theFile.readlines()
		theFile.close()
		theFilter = ""
		if mass1 and     mass2: theFilter = mass1+" : "+mass2+" : "
		if mass1 and not mass2: theFilter = mass1+" : "
		if theFilter:
			theLimits = filter(lambda entry: entry[0:len(theFilter)]==theFilter, theLimits)
		self.master.addToTalk("".join(theLimits))
		newMass = askForInput(self.master, "Give the mass of particle 1 or the mass of both particles (separated by a '+') for which you want to inspect the limit. Or enter 'q' to continue:")
		if   newMass.isdigit(): self.inspectLimit(newMass)
		elif "+" in newMass   : self.inspectLimit(newMass.split("+")[0].strip(), newMass.split("+")[1].strip())
	def inspectPlot(self, histIdx = 0):
		self.master.talk("Inspecting PLOT (enter 'edit' to tune parameters of this tier):")
		if os.path.exists(self.plotdir+"/plot.pdf"):
			cmd(self.master, "display "+self.plotdir+"/plot.pdf &")
		elif os.path.exists(self.plotdir+"/plot.png"):
			cmd(self.master, "display "+self.plotdir+"/plot.png &")
		else:
			return
		newId = askForInput(self.master, "Enter 'q' to continue:")
		if newId == "edit": return self.tunePlot()
		return False
	def inspectRoot(self, path, histIdx = 0):
		c = ROOT.TCanvas("c","c",300,300)
		f = ROOT.TFile.Open(path, "read")
		f.cd()
		it = -1
		listOfKeys = ROOT.gDirectory.GetListOfKeys()
		if len(listOfKeys)==0: return
		for key in listOfKeys:
			it += 1
			if not it == histIdx: continue
			hist = key.ReadObj(); name = hist.GetName()
		if   "TGraph" in hist.ClassName(): hist.Draw("C"   )
		elif hist.GetDimension()==2      : hist.Draw("COLZ")
		else                             : hist.Draw("hist")
		self.master.addToTalk("ID : Name of TObject")
		self.master.addToTalk("\n".join(["%s : %s"%(idString(i,2,True),key.ReadObj().GetName()) for i,key in enumerate(listOfKeys)]))
		self.master.addToTalk("Inspecting TObject '"+name+"'")
		if not os.path.exists(self.inspectdir+"/"+name+".png"):
			c.SaveAs(self.inspectdir+"/"+name+".png")
		cmd(self.master, "display "+self.inspectdir+"/"+name+".png &")
		f.Close()
		newId = askForInput(self.master, "Give the index of the next histogram or graph to inspect or enter 'edit' to tune the parameters of this tier or 'q' to continue to the next tier:")
		return newId
	def inspectSmear(self, histIdx = 0):
		self.master.talk("Inspecting SMEAR (enter 'edit' to tune parameters of this tier):")
		newId = self.inspectRoot(self.smeardir+"/smear_HADD.root", histIdx)
		while newId.isdigit():
			newId = self.inspectRoot(self.smeardir+"/smear_HADD.root", int(newId))
		if newId=="edit"  : return self.tuneSmear()
		return False
	def inspectSummary(self):
		self.master.talk("Inspecting SUMMARY:")
		self.inspectLimit()
		return False
	def isGood(self):
		if len(self.packages)==0 or len(self.points)==0                   : return False
		if any([not p.state                       for p in self.packages]): return False
		if not self.packages[0].model                                     : return False
		if any([p.model != self.packages[0].model for p in self.packages]): return False 
		return self.packages
	def limits(self):
		## execute the limit jobs per card
		if "limits" in self.master.options.excludeTiers: return
		if self.master.options.stopAtTier in ["combine"]: return
		if not "limits" in self.master.options.redoTiers and self.status in ["limits","summary","histo","smear","plot"]: return
		self.master.tier("limits")
		cleandir(self.master, self.limitsdir)
		for point in self.points:
			self.runLimit(point)
		self.master.runJobs()	
		self.master.clearJobs()
		self.init.update("status", "limits")
	def load(self):
		if not os.path.exists(self.dir +"/init"): return False
		if hasattr(self, "init"): return False
		self.init = Init(self, self.dir+"/init")
		self.updatePackages()
		return True
		#if self.init.read("packages").find(",")>-1: ps = self.packages
		#else: ps = [self.packages]
		#del self.packages
		#self.packages = [self.pool.getPackage(p.strip()) for p in ps]
	def plot(self):
		## draw the final plot
		if "plot" in self.master.options.excludeTiers: return
		if self.master.options.stopAtTier in ["combine", "limits", "summary", "histo", "smear"]: return
		if not "plot" in self.master.options.redoTiers and self.status in ["plot"]: return
		self.master.tier("plot")
		cleandir(self.master, self.plotdir)
		self.master.runJob(self, "plot", "plot.py", {}, not self.master.options.qall)
		self.init.update("status", "plot")
		if self.inspect("plot"): self.plot()
	def publish(self):
		if not self.master.options.publdir: return
		self.mkdir(self.master, self.master.options.publdir, True)
		for ext in self.master.options.plotExt.split(","):
			cp(self.master, self.plotdir+"/plot."+ext, self.master.options.publdir)
	def register(self):
		if hasattr(self, "init"): return
		self.init = Init(self, self.dir +"/init") 
		self.init.write({"model"   : self.master.model.name, \
		                 "mode"    : self.mode, \
		                 "lumis"   : ",".join(self.lumis), \
		                 "regions" : ",".join(self.regions), \
		                 "packages": ",".join([p.name for p in self.packages]), \
		                 "points"  : ",".join(self.points), \
		                 "status"  : getattr(self, "status", "init"), \
		                 "remark"  : self.master.options.remark if self.master.options.remark else ""})
		self.updatePackages()
	def tuneHisto(self):
		return self.getTuningOptions("histo", ["histoDeltaM", "interpolsize", "paramX", "paramY", "binningX", "binningY"])
	def tunePlot(self):
		return self.getTuningOptions("plot" , ["noNllNlo", "rangeX", "rangeY", "rangeZ", "nDivX", "nDivY", "plane", "smoothCont", "legendX", "legendY", "gr_obs", "gr_op1s", "gr_om1s", "gr_exp", "gr_ep1s", "gr_em1s", "cutGraphsX", "cutGraphsY", "text", "diag"])
	def tuneSmear(self):
		return self.getTuningOptions("smear", ["preAlgo", "smoothAlgo", "nSmooth", "skipContour", "skipContourSmooth", "basis"])
	def runLimit(self, point):
		if not point: return
		self.master.registerJob(self, "limit_"+point, "limit.sh", {"card": point+".txt", "mass1": point.split("_")[0], "mass2": point.split("_")[1]},False,3)
	def selectGoodMasspoints(self):
		self.points = []
		masspoints  = []
		for p in self.packages: 
			for pp in p.points:
				if not pp in masspoints: 
					masspoints.append(pp)
		for pp in masspoints:
			if all([pp in p.points for p in self.packages]):
				self.points.append(pp)
	def smear(self):
		## add the smoothed graphs to the histograms
		if self.mode == "sens": return
		if "smear" in self.master.options.excludeTiers: return
		if self.master.options.stopAtTier in ["combine", "limits", "summary", "histo"]: return
		if not "smear" in self.master.options.redoTiers and self.status in ["smear", "plot"]: return
		self.master.tier("smear")
		cleandir(self.master, self.smeardir)
		self.master.runJob(self, "smear", "smear.py", {}, not self.master.options.qall)
		self.init.update("status", "smear")
		if self.inspect("smear"): self.smear()
	def summary(self):
		## get the summary of all the limits
		if "summary" in self.master.options.excludeTiers: return
		if self.master.options.stopAtTier in ["combine", "limits"]: return
		if not "summary" in self.master.options.redoTiers and self.status in ["summary","histo","smear","plot"]: return
		self.master.tier("summary")
		cleandir(self.master, self.summarydir)
		self.master.runJob(self, "summary", "summary.py", {}, not self.master.options.qall)
		self.init.update("status", "summary")
		self.inspect("summary")
	def updatePackages(self):
		if isinstance(self.packages, basestring): self.packages = [self.packages]
		if len(self.packages)==0: return
		if hasattr(self.packages[0],"name"): return
		ps = self.packages
		del self.packages
		self.packages = [self.pool.getPackage(p.strip()) for p in ps]


class BundleHandler():
	def __init__(self, master):
		self.master    = master
		self.bundledir = master.bundledir
		self.bundles   = []
		self.pool      = master.pool
		self.loadBundles()
		if self.master.options.view: self.view()
	def addPackages(self, goodPackages):
		remaining = [p for p in goodPackages if not p in self.master.options.addPackages]
		for p in goodPackages:
			packages = remaining + [p]
			self.runBundle(packages)
	def findBundleByName(self, bname):
		for b in self.bundles:
			if b.name == bname:
				return b
		return None
	def collectBundles(self):
		## create the list of all bundles to run
		if self.master.options.bundle: 
			self.bundlesToRun = filter(lambda x: x, [self.findBundleByName(self.master.options.bundle.strip())])
			return
		self.bundlesToRun = []
		available         = self.pool.getListOfPackages()
		if len(available) == 0: return
		if   len(self.master.options.cmbLumis   )>0: self.combLumis  (available)
		elif len(self.master.options.cmbRegions )>0: self.combRegions(available)
		elif len(self.master.options.addPackages)>0: self.addPackages(available)
		else                                       : self.manualComb (available)
	def combLumis(self, goodPackages):
		regions = [p.region for p in goodPackages]
		for r in regions:
			packages = []
			for p in goodPackages:
				if not p.region in [r]: continue
				if not p.lumi   in [self.master.options.cmbLumis]: continue
				packages.append(p)
			self.runBundle(packages)
	def combRegions(self, goodPackages):
		lumis = [p.lumis for p in goodPackages]
		for l in lumis:
			packages = []
			for p in goodPackages:
				if not p.lumi   in [l]: continue
				if not p.region in [self.master.options.cmbRegions]: continue
				packages.append(p)
			self.runBundle(package)
	def deleteBundle(self, bundle):
		rm(self.bundledir+"/"+bundle.name)
		if bundle in self.bundles: self.bundles.remove(bundle)
		del bundle
	def deleteBundleByName(self, bname):
		found = self.findBundleByName(bname)
		if not found: return
		self.deleteBundle(found)
	def findPackageByName(self, pname):
		bnames = [b.name for b in self.bundles]
		if bname in bnames:
			return self.bundles[bnames.index(bname)]
		return None
	def loadBundles(self):
		for bname in os.listdir(self.bundledir):
			if not os.path.isdir(self.bundledir+"/"+bname): continue
			self.bundles.append(Bundle(self.master, bname))
	def manualComb(self, goodPackages):
		if len(goodPackages)>100: 
			self.master.error("Too many packages in the pool. Please remove at least "+str(len(goodPackages)-100))
		self.master.talk("Doing manual combination.")
		self.master.addToTalk("Please select manually the packages you wish to combine for this bundle.")
		self.master.addToTalk("Below you find a list of all available and good packages that can be combined.")
		self.pool.view(goodPackages, False)
		ids = askForInput(self.master, "Please give a list (separated by the + symbol) of package IDs you wish to combine:")
		goodIds = [int(i.strip()) for i in ids.split("+")]
		packages = [p for i, p in enumerate(goodPackages) if i in goodIds]
		self.runBundle(packages)
	def runBundle(self, packages):
		# first: check if bundle exists, if so add it to the good list of bundles
		# if not, create the bundle
		# do build for all bundles
		theBundle = None
		for b in self.bundles:
			if b.packages == packages and b.mode == self.master.mode:
				theBundle = b
		if not theBundle:
			bname = timestamp(False)
			self.bundles.append(Bundle(self.master, bname, packages))
			theBundle = self.bundles[-1]
		self.bundlesToRun.append(theBundle)
	def runBundles(self):
		if not hasattr(self, "bundlesToRun"): return
		for b in self.bundlesToRun:
			b.create()
	def view(self, bundles = [], showDiff = False):
		if len(bundles)==0: bundles = self.bundles #self.getListOfBundles()
		if len(bundles)==0: return
		self.master.talk("Viewing content of the bundledir:")	
		self.master.addToTalk("ID : Name               : Model                : Packages")
		for i,b in enumerate(bundles):
			if not b: continue
			self.master.addToTalk("%s : %s : %s : %s"%(idString(i,2,True),b.name,idString(b.model,20),",".join([p.name for p in b.packages])))
		if not showDiff: return
		remaining = filter(lambda b: b not in bundles, self.bundles)
		if len(remaining)==0: return
		self.master.talk("Following bundles are also present, but cannot be used:")
		self.master.addToTalk(", ".join([b.name for b in remaining]))
		if askForInput(self.master, "Do you want to remove these faulty bundles?", ["y", "n"])=="y":
			theNames = [p.name for p in remaining]
			del remaining # delete any list that contains the pointer before deleting the object
			for name in theNames:
				self.deleteBundleByName(name)




