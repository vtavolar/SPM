from functions import *

class Job():
	def __init__(self, bundle, name, script, args, options, forceLocal = False):
		self.bundle     = bundle
		self.master     = bundle.master
		self.id         = "job"+timestamp(False)
		self.name       = name
		self.template   = script
		self.script     = self.bundle.srcdir+"/"+name+script[script.rfind("."):]
		self.isPython   = True if script[script.rfind(".")+1:]=="py" else False
		self.args       = args
		self.options    = options
		self.forceLocal = forceLocal
		self.prepare()
	def batchRuns(self):
		if self.batchId==-1: return False
		if self.options.queue in ["all.q", "long.q", "short.q"]:
			jobLine = bash(self.master, "qstat -j "+str(self.batchId))
			return not("Following jobs do not exist" in jobLine)
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
			jobLine = bash(self.master, "qstat "+str(self.batchId)) 
			return not("Unknown Job Id Error" in jobLine)
		else:
			jobLine = bash(self.master, "bjobs "+str(self.batchId))
			return not("Job <"+str(self.batchId)+"> is not found" in jobLine)
		return False
	def isDone(self):
		return os.path.exists(self.master.jobdir+"/"+self.id)
	def isError(self):
		stillRunning = self.batchRuns() # will be False for local job
		if stillRunning: return False
		if not os.path.exists(self.master.jobdir+"/"+self.id): return True
		return os.path.exists(self.master.jobdir+"/err_"+self.id)
	def prepare(self):
		template = [l.strip("\n") for l in open(self.master.srcdir+"/template_"+self.template,"r").readlines()]
		task = []
		for line in template:
			line=line.replace("[JOBDIR]"     , self.master.jobdir                                       )
			line=line.replace("[JOBID]"      , self.id                                                  )
			line=line.replace("[SPMDIR]"     , self.master.dir                                          )
			line=line.replace("[CMSSW]"      , self.master.cmssw                                        )
			line=line.replace("[TMPDIR]"     , self.master.tmpdir                                       )
			line=line.replace("[POOLDIR]"    , self.master.pooldir                                      )
			line=line.replace("[BUNDLEDIR]"  , self.master.bundledir                                    )
			line=line.replace("[CARDSDIR]"   , self.bundle.cardsdir.replace(self.bundle.dir+"/","")     )
			line=line.replace("[BUNDLE]"     , self.bundle.name                                         )
			line=line.replace("[SUMMARY]"    , self.bundle.summarydir                                   )
			line=line.replace("[HISTO]"      , self.bundle.histodir                                     )
			line=line.replace("[SMEAR]"      , self.bundle.smeardir                                     )
			line=line.replace("[PLOT]"       , self.bundle.plotdir                                      )
			line=line.replace("[CMD]"        , self.bundle.mode.limitCmd                                )
			line=line.replace("[EXTS]"       , self.master.options.plotExt                              )
			line=line.replace("[PRELIMINARY]", self.master.options.preliminary                          )
			line=line.replace("[LUMIS]"      , ",".join("'"+l+"'" for l in self.bundle.lumis)           )
			line=line.replace("[ENERGY]"     , self.master.options.energy                               )
			line=line.replace("[PACKAGES]"     , " ".join(["'"+p+"'" for p in self.args["packages"]]) if "packages" in self.args.keys() else "")
			line=line.replace("[CARD]"       , self.args["card"]  if "card"  in self.args.keys() else "")
			line=line.replace("[MASS1]"      , self.args["mass1"] if "mass1" in self.args.keys() else "")
			line=line.replace("[MASS2]"      , self.args["mass2"] if "mass2" in self.args.keys() else "")
			for attr in self.master.model.__dict__.keys():
				line=line.replace("[MODEL:"+attr+"]", self.master.getModelParam(attr))
			task.append(line)
		if self.isPython:
			f = open(self.script, "w")
			f.write("\n".join(task))
			f.close()
			task = ["python "+self.script]
			self.script = self.script.replace(".py",".sh")
		runner = "lxbatch_runner.sh"
		if self.options.queue in ["short.q", "all.q", "long.q"]:
			runner = "psibatch_runner.sh"
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
			runner = "oviedobatch_runner.sh"
		r = [l.strip("\n") for l in open(self.master.srcdir+"/"+runner, "r").readlines()]
		f = open(self.script, "w")
		for line in r:
			line = line.replace("[JOBDIR]", self.master.jobdir)
			line = line.replace("[ID]"    , self.id           )
			line = line.replace("[TASK]"  , "\n".join(task)   )
			f.write(line+"\n")
		f.close()
		cmd(self.master, "chmod 755 "+self.script)
	def run(self):
		if self.options.queue and not self.forceLocal:
			super = "bsub -q {queue} -J SPM_{name} "
			if self.options.queue in ["all.q", "long.q", "short.q"]:
				super = "qsub -q {queue} -N SPM_{name} "
			elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
				super = "qsub -q {queue} -N SPM_{name} "
			super += "-o {dir}/submitJob_{name}.out -e {dir}/submitJob_{name}.err "
			super = super.format(queue=self.options.queue, name=self.name, dir=self.bundle.logdir)
		else:
			super = "source "
		self.batchId = self.runCmd(super + self.script)
	def runCmd(self, theCmd):
		jobLine = bash(self.master, theCmd)
		theId   = -1
		if not self.options.queue or self.forceLocal: return theId
		if   self.options.queue in ["all.q", "long.q", "short.q"]                : theId=int(jobLine.split()[2])
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'): theId=int(jobLine.split('.')[0])
		else: theId   = int(jobLine.split()[1].strip("<").strip(">"))
		return theId
		cmd(self.master, super + self.script) 






