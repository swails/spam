"""
This packages checks for the necessary programs so we can run the calculations
that need to be run with external programs
"""
from __future__ import division
from spam.exceptions import ExternalProgramError

CPPTRAJ_NAME = 'cpptraj'
NAMD_NAME = 'namd2'

def which(progname):
   """ Searches the PATH for the given program and returns the full path """
   import os
   from os import path
   def is_exe(filename):
      return path.exists(filename) and os.access(filename, os.X_OK)

   # Split the program name
   filepath, filename = path.split(progname)

   # If it is specified via a path, and it's executable, return it as found
   if filepath and is_exe(progname):
      return progname

   # Otherwise, search everywhere in the PATH
   for spath in os.getenv('PATH').split(os.pathsep):
      if is_exe(path.join(spath, filename)):
         return path.join(spath, filename)

   # If we haven't found it yet, it's not in there
   return None

def check_progs(fix_traj=True, calc_energies=True):
   """
   Check which programs we need. We need cpptraj if we need to fix trajectories
   to work with SPAM, and we need NAMD if we want to calculate the pair
   interaction energies
   """
   global CPPTRAJ_NAME, NAMD_NAME
   programs = {'cpptraj' : None, 'namd' : None}
   if fix_traj:
      prog = which(CPPTRAJ_NAME)
      if prog is None:
         raise ExternalProgramError("Could not find cpptraj [%s]" % 
                                    CPPTRAJ_NAME)
      programs['cpptraj'] = prog
   if calc_energies:
      prog = which(NAMD_NAME)
      if prog is None:
         raise ExternalProgramError("Could not find namd [%s]" % NAMD_NAME)
      programs['namd'] = prog

   return programs

def test(args):
   """ Testing suites """
   from optparse import OptionParser, OptionGroup

   parser = OptionParser()
   group = OptionGroup(parser, "Testing the 'which' function",
                       "Options to test the program finding function")
   group.add_option('--which', dest='which', metavar='PROGRAM', default=None,
                    help='Which program to search for. No default.')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   if opt.which is not None:
      # Test the which function
      print("which(%s) returns %s" % (opt.which, which(opt.which)))

