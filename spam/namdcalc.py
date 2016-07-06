"""
This module contains code that will run NAMD in order to get the pair
interaction energy between a desired water molecule and everybody else
"""
from __future__ import division
import os
import re
import numpy as np
from spam.exceptions import (VersionWarning, SpamVariableWarning, SpamTypeError,
                             FileExists, InputError, SpamNamdWarning,
                             NoFileExists, SpamNamdError)
from spam import AmberParm

overwrite = False

MAXPROCS = 0

def get_num_procs():
   """ 
   This returns the number of processors we should use.  The best way of doing
   this is to use the multiprocessing module, but this was only introduced in
   Python 2.6, so we will optionally pull the number of CPUs from the
   environment variable SPAM_NCPUS or use the multiprocessing module if it's not
   set
   """
   global MAXPROCS
   if MAXPROCS > 0: return MAXPROCS

   if os.getenv('SPAM_NCPUS') is None:
      try:
         from multiprocessing import cpu_count
         return cpu_count()
      except ImportError:
         pass
      # I like the multiprocessing module better, but this will parse the
      # /proc/cpuinfo file and extract the number of processors listed in
      # there
      cpure = re.compile(r'processor\s*:\s*(\d+)')
      rematch = cpure.findall(open('/proc/cpuinfo', 'r').read())
      return max(1, len(rematch))
   else:
      try:
         return int(os.getenv('SPAM_NCPUS'))
      except ValueError:
         raise SpamVariableWarning(("SPAM_NCPUS is [%s] but I expected an " +
                   "integer. Using only 1 CPU for NAMD calculations.") % 
                   os.getenv('SPAM_NCPUS'))
   
   # We should never get here, but if we do, just pretend we want 1 processor
   return 1

# This is a sample NAMD input file taken from Guanglei's original SPAM calc.
# probably a better way of doing this, but this is fine for now
NAMD_INPUT = """# SHAKE
rigidBonds all
useSettle on
rigidDieOnError off

# PME
PME=on
PMEGridSpacing %(gridspace)f
cellBasisVector1 %(xvec)f 0 0
cellBasisVector2 0 %(yvec)f 0
cellBasisVector3 0 0 %(zvec)f

# Basics
timestep 2
temperature 0

# Force field parameters 
cutoff 12
switching on
switchdist 10
pairlistdist 14
exclude scaled1-4
1-4scaling 0.8333333
scnb 2
amber on
parmfile %(prmtop)s
ambercoor %(inpcrd)s
outputname %(output)s
binaryoutput no

# Pairwise decomposition (interaction energy)
pairInteraction on 
pairInteractionSelf off
pairInteractionFile %(pdb)s
pairInteractionCol O
pairInteractionGroup1 1
pairInteractionGroup2 2

# colvar
colvars off 

# TCL 
set ts 1000

coorfile open dcd %(inptraj)s

while { ![coorfile read] } {
   firstTimestep \\$ts
   run 0
   incr ts 1000
}

coorfile close
"""

def write_input(pdbname, inptraj, topology, pmegrid=1.0, incrd_name='dummy.crd',
                input_name='_SPAM_namd_input', namd_output='_SPAM_namd_output'):
   """ Sets up and writes a NAMD input file from the given options """
   global overwrite, NAMD_INPUT
   # Make sure topology is an AmberParm
   if not isinstance(topology, AmberParm):
      raise SpamTypeError("namdcalc.write_input expects AmberParm instance!")

   # Make sure we have box information
   if not topology.ptr('ifbox'):
      raise InputError("%s is not set up for periodic simulations!" % topology)
   try:
      a, b, c = tuple(topology.parm_data['BOX_DIMENSIONS'][1:])
   except KeyError:
      raise InputError("%s does not have BOX_DIMENSIONS set!" % topology)

   # Set up infile for writing if necessary
   if hasattr(input_name, 'write'):
      infile = input_name
   else:
      if not overwrite and os.path.exists(input_name):
         raise FileExists("%s exists. Not overwriting" % input_name)
      infile = open(str(input_name), 'w')

   # Set up a dictionary for substitution into the NAMD string
   
   options = {'gridspace' : float(pmegrid), 'xvec' : a, 'yvec' : b, 'zvec' : c,
              'pdb' : str(pdbname), 'prmtop' : topology, 'inpcrd' : incrd_name,
              'output' : namd_output, 'inptraj' : inptraj}

   infile.write(NAMD_INPUT % options)

