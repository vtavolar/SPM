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
                self.HTCsub     = self.master.jobdir +"/HTCsub_"+name+".sh"
		self.tasks      = self.prepare(self.script, self.args)
	def addTask(self, script, args):
		self.tasks += self.prepare(script, args, True)
	def batchRuns(self):
		if hasattr(self, "batchDone"): return self.batchDone
		if self.batchId==-1: return False
		toReturn = False
		if self.options.queue in ["all.q", "long.q", "short.q"]:
			jobLine = bash(self.master, "qstat -j "+str(self.batchId))
			toReturn = not(jobLine=="" or "Following jobs do not exist" in jobLine)
		elif self.options.queue in ["espresso", "microcentury", "longlunch", "workday", "tomorrow", "testmatch", "nextweek"]:
			jobLine = bash(self.master, "condor_q "+str(self.batchId)+" -af JobStatus")
                        toReturn = not(jobLine=="" or jobLine=="3" or jobLine=="4") #jobStatus is not Removed (3) or Completed (4). Sumbission_error (6)?
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
			jobLine = bash(self.master, "qstat "+str(self.batchId)) 
			toReturn = not(jobLine=="" or "Unknown Job Id Error" in jobLine)
		else:
			jobLine = bash(self.master, "bjobs "+str(self.batchId))
			toReturn = not(jobLine=="" or "Job <"+str(self.batchId)+"> is not found" in jobLine)
		if toReturn: setattr(self, "batchDone", True)
		return toReturn
	def isDone(self):
		return os.path.exists(self.master.jobdir+"/"+self.id)
	def isError(self):
		stillRunning = self.batchRuns() # will be False for local job
		if stillRunning: return False
		if not os.path.exists(self.master.jobdir+"/"+self.id): return True
		return os.path.exists(self.master.jobdir+"/err_"+self.id)
	def prepare(self, useScript, useArgs, isAddedTask = False):
		template = [l.strip("\n") for l in open(self.master.srcdir+"/template_"+self.template,"r").readlines()]
		tasks    = []
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
			line=line.replace("[PLOTMODE]"   , self.bundle.mode                                         )
			line=line.replace("[BRAZMASS2]"  , str(self.bundle.mass2)                                   )
			line=line.replace("[CMD]"        , self.bundle.modeinst.limitCmd                            )
			line=line.replace("[EXTS]"       , self.master.options.plotExt                              )
			line=line.replace("[PRELIMINARY]", self.master.options.preliminary                          )
			line=line.replace("[LUMIS]"      , ",".join("'"+l+"'" for l in self.bundle.lumis)           )
			line=line.replace("[ENERGY]"     , self.master.options.energy                               )
			line=line.replace("[PACKAGES]"   , " ".join(["'"+p+"'" for p in useArgs["packages"]]) if "packages" in useArgs.keys() else "")
			line=line.replace("[CARD]"       , useArgs["card"]  if "card"  in useArgs.keys() else "")
			line=line.replace("[MASS1]"      , useArgs["mass1"] if "mass1" in useArgs.keys() else "")
			line=line.replace("[MASS2]"      , useArgs["mass2"] if "mass2" in useArgs.keys() else "")
			for attr in self.master.model.__dict__.keys():
				line=line.replace("[MODEL:"+attr+"]", self.master.getModelParam(attr))
			tasks.append(line)
		if self.isPython:
			f = open(useScript, "w")
			f.write("\n".join(tasks))
			f.close()
			tasks = ["python "+useScript]
			if not isAddedTask:
				self.script = useScript.replace(".py",".sh")
		return tasks
	def prepareRun(self):
		runner = "lxbatch_runner.sh"
		if self.options.queue in ["short.q", "all.q", "long.q"]:
			runner = "psibatch_runner.sh"
		elif self.options.queue in ["espresso", "microcentury", "longlunch", "workday", "tomorrow", "testmatch", "nextweek"]:
			runner = "htcondor_runner.sh"
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
			runner = "oviedobatch_runner.sh"
		r = [l.strip("\n") for l in open(self.master.srcdir+"/"+runner, "r").readlines()]
		f = open(self.script, "w")
		for line in r:
			line = line.replace("[JOBDIR]", self.master.jobdir   )
			line = line.replace("[JOBID]" , self.id              )
			line = line.replace("[TASK]"  , "\n".join(self.tasks))
			f.write(line+"\n")
		f.close()
		cmd(self.master, "chmod 755 "+self.script)
	def run(self):
		self.prepareRun()
		if self.options.queue not in ["espresso", "microcentury", "longlunch", "workday", "tomorrow", "testmatch", "nextweek"]:
			if self.options.queue and not self.forceLocal:
				super = "bsub -q {queue} -J SPM_{name} "
				if self.options.queue in ["all.q", "long.q", "short.q"]:
					super = "qsub -q {queue} -N SPM_{name} "
				elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'):
					super = "qsub -q {queue} -N SPM_{name} "
				super += "-o {dir}/submitJob_{name}.out -e {dir}/submitJob_{name}.err "
				super = super.format(queue=self.options.queue, name=self.name, dir=self.bundle.logdir)
				self.batchId = self.runCmd(super + self.script)
			else:
				super = "source "
				self.batchId = self.runCmd(super + self.script)


######
		elif self.options.queue in ["espresso", "microcentury", "longlunch", "workday", "tomorrow", "testmatch", "nextweek"]:
                        template = [l.strip("\n") for l in open(self.master.srcdir+"/htcondor_submitter.sh").readlines()]
                        f = open(self.HTCsub, "w")
                        for line in template:
                                line = line.replace("[SCRIPT]"       , self.script   )
                                line = line.replace("[NAME]"       , self.name   )
                                line = line.replace("[QUEUE]"       , '"'+self.options.queue+'"'   )
                                line = line.replace("[DIR]"       , self.bundle.logdir  )
                                f.write(line+"\n")
                        f.close()
                        super = "condor_submit "+str(self.HTCsub)
                        self.runCmd(super)
                        ##to be fixed for monitoring htcondor jobs
                        jobIdCmd = "condor_wait %s/job.%s.log -status -wait 0.01" % (self.bundle.logdir, self.name)
			print jobIdCmd
                        jobIdOut = bash(self.master, jobIdCmd)
                        print "wait out ",jobIdOut
                        if jobIdOut == "":
                                print "jobIdOut is empty"
                                ntry=0
                                while(ntry<5 and jobIdOut==""):
                                        print "sleeping 1 and trying again for the %s time"%ntry
                                        time.sleep(1)
                                        jobIdOut = bash(self.master, jobIdCmd)
                                        ntry=ntry+1
                                        print "now jobIdOut is", jobIdOut

                        if jobIdOut == "":
                                print "Could not set job Id for this job, setting to 0"
                                self.batchId = 0
                        else:
                                self.batchId = jobIdOut.split()[0][:-2]
                        print "condor jobId ",self.batchId
		else:
			print "Queue not known."



	def runCmd(self, theCmd):
		jobLine = bash(self.master, theCmd)
		theId   = -1
		if not self.options.queue or self.forceLocal: return theId
		if   self.options.queue in ["all.q", "long.q", "short.q"]                : theId=int(jobLine.split()[2])
		elif self.options.queue in ["batch"] and os.path.isdir('/pool/ciencias/'): theId=int(jobLine.split('.')[0])
		elif self.options.queue in ["espresso", "microcentury", "longlunch", "workday", "tomorrow", "testmatch", "nextweek"]: theId=0
		else: theId   = int(jobLine.split()[1].strip("<").strip(">"))
		return theId
		cmd(self.master, super + self.script) 






