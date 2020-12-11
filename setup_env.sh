#!/bin/bash


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

# source CMSSW so we can query the database in the python script
cd "/opt/cmssw/Stable/current/" # sym-link to current cmssw version
eval `scram runtime -sh`
cd "/opt/cmssw/scripts/SiStripCronJob"
getConfDb CONFDB_ONLINE
echo "  ConfDb account setting   : "$CONFDB

#python -u stripanalysis.py

echo "CRON done"

