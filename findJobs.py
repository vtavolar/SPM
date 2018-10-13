import sys, subprocess
from lib import tools

args = sys.argv[1:]
if len(args)<1: sys.exit()
bundle = args[0]

def bash(base):
	pipe = subprocess.Popen(base, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	back = pipe.stdout.readlines()
	return [l.rstrip("\n").strip() for l in back]

jobs = []
for line in bash("qstat"):
	if "job-ID" in line: continue
	if "---" in line: continue
	sl = line.split()
	for entry in bash("qstat -j "+sl[0]):
		if "script_file" in entry and bundle in entry:
			print sl[0]
			break
