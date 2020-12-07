#!usr/inb/python

import os,sys
import getopt
import cx_Oracle
import glob
import datetime
import json
import ROOT as r

rundir = '/raid/fff'
analyzed_runs = '/opt/cmssw/scripts/SiStripCronJob/analyzedruns.txt'
failed_runs = '/opt/cmssw/scripts/SiStripCronJob/failedruns.txt'

# Comepare runs in /raid/fff/ with a list of runs that have passed or failed analysis
# Returns the runs not in either list
def get_runlist():
    runs = [ x.split('/')[-1] for x in glob.glob('{}/run*'.format(rundir)) ][:70]
    if len(runs) == 0:
        print 'Found no runs in rundir: {}....aborting'.format(rundir)
        sys.exit()
    if os.path.exists(analyzed_runs):
        analyzed = open(analyzed_runs, 'r').read().splitlines()
    else:
        analyzed = []
    if os.path.exists(failed_runs):
        failed = open(failed_runs, 'r').read().splitlines()
        # Strip off the fail reasons
        failed = [fail.split()[0] for fail in failed]
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

def write_to_file(run, good, reason=[]):
    if good:
        filename = analyzed_runs
    else:
        filename = failed_runs
    f = open(filename, 'a+')
    f.write('run%d'%run)
    if not good and len(reason) > 0:
        [f.write(' '+str(fail)) for fail in reason]
    f.write("\n")
    f.close()
    print 'Appended run to', filename

def validate_time(start, end):
    # Check the following:
    # start time in DB
    if not start: return False
    # start time not in future
    if start > datetime.datetime.now(): return False
    # start time not after end time
    if start > end: return False
    # end time not in the future
    if end > datetime.datetime.now(): return False

    return True

def validate_events(run):
    # Check that the output root file was created properly and make sure that all events were processed
    # If so, we can delete raw files

    # Use json files to get event number from raw files

    # First make sure json file exists
    json_name = ['{rundir}/run{run}/run{run}_ls0000_EoR.jsn'.format(rundir=rundir,run=run)]
    try:
        json_events = int(json.load(open(name, 'r'))['data'][0])
    # If this fails, either json doesnt exist or is empty
    # In either case, fall back to old method of reading all json
    except:
        #print 'json file %s does not exist' % json_name
        json_name = glob.glob('{rundir}/run{run}/run{run}_ls*_index*.jsn'.format(rundir=rundir,run=run))
        if len(json_name) == 0:
            print 'Could not find any json files, unable to validate events'
            return False
        json_events = sum([int(json.load(open(name, 'r'))['data'][0]) for name in json_name])

    # Make sure EDM file exists
    tfile_name = '{rundir}/run{run}/run{run}.root'.format(rundir=rundir,run=run)
    if not os.path.exists(tfile_name):
        print 'root file %s does not exist' % tfile_name
        return False
    
    # Open up tree and get number of events from Events tree
    # If this fails, problem with root file
    try:
        tfile = r.TFile(tfile_name, 'READ')
        events = int(tfile.Events.GetEntries())
    except:
        print 'Unable to open file {rundir}/run{run}/run{run}.root and read Events tree'.format(rundir=rundir,run=run)
        return False
    if tfile.IsZombie():
        print 'Warning, file is zombie'
        tfile.Close()
        return False
    if tfile.TestBit(r.TFile.kRecovered):
        print 'Warning, file recovery procedure was run on file'
        tfile.Close()
        return False
    tfile.Close()

    if json_events == events:
        #print 'EDM file validated, total number of events:', events
        return True
    else:
        print 'Different number of events in json and root file'
        print 'json:', json_events
        print 'root:', events
        return False

