#!/usr/bin/python

import os,sys,getopt,cx_Oracle,glob,datetime,subprocess

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["runmin=", "runmax="])
except getopt.GetoptError as err:
    print str(err)
    sys.exit(1)

runmin = 0
runmax = 0

for o, a in opts:
    if o == "--runmin": runmin = int(a)
    if o == "--runmax": runmax = int(a)
    
print 'set runmin to',runmin
print 'set runmax to',runmax

conn_str = u'cms_trk_r/1A3C5E7G:FIN@cms_omds_lb'
conn = cx_Oracle.connect(conn_str)
c = conn.cursor()
d = conn.cursor()
e = conn.cursor()
f = conn.cursor()
# use bind parameter to allow the DB to store the query and reuse it
# simply with a different run number
c.prepare(u'select distinct partitionname from viewallrun where runnumber = :run')
d.prepare(u'select ENDTIME from run where runnumber = :run')
e.prepare(u'select RUNMODE from run where runnumber = :run')
f.prepare(u'select ANALYSISID from ANALYSIS where runnumber = :run')

htmldir = '/raid/www/html/jmhogan/clientfiles'

for run in range(runmin,runmax+1):

    hasEDM = False
    hasUpload = False
    hasClient = False
    # Check that this run number represents a real run
    if os.path.exists('/raid/fff/run'+str(run)+'/run'+str(run)+'_ls0001_index000000.raw'):

        # Check if it has already been analyzed
        if os.path.exists('/opt/cmssw/Data/'+str(run)+'/SiStripCommissioningClient_00'+str(run)+'.root'):
            print 'Run',run,'previously analyzed, client file exists in run directory'
            hasClient = True

            if os.path.exists('/raid/fff/run'+str(run)+'/run'+str(run)+'.root'):
                print 'Conversion to EDM has been done for run',run
                hasEDM = True
            
            f.execute(None,{'run':run} )
            analid = f.fetchall()
            if len(analid) > 0: 
                print 'Analysis of',run,'was uploaded to DB'
                hasUpload = True

        # if there's EDM but no upload, want to run the analysis. If there's no EDM and no upload, analysis will do both. If there's no EDM but it's uploaded, just want to do conversion
        print 'Status of run',run,': hasClient =',hasClient,'hasUpload =',hasUpload,'hasEDM =',hasEDM

        # if hasClient and hasEDM and hasUpload: continue #done        

        # if hasClient and hasUpload and not hasEDM:
        #     print 'Converting .raw into a EDM file'
        #     os.chdir('/opt/cmssw/Data/'+str(run))
        #     convertfail = os.system('cmsRun conversion_'+str(run)+'_cfg.py >/dev/null 2>&1')
        #     if convertfail: 
        #         print 'EDM conversion failed'
        #         continue
            
        #     jsnfiles = glob.glob('/raid/fff/run'+str(run)+'/*'+str(run)+'*index*.jsn')
        #     events = 0
        #     for jsnfile in jsnfiles:
        #         command = 'grep "data" '+jsnfile
        #         proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        #         (out,err) = proc.communicate()
        #         events += int(out[15:].split('"')[0])

        #     command = 'edmEventSize -v /raid/fff/run'+str(run)+'/run'+str(run)+'.root | grep "Events"'
        #     proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        #     (out,err) = proc.communicate()
        #     eventsedm = int(out[out.find('Events ')+7:])

        #     if events == eventsedm:
        #         print 'EDM and RAW files match, deleting RAW files'
        #         os.system('rm -f /raid/fff/run'+str(run)+'/*.raw')
        #     else:
        #         print 'EDM has',eventsedm,'events while RAW files have',events,'events. Leaving RAW filles'

        #     # done with this one now
        #     continue

        # otherwise run the analysis script        
        print 'Processing run',run,'through run_analysis_new.sh'

        d.execute(None,{'run':run} )
        end = d.fetchall()

        # Test that the endtime exists
        if len(end)==0: print 'Run',run,'has no end time'
        if len(end) > 0:
            
            # Option to require that endtime is earlier/later than some specific time    
            #endtime = end[0][0]
            #uselaterthan = datetime.datetime(2016,5,5,00,00,00)
            #if endtime > uselaterthan: continue

            c.execute(None,{'run':run} )    
            partition = c.fetchall()
            
            e.execute(None,{'run':run} )
            runmode = e.fetchall()

            # Check for calibration scans which don't analyze properly (or at least take years) # Calibration don't need to be analyzed
            if len(runmode) == 0: print run,'has no type'

            runtype = -1
            if len(runmode) > 0: runtype = (str(runmode[0]).split(',')[0]).split('(')[1]
            if runtype == '19' or runtype == '20': print 'This is a calibration scan'

            # Choose to analyze pedestal, gainscan, timing, and vpsp
            if runtype != '2' and runtype != '4' and runtype != '5' and runtype != '14': continue

            # Test that we got the partition
            if len(partition)==0: print 'Run',run,'has no partition'
            if len(partition) > 0:
                print '---------------------- Analyzing run:',run,'---------------------------'
                print 'partition for type',runtype,'run',run,'=',str(partition[0]).split('\'')[1] 

                dirname = '/opt/cmssw/Data/'+str(run)


                # Run the analysis
                os.system('sh /opt/cmssw/scripts/run_analysis_new.sh '+str(run)+' False False '+str(partition[0]).split('\'')[1]+' False False False True')

                # Save summary hists
                histsfail = os.system('root -l -b -q /raid/cmssw/shifter/jmhogan/saveSummaryHists.cxx\(\\"'+dirname+'/SiStripCommissioningClient_00'+str(run)+'.root\\",\\"'+dirname+'/SummaryHistos_'+str(run)+'.root\\"\)')

                # Make a symbolic link of the output to the web directory                
                if(histsfail): continue
                linkfail = os.system('ln -s '+dirname+'/SummaryHistos_'+str(run)+'.root '+htmldir+'/SummaryHistos_'+str(run)+'.root')
                
                # Add the file to viewruns.html
                if(linkfail): continue
                f = open(htmldir+'/viewruns.html','rU')
                lines = f.readlines()
                f.close()
                with open(htmldir+'/viewruns.html','w') as fout:
                    for line in lines:
                        if line.startswith('       files="'):
                            newline = line.replace('files="','files="SummaryHistos_'+str(run)+'.root;')
                            fout.write(newline)
                        else: fout.write(line)

                # Write an automatic elog entry with the link? TO DO.


print 'DONE'        

c.close()
d.close()
e.close()
f.close()
conn.close()

#  ./run_analysis.sh 
#    1: <run_number>
#    2: <HWUPLOAD>
#    3: <AnalysisUpload>
#    4: <DB_PARTITION>
#    5: <UseClientFile>
#    6: <DisableDevices>
#    7: <saveClientFile>
#    8: <convertEDMfile>

# RUNMODE MODEDESCRIPTION
# ------- ------------------------------
#        1 PHYSIC
#        2 PEDESTAL
#        3 CALIBRATION
#        4 GAINSCAN
#        5 TIMING
#        6 LATENCY
#        7 DELAY
#        8 DELAY_TTC
#       10 PHYSIC10
#       11 CONNECTION
#       12 TIMING_FED
#       13 BARE_CONNECTION
#       14 VPSPSCAN
#       15 SCOPE
#       16 FAST_CONNECTION
#       17 DELAY_LAYER
#       18 PHYSIC_ZERO_SUPPRESSION
#       19 CALIBRATIONSCANPEAK
#       20 CALIBRATIONSCAN_DECO
#       21 VERY_FAST_CONNECTION
#       27 DELAY_RANDOM
#       33 CALIBRATION_DECO