def run_namd(pdbname, inptraj, topology, pmegrid=1.0, incrd_name='dummy.crd',
             input_name='_SPAM_namd_input', namd_output='_SPAM_namd_output'):
   from subprocess import Popen
   from spam.checkprogs import check_progs

   global overwrite

   programs = check_progs()
   namd = programs['namd']

   # Write the input file
   write_input(pdbname, inptraj, topology, pmegrid, incrd_name, input_name,
               namd_output)

   nproc = '+p%d' % get_num_procs()

   if not overwrite and os.path.exists('%s.out' % namd_output):
      raise FileExists("%s exists. Not overwriting" % ("%s.out" % namd_output))
   outfile = open("%s.out" % namd_output, 'w')
   process = Popen([namd, nproc, input_name], stdout=outfile, stderr=outfile)

   if process.wait():
      raise SpamNamdWarning("NAMD exited with non-zero status!")

class NamdPairOutput(object):
   """ Parses a NAMD output file with PairInteraction turned on """
   def __init__(self, output_file = None):
      """ Constructor for NamdPairOutput object """
      if output_file is not None and not isinstance(output_file, str):
         raise SpamTypeError('NamdPairOutput requires string output file name!')

      self.data = {}

      if output_file is not None:
         self.parse_output_file(output_file)

   def _get_file_info(self, infile):
      """ Read through input file and get the number of frames analyzed """
      # Get the energy keys
      key_list = []
      for line in infile:
         if line[:7] == 'ETITLE:': 
            key_list = line.split()[1:]
            nframes = 1
            break
      # Look for each ETITLE: line and count them to determine # of frames
      for line in infile:
         if line[:7] == 'ETITLE:':
            nframes += 1
      # Rewind the file back to the beginning
      infile.seek(0)
      if len(key_list) == 0:
         raise SpamNamdError("Bad NAMD output file %s!" % self.output_file_name)
      return nframes, key_list

   def parse_output_file(self, fname=None):
      """ 
      Parses the output file and puts the data into the data dict keyed by the
      title of that energy contribution
      """
      if fname is None and self.output_file_name is None:
         raise SpamNamdWarning("I have no file to parse!")
      if fname is not None:
         if not os.path.exists(fname):
            raise NoFileExists("Could not find NAMD output file %s" % fname)
         infile = open(fname, 'r')
         self.output_file_name = fname
      nframes, key_list = self._get_file_info(infile)
      for key in key_list:
         self.data[key] = np.ndarray(nframes)
      rawline = infile.readline()
      frame = 0
      while rawline:
         if rawline[:7] == 'ETITLE:':
            infile.readline()
            words = infile.readline().split()
            for i, dat in enumerate(words):
               if i == 0: continue
               self.data[key_list[i-1]][frame] = float(dat)
            frame += 1
         rawline = infile.readline()
   
   def filter_output_file(self, infoobj, peaknum):
      """ 
      This filters the data in the output file, stripping out the omitted points
      and resizing the data arrays so that only the data we are interested in is
      kept
      """
      from spam.spaminfo import SpamInfo
      if not isinstance(infoobj, SpamInfo):
         raise SpamTypeError("Expected SpamInfo to filter_output_file!")
      if not isinstance(peaknum, int):
         raise SpamTypeError("Expected integer peak number!")
      for i, idx in enumerate(infoobj.included_frames(peaknum)):
         for key in self.data:
            self.data[key][i] = self.data[key][idx]
      # We have now moved all of the data from frames we want to include down
      # into the first num_included_frames sections of the various arrays. Now
      # we can simply resize all of the numpy arrays and ignore the data we're
      # chopping off
      for key in self.data:
         self.data[key].resize(infoobj.num_included_frames(peaknum))