def delete_raw(run):
    return
    os.system('ls {rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))
    #os.system('rm {rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))
    
# Note, only care about partition for spy runs, all other runs leave field blanks
def validate_db(run, conn, partition=''):
    # Check if analyzed run has been uploaded properly
    hasClient = False
    hasSource = False
    hasDB = False
    #os.system('ls /opt/cmssw/Data/{run}/'.format(run=run))
    if glob.glob('/opt/cmssw/Data/{run}/SiStripCommissioningClient_*{part}*{run}*.root'.format(part=partition, run=run)): hasClient=True
    if glob.glob('/opt/cmssw/Data/{run}/SiStripCommissioningSource_*{part}*{run}*.root'.format(part=partition, run=run)): hasSource=True

    c = conn.cursor()
    if partition == '':
        db_cmd = u"select ANALYSISID,VERSIONMAJORID,VERSIONMINORID,RUNNUMBER,ANALYSISTYPE,PARTITIONNAME from analysis a join partition b on a.partitionid=b.partitionid where runnumber=%d" % run
    else:
        db_cmd = u"select ANALYSISID,VERSIONMAJORID,VERSIONMINORID,RUNNUMBER,ANALYSISTYPE from analysis a join partition b on a.partitionid=b.partitionid where runnumber=%d and PARTITIONNAME='%s'" % (run, partition)
    print db_cmd
    c.execute(db_cmd)
    try:
        results = c.fetchall()[0]
    except:
        print 'run not in db'
        return False

    # Want to make sure the entries aren't empty
    # Casting values to strings or else ID value of 0 is interpreted as False
    if str(results[0]) and str(results[1]) and str(results[2]): hasDB = True
    print hasClient, hasSource, hasDB
    if hasClient and hasSource and hasDB:
        # print 'Client file, upload file, and DB info is good'
        return True
    else:
        print 'One or more validate_db checks have failed'
        return False
        

def analyze_runs(runs, partitions, rerun=False):

    # First make connection to database
    conn_str = u'cms_trk_r/1A3C5E7G:FIN@cms_omds_lb'
    #os.system('getConfDb CONFDB_ONLINE')
    #conn_str = os.getenv('CONFDB')
    conn = cx_Oracle.connect(conn_str)
    c = conn.cursor()

    # Loop through list of runs
    for run in runs:

        run = int(run[3:])
        hasEDM = False
        dbValid = False
        timeValid = False

        print '***************************************************'
        print 'Starting run', run
        
        # first get run information
        c.execute(u'select PARTITIONNAME,RUNMODE,STARTTIME,ENDTIME from RUN a join PARTITION b on a.PARTITIONID=b.PARTITIONID where RUNNUMBER=:run', {'run':run})     
        db_results = c.fetchall()
        print db_results
        if len(db_results):
            (partition, runmode, start, end) = db_results[0]
        else:
            # run number not in database
            print 'Run number', run, 'not in RUN database, aborting run'
            continue

        # For spy channel, make sure that you check that you retreive all partitions that were used in run
        if runmode == 15:
            partition = [result[0] for result in db_results]
        else:
            partition = [partition]

        # First check if run is finished to see if we should continue looking at it
        if end:
            timeValid = validate_time(start, end)
        else:
            # Run has not finished yet
            continue

        # Check if run is of the type that we want to run
        modes_to_analyze = [2, 4, 5, 6, 7, 11, 14, 15, 16, 17, 21, 27]
        # If running certain partitions on different machines, then add CALIBRATION=3,CALIBRATION_DECO=33,CALIBRATION_SCAN=19,CALIBRATION_SCAN_DECO=20 modes
        #modes_to_analyze += [3, 19, 20, 33]
        if runmode not in modes_to_analyze: continue

        # Check if this partition run on machine (only matters if spltting jobs onto srv 29-01 and 30-01)
        # Exception is spy run which only gets run on srv-s2b17-XX-01
        if any(part in partition[0] for part in partitions) and runmode != 15:
            pass
        elif runmode == 15 and partitions[0] == 'TI':
            pass
        else:
            continue

        # For runs that are stopped and started multiple times, they will produce extra 0 event runs
        # For those runs, just ignore them and add the run number to list of good runs
        if len(glob.glob('/raid/fff/run{run}/*'.format(run=run))) == 4:
            # will have fu.lock, hlt, jsd, and run{run}_ls0000_EoR.jsn
            print 'This was an empty run'
            write_to_file(run, True)
            continue

        # first check if EDM file exists for run
        if os.path.exists('{rundir}/run{run}/run{run}.root'.format(rundir=rundir, run=run)):
            print 'run was analyzed'
            # If EDM file exists, check that analysis finished properly
            hasEDM = validate_events(run)
            dbValid = validate_db(run, conn)
            hasRaw = len(glob.glob('{rundir}/run{run}/*.raw'.format(rundir=rundir, run=run))) > 0
            if not hasEDM and hasRaw:
                print 'Problem in existing EDM file and raw files still exist.\nWill delete EDM file and re-run analysis'
                #os.system('ls {rundir}/run{run}/run{run}.root'.format(rundir=rundir, run=run))
                #os.system('rm {rundir}/run{run}/run{run}.root'.format(rundir=rundir, run=run))
            elif not hasEDM and not hasRaw:
                print '***warning*** Problem validating EDM file but no raw files exist...Will continue with existing file, but problems may ensue'
            elif hasEDM and hasRaw:
                # EDM file is good and raw still exists, delete the no longer needed raw files to save space
                print 'Run has already been analyzed, but raw files still exist. Deleting raw files'
                delete_raw(run)
                
        # For spy runs, still need to check that analysis was run on each partition
        if not (hasEDM and dbValid) or runmode == 15:
            # Pack the raw files together and into EDM format and analyze based on run analysis
            print 'Will now perform analysis on run'
            if len(partition) == 1:
                pass
                #os.system('sh /opt/cmssw/scripts/run_analysis_CC7.sh {run} False True {partition} False False True True'.format(run=run, partition=partition[0]))
                dbValid = validate_db(run, conn)
            else:
                # for spy runs need to loop over all partitions
                dbValid_part = []
                for part in partition:
                    # Check if we have already succesfully analyzed this partition
                    if validate_db(run, conn, part):
                        dbValid_part.append(True)
                    else:
                        #os.system('sh /opt/cmssw/scripts/run_analysis_CC7.sh {run} False True {partition} False False True True'.format(run=run, partition=part))
                        dbValid_part.append(validate_db(run, conn, part))
                # Make sure check returns true for all partitions
                dbValid = all(dbValid_part)

            hasEDM = validate_events(run)
            if hasEDM:
                delete_raw(run)

        # Finally, make sure all validation checks return True
        print '*** Analysis Validation Checks ****'
        print 'Run start and end time are consistent:', timeValid
        print 'EDM File Good:', hasEDM
        print 'Commissioning and source files exist, analysis added to DB:', dbValid
        print '**** Result ****'
        if timeValid and hasEDM and dbValid:
            print 'Run %d is good\n' % run
            write_to_file(run, True)
        elif not rerun:
            # If any check fails, try running it again
            print 'One or more check failed, will re-run over run\n', run
            analyze_runs(['run%d'%run], partitions, rerun=True)
        else:
            # If run fails second time, add to list of failed runs and continue
            print 'Analysis failed a second time, adding run to fail list\n'
            write_to_file(run, False, [timeValid, hasEDM, dbValid])
            return

    return



def main():
    srv = get_machine()
    # Figure out which partitions to run on
    if srv == 'srv-s2b17-29-01':
        partitions = ['TI', 'TM']
    elif srv == 'srv-s2b17-30-01':
        partions= ['TO', 'TP']
    partitions = ['TI', 'TM', 'TO', 'TP']
    runs = get_runlist()
    print runs
    #runs = ['run334325', 'run312876', 'run338329', 'run336985', 'run324898', 'run325058', 'run325160']
    #runs = ['run324898']
    if len(runs):
        analyze_runs(runs, partitions)
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
