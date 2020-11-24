#!usr/inb/python

import os,sys
import getopt
import cx_Oracle
import glob
import datetime
import json
import ROOT as r

rundir = '/raid/fff'
analyzed_runs = 'analyzedruns.txt'
failed_runs = 'failedruns.txt'

# Comepare runs in /raid/fff/ with a list of analyzed runs
def get_runlist():
    runs = [ x.split('/')[-1] for x in glob.glob('{}/run*'.format(rundir)) ]
    if len(runs) == 0:
        print 'Found no runs in rundir: {}....aborting'.format(rundir)
        sys.exit()
    if os.path.exists(analyzed_runs):
        analyzed = open(analyzed_runs, 'r').readlines()
    else:
        analyzed = []
    if os.path.exists(failed_runs):
        failed = open(failed_runs, 'r').readlines()
    else:
        failed = []
    return list(set(runs) - set(analyzed) - set(failed))

def get_machine():
    import socket
    srv = socket.gethostname()
    if srv not in ['srv-s2b17-29-01', 'srv-s2b17-30-01']:
        print 'Not running on service machine'
        sys.exit(1)
    return srv

def write_to_file(run, good):
    if good:
        filename = analyzed_runs
    else:
        filename = failed_runs
    f = open(filename, 'a+')
    f.write('run%d\n'%run)
    f.close()
    print 'Appended run to', filename

def validate_time(start, end):
    # Check the following:
    #  - start time in DB
    #  - start time not in future
    #  - start time not after end time
    #  - end time not in the future
    if not start: return False
    if start > datetime.datetime.now(): return False
    if start > end: return False
    if end > datetime.datetime.now(): return False

    print 'Runtime is good'
    return True

def validate_events(run):
    # Check that the output root file was created properly and make sure that all events were processed
    # If so, we can delete raw files

    # Use json files to get event number from raw files
    json_name = '{rundir}/run{run}/run{run}_ls0000_EoR.jsn'.format(rundir=rundir,run=run)
    if not os.path.exists(json_name):
        print 'json file %s does not exist' % json_name
        return False
    json_events = int(json.load(open(json_name, 'r'))['data'][0])
    
    # Open up tree and get number of events from Events tree
    # If this fails, problem with root file
    try:
        tfile = r.TFile('{rundir}/run{run}/run{run}.root'.format(rundir=rundir,run=run), 'READ')
        events = int(tfile.Events.GetEntries())
        tfile.Close()
    except:
        print 'Unable to open file {rundir}/run{run}/run{run}.root'.format(rundir=rundir,run=run)
        return False

    if json_events == events:
        return True
    else:
        print 'Different number of events in json and root file'
        print 'json:', json_events
        print 'root:', events
        return False

def delete_raw(run):
    os.system('ls {rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))
    #os.system('rm {rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))
    
def validate_db(run, conn):
    # Check if analyzed run has been uploaded properly
    hasClient = False
    hasSource = False
    hasDB = False
    if os.path.exists('/opt/cmssw/Data/{run}/SiStripCommissioningClient_00{run}.root'.format(run=run)): hasClient=True
    if glob.glob('/opt/cmssw/Data/{run}/SiStripCommissioningSource_00{run}*.root'.format(run=run)): hasSource=True
    c = conn.cursor()
    c.execute(u'select ANALYSISID,VERSIONMAJORID,VERSIONMINORID,RUNNUMBER,ANALYSISTYPE,PARTITIONNAME from analysis a join partition b on a.partitionid=b.partitionid where runnumber=:run', {'run':run})
    results = c.fetchall()[0]
    print results
    if results[0] and results[1] and results[2]: hasDB = True
    if hasClient and hasSource and hasDB:
        print 'Client file, upload file, and DB info is good'
        return True
    else:
        print 'validate db failed'
        return False
        

def analyze_runs(runs, srv):

    # TODO make sure these are the correct partition names
    parts_to_run = ['TI', 'TM', 'TO', 'TP']
    #if srv == 'srv-s2b17-29-01':
    #    parts_to_run = ['TI', 'TM']
    #else:
    #    parts_to_run = ['TO', 'TP']

    # First make connection to database
    conn_str = u'cms_trk_r/1A3C5E7G:FIN@cms_omds_lb'
    conn = cx_Oracle.connect(conn_str)
    c = conn.cursor()

    # Loop through list of runs
    for run in runs:

        run = int(run[3:])
        hasEDM = False
        dbValid = False
        eventsValid = False
        timeValid = False
        
        # first get run information
        c.execute(u'select PARTITIONNAME,RUNMODE,STARTTIME,ENDTIME from RUN a join PARTITION b on a.PARTITIONID=b.PARTITIONID where RUNNUMBER=:run', {'run':run})     
        db_results = c.fetchall()[0]
        if len(db_results):
            (partition, runmode, start, end) = db_results
        else:
            # run number not in database
            print 'Run number', run, 'not in RUN database, aborting run'
            continue

        # First check if run is finished to see if we should continue looking at it
        if end:
            timeValid = validate_time(start, end)
        else:
            # Run has not finished yet
            continue

        # TODO add CALIBRATION=3,CALIBRATION_DECO=33,CALIBRATION_SCAN=19,CALIBRATION_SCAN_DECO=20 if we decide to 
        if runmode not in [2, 4, 5, 6, 7, 11, 14, 15, 16, 17, 21, 27]: continue
        if not any(part in partition for part in parts_to_run): continue


        # TODO need separate case for spy channel, where we only run raw->EDM


        if os.path.exists('{rundir}/run{run}/run{run}.root'.format(rundir=rundir, run=run)):
            # Check if raw files still exist, if so see if we can delete them
            print 'run was analyzed'
            hasEDM = True
            eventsValid = validate_events(run)
            if len(glob.glob('{rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))):
                if eventsValid: delete_raw(run)
        else:
            print 'run not yet analyzed'
            # Pack the raw files together and into EDM format and analyze based on run analysis
            #os.system('sh /opt/cmssw/scripts/run_analysis_CC7.sh {run} False True {partition} False False True True'.format(run=run, partition=partition))
            # make sure edm file now exists
            if not os.path.exists('{rundir}/run{run}/run{run}.root'.format(rundir=rundir, run=run)):
                print 'Ran analysis but EDM does not exist, aborting run'
                write_to_file(run, False)
                continue
            eventsValid = validate_events(run)

        dbValid = validate_db(run, conn)

        print hasEDM, dbValid, eventsValid, timeValid
        if hasEDM and dbValid and eventsValid and timeValid:
            write_to_file(run, True)
        else:
            write_to_file(run, False)

    return



def main():
    srv = get_machine()
    #runs = get_runlist()
    runs = ['run338337']
    if len(runs):
        analyze_runs(runs, srv)
    return 0

if __name__ == '__main__':
    main()


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
