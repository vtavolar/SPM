import sys, os, subprocess, datetime

def askForInput(mm, question, values = [], type="string"):
	toPrint = question
	if len(values)>0: toPrint += " ("+", ".join(values)+")"
	mm.addToTalk(toPrint)
	raw = raw_input(">> ")
	if type == "string": return raw.strip()
	if type == "float" : return float(raw.strip())
	if type == "int"   : return int(raw.strip())
	return raw

def bash(mm, cmd):
	mm.talk2(cmd)
	pipe = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	back = pipe.stdout.read().rstrip("\n").strip()
	return back

def cleandir(mm, path, cpIdx = False):
	if not os.path.isdir(path): return
	path = path.rstrip("/")
	cmd(mm, "rm -rf " + path + "/*")
	if cpIdx: cp(mm, "/afs/cern.ch/user/g/gpetrucc/php/index.php", path)

def cmd(mm, cmd):
	if mm: mm.talk2(cmd)
	os.system(cmd)

def cp(mm, location, destination):
	cmd(mm, "cp " + location + " " + destination)

def idString(id, length=2, leftSide=False):
	if not isinstance(id, str): id = str(id)
	if leftSide:
		return " "*(length-len(id))+id
	return id+" "*(length-len(id))

def mkdir(mm, path, cpIdx = False):
	if os.path.isdir(path): return
	cmd(mm, "mkdir -p " + path)
	if cpIdx and not os.path.exists(path.rstrip("/") + "/index.php"):
		cp(mm, "/afs/cern.ch/user/g/gpetrucc/php/index.php", path)

def mkcleandir(mm, path, cpIdx = False):
	if os.path.isdir(path):
		cleandir(mm, path, cpIdx)
		return
	mkdir(mm, path, cpIdx)

def mv(mm, location, destination):
	cmd(mm, "mv " + location + " " + destination)

def replaceInFile(path, search, replace):
	f = open(path, "r")
	lines = "".join(f.readlines())
	f.close()
	lines = lines.replace(search, replace)
	os.system("rm " + path)
	f = open(path, "w")
	f.write(lines)
	f.close()

def rm(mm, location):
	cmd(mm, "rm -rf " + location)

def setAttrFromLine(obj, line, separator=":"):
	sl = [s.strip() for s in line.split(separator)]
	isList = "+" in sl[0]
	key    = sl[0].strip("+")
	if sl[1].count(",")>0: setattr(obj, key, sl[1].split(","))
	elif isList          : setattr(obj, key, [sl[1]]         )
	else                 : setattr(obj, key, sl[1]           )

def timestamp(readable = True):
	if readable:
		return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	return datetime.datetime.now().strftime("%y%m%d%H%M%S%f")