def test(args):
   from optparse import OptionParser, OptionGroup
   from spam import checkprogs
   from spam.spaminfo import SpamInfo
   import sys

   parser = OptionParser()
   parser.add_option('-O', '--overwrite', dest='owrite', default=False,
                     action='store_true', help='Overwrite existing files')
   group = OptionGroup(parser, 'Write input file',
                       'Test writing the input file')
   group.add_option('-p', '--prmtop', dest='prmtop', metavar='FILE',
                    default=None, help='Input prmtop file')
   group.add_option('-c', '--inpcrd', dest='inpcrd', metavar='FILE',
                    default=None, help='Input Amber crd file')
   group.add_option('-i', '--input-name', dest='input_name', metavar='FILE',
                    default=None, help='Name of input file to write')
   group.add_option('-g', '--grid-spacing', type='float', metavar='FLOAT',
                    dest='grid_space', default=1.0, help='PME Grid spacing ' +
                    'to use for calculation. (Default %default)')
   group.add_option('-y', '--inptraj', dest='inptraj', metavar='FILE',
                    default=None, help='Input trajectory file to analyze')
   group.add_option('-o', '--output-name', dest='outfile', metavar='FILE',
                    default=None, help='Name of NAMD output file to use')
   group.add_option('--pdb', dest='pdb', metavar='FILE', default=None,
                    help='Name of the input PDB with interactions turned on')
   parser.add_option_group(group)
   group = OptionGroup(parser, "Run NAMD", "Options to run NAMD")
   group.add_option('--run-namd', dest='run_namd', default=False, 
                    action='store_true', help='Run NAMD to get energies')
   group.add_option('-n', '--namd', dest='namd', metavar='EXE', default=None,
                    help='Name of the NAMD executable to use')
   parser.add_option_group(group)
   group = OptionGroup(parser, "Parse NAMD Output",
                       "Options to parse the NAMD output file")
   group.add_option('--parse', dest='toparse', metavar='FILE', default=None,
                    help='An output file to parse and print details about')
   group.add_option('--info', dest='info', metavar='FILE', default=None,
                    help='Input spam.info file to use to filter results')
   group.add_option('--peak', dest='peak', metavar='INT', default=0,
                    help='Which peak to apply the spam.info filter to. (' +
                    'Default %default)', type='int')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args)

   global overwrite
   overwrite = opt.owrite

   if opt.input_name is not None and not opt.run_namd:
      if (opt.prmtop is None or opt.inptraj is None or opt.outfile is None or
          opt.pdb is None):
         print 'Error: You must specify -y/--inptraj, --pdb, -p/--prmtop, ',
         print 'and -o/--output-name with -i/--input-name'
         sys.exit(1)
      
      print 'Writing input file %s' % opt.input_name
      write_input(opt.pdb, opt.inptraj, AmberParm(opt.prmtop),
                  pmegrid=opt.grid_space, incrd_name=opt.inpcrd,
                  input_name=opt.input_name, namd_output=opt.outfile)

   if opt.run_namd:
      if opt.namd is not None:
         checkprogs.NAMD_NAME = opt.namd

      run_namd(opt.pdb, opt.inptraj, AmberParm(opt.prmtop),
               pmegrid=opt.grid_space, incrd_name=opt.inpcrd,
               input_name=opt.input_name, namd_output=opt.outfile)
   
   if opt.toparse is not None:
      outf = NamdPairOutput(opt.toparse)

      print 'Parsed %s. Statistics' % opt.toparse
      print '  Avg TOTAL energy: %f' % (
            sum(outf.data['TOTAL']) / len(outf.data['TOTAL']))

      print '  Std Dev TOTAL   : %f' % (outf.data['TOTAL'].std())
      print '  Num of frames   : %d' % (len(outf.data['TOTAL']))

      if opt.info is not None:
         outf.filter_output_file(SpamInfo(opt.info), opt.peak)

         print 'Filtered %s. Statistics' % opt.toparse
         print '  Avg TOTAL energy: %f' % (
               sum(outf.data['TOTAL']) / len(outf.data['TOTAL']))
   
         print '  Std Dev TOTAL   : %f' % (outf.data['TOTAL'].std())
         print '  Num of frames   : %d' % (len(outf.data['TOTAL']))
