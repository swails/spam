"""
This module packages up all of the Python classes/functions that are needed to
run SPAM calculations (Guanglei Cui's water map method).  This will automate the
procedure of generating the trajectory, running the calculation, and processing
the results.
"""

__version__ = "1.0b"
__authors__ = "Jason M. Swails and Guanglei Cui"
__all__ = ['main', 'checkprogs', 'dx', 'traj', 'namdpdb', 'xyzpeaks',
           'namdcalc', 'spaminfo', 'spamstats', 'progressbar']

# Bring the necessary chemistry package components into spam namespace
import sys as _sys
import os as _os

if _os.getenv('AMBERHOME') is None:
   raise Exception('AMBERHOME is not set! Please install AmberTools 12 for SPAM.py')

_sys.path.append(_os.path.join(_os.getenv('AMBERHOME'), 'bin'))
from chemistry.amber.readparm import AmberParm
from chemistry.amber.mask import AmberMask
from chemistry.exceptions import MaskError as _maskerr

# Clean up the spam namespace
del _os, _sys

# bring all of the packages into the package namespace
from spam import *
