#!/usr/bin/python

import os,sys,getopt,glob

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["runmin=", "runmax="])
except getopt.GetoptError as err:
    print str(err)
    sys.exit(1)

runmin = 0
runmax = 0

for o, a in opts:
    print o, a
    if o == "--runmin": runmin = int(a)
    if o == "--runmax": runmax = int(a)

print 'set runmin to',runmin
print 'set runmax to',runmax

for run in range(runmin,runmax+1):
    if os.path.exists('/opt/cmssw/Data/'+str(run)):
        roots = glob.glob('/opt/cmssw/Data/'+str(run)+'/USC.00'+str(run)+'*.root')
        dats = glob.glob('/opt/cmssw/Data/'+str(run)+'/USC.00'+str(run)+'*.dat')
        log = glob.glob('/opt/cmssw/Data/'+str(run)+'/conversion*.log')        
        if len(roots) > 0 and len(log) > 0: 
            print '---------------------- Run converted previously:',run,'---------------------------'
            os.system('ls -lh /opt/cmssw/Data/'+str(run)+'/USC*')
        else:
            print '---------------------- Converting run:',run,'---------------------------'
            print 'N DATs:',len(dats)
            os.system('sh /opt/cmssw/scripts/run_conversion_SLC6.sh '+str(run))
            roots = glob.glob('/opt/cmssw/Data/'+str(run)+'/USC.00'+str(run)+'*.root')
            print 'N ROOTs:',len(roots)
            print 'file size check:',str(run)
            os.system('ls -lh /opt/cmssw/Data/'+str(run)+'/USC*')

print 'DONE'
