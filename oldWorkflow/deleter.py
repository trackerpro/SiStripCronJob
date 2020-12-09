import os, sys, subprocess, glob

if len(sys.argv) > 0: run = sys.argv[1]
else: 
    print 'Deleter.py got no run number argument! Exiting...'
    sys.exit(1)

jsnfiles = glob.glob('/raid/fff/run'+str(run)+'/*'+str(run)+'*index*.jsn')
events = 0
for jsnfile in jsnfiles:
    command = 'grep "data" '+jsnfile
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (out,err) = proc.communicate()
    events += int(out[15:].split('"')[0])

command = 'edmEventSize -v /raid/fff/run'+str(run)+'/run'+str(run)+'.root | grep "Events"'
proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
(out,err) = proc.communicate()
eventsedm = int(out[out.find('Events ')+7:])

if events == eventsedm:
    print 'EDM and RAW files match, deleting RAW files'
    os.system('rm -f /raid/fff/run'+str(run)+'/*.raw')
else:
    print 'EDM has',eventsedm,'events while RAW files have',events,'events. Leaving RAW filles'
