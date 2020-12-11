# SiStripCronJob

This code runs in the background of the srv-s2b17-29-01 and srv-s2b17-30-01 service machines and automatically analyze new strip calibration as new runs are taken. Repository contains the following scripts and subdirectories:

* oldWorkflow -
    Directory containing scripts used in previous cron-job script
* README.md -
    This file
* FULLDOCUMENTATION.md -
    In depth description of code workflow
* setup\_env.sh -
    Setup cmssw environment and setup database configuration
* analyzedruns.txt -
    List of runs that have been verified as succesfully analyzed by the cron-job script
* failedruns.txt -
    List of runs that cron-job has attempted to analyze but one or more of the analysis integrity verification checks have failed. The list includes a list of which checks the run passed and failed
* stripanalysis.py -
    Primary script which gets list of new runs and performs the analysis

#### Running the code interactively

To run the code interactively, first setup the environment using:
`source setup_env.sh`

The code can then be run via:
`python stripanalysis.py`

In the `main()` function of the script, two variables can be modified:
* `end_delay`:
    Parameter specifies how much time must have passed since a run ended before code will attempt to analyze it. Default is set to 2 hours.
* `frequency`:
    Parameter specifies how long the script will wait between runtimes. Default is set to 1 hour.

#### Running the script as daemon

Code is run as a system daemon when running in the background of the service machines. To run the code as a daemon...

