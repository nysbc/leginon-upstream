#!/bin/bash

export APPIONDIR=`dirname ${BASH_SOURCE[0]}`
export PYTHONPATH=$APPIONDIR/lib:$PYTHONPATH
export PATH=$APPIONDIR/bin:$PATH
export MATLABPATH=$MATLABPATH:$APPIONDIR/ace
