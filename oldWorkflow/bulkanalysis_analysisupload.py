#!/usr/bin/python

import os,sys,getopt,cx_Oracle,glob,datetime

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
# use bind parameter to allow the DB to store the query and reuse it
# simply with a different run number
c.prepare(u'select distinct partitionname from viewallrun where runnumber = :run')
d.prepare(u'select ENDTIME from run where runnumber = :run')
# might need a new conn u'select RUNMODE from run where runnumber = :run'

htmldir = '/raid/www/html/jmhogan/clientfiles'

for run in range(runmin,runmax+1):

    # Look for files in Data/closed/
    if os.path.exists('/opt/cmssw/Data/closed/USC.00'+str(run)+'.0001.A.storageManager.00.0000.dat'):
    #roots = glob.glob('/opt/cmssw/Data/SiStripCommissioningSource_00'+str(run)+'*.root')
    #if len(roots) > 0:
        d.execute(None,{'run':run} )
        end = d.fetchall()

        # Test that the endtime exists
        if len(end) > 0:
            
            # Option to require that endtime is earlier/later than some specific time    
            #endtime = end[0][0]
            #uselaterthan = datetime.datetime(2016,5,5,00,00,00)
            #if endtime > uselaterthan: continue

            c.execute(None,{'run':run} )    
            partition = c.fetchall()

            # Test that we got the partition
            if len(partition) > 0:
                print '---------------------- Analyzing run:',run,'---------------------------'
                print 'partition for run',run,'=',str(partition[0]).split('\'')[1]

                dirname = '/opt/cmssw/Data/'+str(run)

                # Check for calibration scans which don't analyze properly (or at least take years)
                scans_Data = glob.glob('/opt/cmssw/Data/SiStripCommissioningSource_00'+str(run)+'*_ISHA*.root')
                scans_Run = ''
                if os.path.exists(dirname): scans_Run = glob.glob(dirname+'/SiStripCommissioningSource_00'+str(run)+'*_ISHA*.root')
                if len(scans_Data) > 0 or len(scans_Run) > 0:
                    print 'Run '+str(run)+' is a scan: not analyzing'
                    if not os.path.exists(dirname): os.makedirs(dirname) 
                    os.system('mv /opt/cmssw/Data/SiStripCommissioningSource_00'+str(run)+'*.root '+dirname+'/')
                    os.system('mv /opt/cmssw/Data/closed/USC.00'+str(run)+'.*.dat '+dirname+'/')
                else:
                    # Run the analysis
                    os.system('sh /opt/cmssw/scripts/run_analysis.sh '+str(run)+' False True '+str(partition[0]).split('\'')[1]+' False False True')

                    # PLACEHOLDER: rerun ONLY GAINSCAN runs from raw
                    # Almost certainly need a new DB connection to access the RUNMODE -- gainscan is "4"


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

                    # Run the DAT --> ROOT conversion job
                    os.system('sh /opt/cmssw/scripts/run_conversion_SLC6.sh '+str(run))


print 'DONE'        

c.close()
d.close()
conn.close()

#  ./run_analysis.sh 
#    1: <run_number>
#    2: <HWUPLOAD>
#    3: <AnalysisUpload>
#    4: <DB_PARTITION>
#    5: <UseClientFile>
#    6: <DisableDevices>
#    7: <saveClientFile>

#"Usage:  ./run_analysis.sh <run_number> <HWUPLOAD> <AnalysisUpload> <DB_partition_name> <UseClientFile> <DisableDevices> <saveClientFile>"
#"  run_number        = run number"
#"  HWUpload          = set to true if you want to upload the HW config to the DB"
#"  AnalysisUpload    = set to true if you want to upload the analysis results to the DB"
#"  DB_partition_name = Name of the corresponding DB partition"
#"  UseClientFile     = set to true if you want to analyze an existing client file rather than the source file(s)"
#"  DisableDevices    = set to true if you want to disable devices in the DB (normally set False)"
#"  saveClientFile    = set to true if you want to write the client file to disk (normally set True)"

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


