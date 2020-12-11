# SiStripCronJob

This script is used to automatically look for new strip commissioning runs. When it finds new runs, it then checks whether or not they need to be analyzed. If they do, the script then runs /opt/cmssw/scripts/run\_analysis\_CC7.sh


## Running the code

To run the code, first run the following command to setup the proper cmssw environment and connect to the database </br>
`source setup_env.sh`

The cron-job task can then be run via </br>
`python stripanalysis.py`

The code will then continue to run and check for new runs every 2 hours until the script is manually killed.

## Code workflow

The cron-job workflow can be broken up into the following steps:
1. Determine which service machine the script is being run from
2. Obtain a list of new runs
3. Obtain run information from the RUN database
4. Use DB information to determine whether the script should look at the run
5. Check if the run has been analyzed
6. If applicable, analyze the run
7. Determine whether the analysis has run properly
8. Wait for 1 hour, and go to step 2

## Description of analysis strips

#### 1. Determine which service machine the script is being run from

The code can be run from srv-s2b17-29-01 or srv-s2b17-30-01, and `socket.gethostname()` is used to determine which of the machines are being used. The script is designed to be run on both machines in parallel. srv-s2b17-29-01 will be used to analyze runs including the TI and TM, and srv-s2b17-30-01 will be used to analyze the TO and TP. However, if the code is only being run from on one machine, the line `partitions = ['TI', 'TM', 'TO', 'TP']` can be added to `main()` at the bottom of the script.

#### 2. Obtain a list of new runs

The run list is obtained by first using the `glob` module to create a list of all run directories in the /raid/fff/ storage area. Runs are then filtered out of the list if they are marked as good in /opt/cmssw/scripts/SiStripCronJob/analyzedruns.txt or bad in /opt/cmssw/scripts/SiStripCronJob/failedruns.txt
Both of the files are maintained by this workflow, and only consist of runs that it has previosly looked at and verified whether or not the analysis was performed properly.

Once the run list has been obtained, they script loops through them in the `analyze_runs() function`

#### 3. Obtain run information from the RUN database

The cx\_oracle module is used to query various databases. Before looping through the list of newly taken runs, the script first connects to cms\_trk\_r/1A3C5E7G:FIN@cms\_omds\_lb. When looping through the run list, the script will query the RUN database using the following sql command:
`select PARTITIONNAME,RUNMODE,STARTTIME,ENDTIME from RUN a join PARTITION b on a.PARTITIONID=b.PARTITIONID where RUNNUMBER=$(RUNNUMBER)`

If nothing is returned from the database, the code assumes that the run is not yet ready to be analyzed, and skips the run without appending it to the good or failed analysis files.

If the run is found the database, the name of the parition used, run mode, run start time, and run end time are saved. In the case of runs taken in scope mode (run mode 15) we expect 4 results from the database query due to spy data (which is read in scope mode) using all 4 detector partitions. Because of this case, the partition is stored in a list despite only having one element for the majority of runs.

#### 4. Use DB information to determine whether the script should look at the run

Once the run has been found in the database, multiple checks are performed to determine whether the run should be analyzed

* Time:
    The database needs to show that the run has finished. Furthermore, the `end_delay` variable can be modified in `main()` to specify how many hours have to have passed since the run finished before the script considers analyzing it. By default, this is set to 2 hours. The extra delay is used so users have an oppurtunity to manually analyze runs as they finish. If the end time check passes, the `validate_time()` function is run to make sure that the start and end times listed in the database are make sense.

* Runmode:
    Only the following run modes are analyzed by this script
    * 2 -
        PEDESTAL
    * 4 -
        GAINSCAN
    * 5 -
        TIMING
    * 6 -
        LATENCY
    * 7 -
        DELAY
    * 11 -
        CONNECTION
    * 14 -
        VPSPSCAN
    * 15 -
        SCOPE
    * 16 -
        FAST\_CONNECTION
    * 17 -
        DELAY\_LAYER
    * 21 -
        VERY\_FAST\_CONNECTION
    * 27 -
        DELAY\_RANDOM

    If the cron-job is run on srv-s2b17-29-01 and srv-s2b17-30-01 in parallel, the following run modes will also be analyzed:
    * 3 -
        CALIBRATION
    * 19 -
        CALIBRATIONSCANPEAK
    * 20 -
        CALIBRATIONSCAN\_DECO
    * 33 -
        CALIBRATION\_DECO

* Partition:
    As mentioned above, if the cron-job is run from both service machines then each service machine will only analyze specific partitions. If the run partition is not supposed to be run on the current machine, it is skipped.

* Lock File:
    To make sure two runs are not analyzed at the same time, /opt/cmssw/scripts/run_analysis_CC7.sh will create a lock file to signify that a run is currently being analyzed. If the cron-job were to move forward with a run while it is being analyzed, the run will fail the validation checks and it can potential create problems with the EDM file creation. To prevent this from happening, the cron-job will skip the run without appending it to the good or failed analysis list if it finds the lock file.

If a run passes the previous checks, the script does one additional check to see if it is a 0 event run. These can be created when a run is started and stopped multiple times. Each time the run is stopped, a unique run directory will be created in the /raid/fff/ storage area and will be added to the RUN database. However, the only run that has events will be the final run number in the group. The run checks for these runs by looking at the /raid/fff/run$(RUNNUMBER) directory and counting its content. If and only if there are no events in the run, the only files and subdirectories that will exist are `fu.lock`, `hlt`, `jsd`, and `run$(RUNNUMBER)_ls0000_E0R.jsn`. In these cases, the run will be appened to the list of succesfully analyzed runs and skipped.

