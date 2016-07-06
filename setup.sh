#!/bin/sh

# This script is invoked via [setup.sh $BINDIR $PYTHON] which passes us the
# directory where the programs should be installed and which Python executable
# we should use. If either is missing, we just stop.

if [ $# -ne 2 ]; then
	echo "Bad usage of `basename $0`: `basename $0` <BINDIR> <PYTHON>"
	exit 1
fi

$2 -c "from spam import *" || exit 1
/bin/cp -LR spam $1/

sed -e "s@/usr/bin/env python@$2@g" < SPAM.py > $1/SPAM.py
/bin/chmod +x $1/SPAM.py
