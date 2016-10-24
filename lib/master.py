import os, time
from functions import *
from custom import *
from bundle import *
from pool import *
from job import *

class SPM():
	def __init__(self, args, options):
		self.options   = options
		self.verbosity = options.verbosity
		self.talkStart()
		self.dir       = os.getcwd()
		self.models    = Collection(self.dir +"/env/models")
		self.model     = self.models.get(args[0])
		self.model.fillDefaults("model")
		self.srcdir    = self.dir +"/scripts"
		self.tmpdir    = self.dir +"/tmp"
		self.jobdir    = self.tmpdir +"/jobcontrol"
		self.pooldir   = self.tmpdir +"/pool"
		self.bundledir = self.tmpdir +"/bundle"
		mkdir(self, self.tmpdir   )
		mkdir(self, self.jobdir   )
		mkdir(self, self.pooldir  )
		mkdir(self, self.bundledir)
		self.loadInit()
		self.checkCMSSW()
		self.pool      = PoolHandler(self)
		self.bundles   = BundleHandler(self)
		self.bundles.collectBundles()
		self.bundles.runBundles()
	def addToTalk(self, message):
		print message # reserved for later log-file treatment?
	def askForCMSSW(self):
		cmssw = raw_input(">> ")
		cmssw = cmssw.rstrip("/")
		if cmssw[cmssw.rfind("/")+1:] != "src":
			self.talk("Please give the path to the SRC directory of your CMSSW environment")
			return self.askForCMSSW()
		if not os.access(cmssw, os.W_OK):
			self.talk("Please give a WRITABLE CMSSW src directory")
			return self.askForCMSSW()
		return cmssw
	def checkCMSSW(self):
		if not hasattr(self, "cmssw") or not self.cmssw or self.cmssw[self.cmssw.rfind("/")+1:] != "src" or not os.access(self.cmssw, os.W_OK):
			self.talk("I cannot write to CMSSW installation directory '"+getattr(self,"cmssw","")+"'\nPlease give the path to the writable CMSSW environment (src directory) where HiggsCombined is installed\nWhen running SPM, it will create a sub-directory 'SPM' within the src directory of your CMSSW environment")
			self.cmssw = self.askForCMSSW()
			mkdir(self, self.cmssw +"/SPM")
			self.init.update("cmssw", self.cmssw)
	def clearJobs(self):
		if hasattr(self, "jobs") and len(self.jobs)>0: 
			njobs = [j.isDone() or j.isError() for j in self.jobs].count(False)
			while njobs > 0:
				nerr = [j.isError() for j in self.jobs].count(True)
				self.talk(str(njobs)+"/"+str(len(self.jobs))+" jobs are running. Checking back in 5 seconds...")
				time.sleep(5)
				njobs = [j.isDone() or j.isError() for j in self.jobs].count(False)
			nerr = [j.isError() for j in self.jobs].count(True)
			if nerr>0:
				self.error(str(nerr)+"/"+str(len(self.jobs))+" jobs have finished in error state.")
		self.jobs = []
		self.jobcount = -1
		cleandir(self, self.jobdir)
		cleandir(self, self.cmssw +"/SPM")
	def error(self, message):
		self.talk(message, True)
	def getModelParam(self, attr):
		if hasattr(self.options, attr) and getattr(self.options, attr):
			return getattr(self.options, attr, "")
		if isinstance(getattr(self.model, attr),(int,float)):
			return str(getattr(self.model, attr))
		elif isinstance(getattr(self.model, attr),basestring):
			return getattr(self.model, attr)
		return ",".join(["'"+p+"'" for p in getattr(self.model, attr)])
	def loadInit(self):
		if not os.path.exists(self.dir+"/init"):
			self.error("Cannot find my init file")
		self.init = Init(self, self.dir+"/init")
	def registerJob(self, bundle, name, script, args = {}, forceLocal = False, collect = 0):
		if not hasattr(self, "jobs"    ): self.jobs = []
		if not hasattr(self, "jobcount"): self.jobcount = -1
		self.jobcount += 1
		if collect>0 and self.jobcount%collect!=0:
			self.jobs[-1].addTask(script, args)
			return
		self.jobs.append(Job(bundle, name, script, args, self.options, forceLocal))
	def runJob(self, bundle, name, script, args = {}, forceLocal = False):
		theJob = Job(bundle, name, script, args, self.options, forceLocal)
		theJob.run()
		while not (theJob.isDone() or theJob.isError()):
			self.talk("Job '"+name+"' is running. Checking back in 5 seconds...")
			time.sleep(5)
		if theJob.isError():
			self.error("Job '"+name+"' has finished in error state.")
		del theJob
	def runJobs(self):
		for job in self.jobs:
			job.run()
	def talk(self, message, isError=False, doBreak=False):
		if self.verbosity < 1 and not isError: return
		print ""
		if isError:
			print "ERROR: "+message
			print "Aborting..."
			sys.exit()
		if doBreak:
			print "-"*25
		print timestamp()+": "+message
	def talk2(self, message):
		if self.verbosity < 2: return
		print "cmd: "+message
	def talkBundle(self, bundle):
		self.talk("GOING TO BUILD BUNDLE '"+bundle.name+"'")
		self.addToTalk("model: "+bundle.model)
		self.addToTalk("regions: "+",".join(sorted([r for r in list(set(p.region for p in bundle.packages))])))
		self.addToTalk("lumis: "+",".join(sorted([l for l in list(set(p.lumi for p in bundle.packages))])))
		self.addToTalk("packages: "+",".join(sorted([p.name for p in bundle.packages])))
		self.addToTalk("remark: "+getattr(bundle,"remark",""))
	def talkImport(self):
		self.talk("GOING TO SEARCH FOR AND IMPORT PACKAGES IN "+self.options.inputdir)
	def talkPool(self, pool):
		self.talk("POOL SUCCESSFULLY LOADED: "+str(len(pool.packages))+" packages found")
	def talkStart(self):
		self.talk("+++ Initializing SPM - the ScanPlotMaker +++")
		if len(self.options.excludeTiers)>0: self.addToTalk("Going to exclude tiers "+",".join(["'"+p+"'" for p in self.options.excludeTiers]))
		if len(self.options.redoTiers   )>0: self.addToTalk("Going to redo tiers "   +",".join(["'"+p+"'" for p in self.options.redoTiers   ]))
		if self.options.stopAtTier         : self.addToTalk("Going to stop at tier '"+self.options.stopAtTier+"'")
		if self.options.bundle             : self.addToTalk("Going to process bundle '"+self.options.bundle+"'")
	def tier(self, name):
		self.talk("GOING TO RUN TIER '"+name+"'", False)