#### 5. Check if the run has been analyzed

The script looks for the existance of the /raid/fff/run$(RUNNUMBER)/run$(RUNNUMBER).root EDM file to determine whether the run has already been analyzed. If the code finds the EDM file, it performs a sequency of analysis validation checks (described in step 7) to determine if the run was analyzed properly. If it finds problems with the EDM file but finds that the original raw files still exist, it will delete the EDM file so it can be recreated in the following step. If it verifies the EDM file integrity and finds that the raw files still exist, it will delete the raw files.

For runs taken in scope mode, only the EDM file validation is performed in this step. The other analysis verification checks are later performed for each partition to better accomodate the scope mode workflow.

#### 6. If applicable, analyze the run

If the code does not find the EDM file, or it finds the EDM file but one of the analysis validation checks fails, the run will be analyzed using the following command:
`'sh /opt/cmssw/scripts/run_analysis_CC7.sh $(RUN) False True $(PARTITIONNAME) False False True True`
The True parameters that the run should be added to the ANALYSIS database, a SiStripCommissioningClient file should be saved for the analysis, and that the an EDM file should be produced if it does not already exist.

If the run was taken in scope mode, this analysis is individually run over each partition. However, an additional check is made to see if the partition has already been analyzed. If it has, the partition will be skipped to prevent unneeded computations.

#### 7. Determine whether the analysis has run properly

For an analyzed run, the `validate_events()` and `validate_db()` checks are performed to make sure that the run analysis finished without and problems. For both validation procedures, the following steps are performed:

###### 7a. Validate EDM

The EDM file is validated using the `validate_db()` function. The function will return `True` if the files passes all checks, and return `False` if any of the checks fail.

The json files are read to determine the number of events in the raw file. If it exists, only the /raid/fff/run$(RUNNUMBER)/run$(RUNNUMBER)\_ls0000\_EoR.jsn is read because it stores the event count for the entire run. However, this file may not exist for older runs and in that case the script will read all /raid/fff/run$(RUNNUMBER)/run$(RUNNUMBER)\_ls\*\_index\*.jsn to obtain the total event count from all raw files.

The EDM file is then opened using pyroot and the event count is obtained using `TFile.Events.GetEntries()`. The file is then checked to see if it is a zombie or if the file recovey procedure was run during it's creation. If either of the checks return True or the script is unable to read the Events tree, the EDM file will be marked as bad.

If the previous TFile integrity checks pass, the script will compare the number of events in the json file with the number of events in the EMD file. If the event counts are not equal, the EDM file is marked as bad.

###### 7b. Validate Database and SiStripCommissioning Files

The script looks for the existance of the SiStripCommissioningClient and SiStripCommissioningSource files in the /opt/cmssw/Data/$(RUNNUMBER)/ directory. For runs taken in scope mode, an additional check is performed to make sure that the partition name exists in the file name as well. Because all other run modes will only be performed one partition at a time, this additional check is only used for scope mode. Additionally, some older runs do not include the partition name in the name of the Client and Source files, so omitting this check when not needed is required for backwards compatibility.

The existance of the run is then checked in the ANALYSIS database using the following query:
`select ANALYSISID,VERSIONMAJORID,VERSIONMINORID,RUNNUMBER,ANALYSISTYPE,PARTITIONNAME from analysis a join partition b on a.partitionid=b.partitionid where runnumber=$(RUNNUMBER)`
For scope mode, an additional parameter is added so the database will only return rows for the current partition that is being checked. If the run is found in the database, a check is performed to verify that the ANALYSISID, VERSIONMAJORID, and VERSIONMINORID fields are filled.

The `validate_db()` function will then return two booleans. The first will return `True` if the SiStripCommissioningClient and SiStripCommissioningSource files exist. The second will return `True` if the three aforementioned fields in the database are filled.

#### 7. Determine whether the analysis has run properly

If the run time, EDM file, SiStripCommissioning files, and ANALYSIS databse checks are all `True`, the run number will be added to the analyzedruns.txt file. However, if any checks fail, the run will be passed through the `analyze_runs()` function a second time, but with the `rerun=True` parameter. If the run goes through the analysis workflow a second time and everything is good, it will be added to the analyzedruns.txt file. However, if the run fails the analysis validity checks after rerunning the analysis, it will be appended to the failedruns.txt file along with the list of checks that it passed and failed.

Users will be required to periodically check the failedruns.txt file to see why a run failed the analysis integrity checks and continue to rerun the analysis.

#### 8. Wait for 1 hour, and go to step 2

After all of the new runs have gone through the workflow, the cron-job will sleep for 1 hour. Once it has finished sleeping, it will go to *Step 2* and see if any new runs exist. If it finds new runs, it will continue the workflow. If not, it will sleep for another 1 hour.

The amount of time that the cron-job sleeps for can be modified by changing the `frequency` variable in the `main()` function.

# NOTE: If the run mode is not in our list of modes to analyze, it will always be returned from get\_runlist(). Need to decide where we should store these run numbers

## Old framework

The previous cron-job workflow can be found in the oldWorkflow directory
