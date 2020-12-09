#!/bin/bash

#source /nsfhome0/trackerpro/.bashrc

echo "-------------------------------------------------------------------"
date

getConfDb () { 
    MYCONF=$1;
    export CONFDB=`cat ~trackerpro/.passwords/confdb | egrep ^$MYCONF= | sed -e "s#^$MYCONF=##"`;
    if [ "$CONFDB" == "" ]; then
        export CONFDB=`cat ~trackerpro/.passwords/confdb | egrep ^CONFDB_$MYCONF= | sed -e "s#^CONFDB_$MYCONF=##"`;
    fi
}

# tests on env
if [ -n "`uname -n | grep vmepc`" -a "`whoami`" == "trackerpro" ] ; then
    :
elif [ -n "`uname -n | grep srv-s2b17-29`" -a "`whoami`" == "trackerpro" ] ; then
    :
elif [ -n "`uname -n | grep srv-s2b17-30`" -a "`whoami`" == "trackerpro" ] ; then
    :
elif [ -n "`uname -n | grep cmstracker029`" -a "`whoami`" == "xdaqtk" ] ; then
    :
elif [ -n "`uname -n | grep cmstracker040`" -a "`whoami`" == "xdaqtk" ] ; then
    echo "LALA"
 #    :
else
    echo "You are not running as trackerpro (on vmepcs) or xdaqtk (on cmstracker029, cmstracker040).";
    echo "This can cause problems during file moving, like loss of raw data.";
    echo "You don't want that to happen, probably, so please login as the appropriate user and try again.";
    exit 0;
fi

# Settings for basic directories
BASEDIR=/opt/cmssw
echo "  CMSSW base directory     : "$BASEDIR
DATALOC=/opt/cmssw/Data/closed
echo "  Temporary storage area   : "$DATALOC

# source CMSSW so we can query the database in the python script
cd /opt/cmssw/Stable/current/src
eval `scram runtime -sh`
cd /raid/cmssw/shifter/jmhogan/
getConfDb CONFDB_ONLINE
echo "  ConfDb account setting   : "$CONFDB

# Get the run range
RUNMIN=999999
RUNMAX=000000

for USCFILE in `ls $DATALOC | grep USC`; do
    RUN=`echo $USCFILE | cut -d. -f2`
    #echo "testing run ${RUN}"
    if [ "$RUN" -lt "$RUNMIN" ]; then
	RUNMIN=$RUN
    fi
    if [ "$RUN" -gt "$RUNMAX" ]; then
	RUNMAX=$RUN
    fi
done

# strip leading zeros
RUNMIN=$(expr $RUNMIN + 0)
RUNMAX=$(expr $RUNMAX + 0)

echo "found runmin = ${RUNMIN}"
echo "found runmax = ${RUNMAX}"

# run the python script to analyze all these runs
python -u bulkanalysis_analysisupload.py --runmin $RUNMIN --runmax $RUNMAX

echo "CRON done"

