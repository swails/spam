"""
The main driver for SPAM calculations. This contains all of the driving 
functions which can be called either through a GUI driver or a command-line
based driver.  The CL-based driver is included in the main function here.

All arguments to all methods in this class are assumed to be basic immutable
types that can be extracted from the command-line (that is, str, int, float,
bool, etc.) except for logfile, which is an open file object (or something
with a 'write' attribute) and the topology file is an AmberParm object
"""
from __future__ import division
import os
import sys
from spam import AmberMask
from spam import AmberParm
from spam import (checkprogs, dx, namdcalc, namdpdb, spaminfo,
                  spamstats, traj, xyzpeaks)
from spam.exceptions import *

# Filename prefix
FN_PRE = '_SPAM_'

def setup_peaks_file(trajins, 
                     gridmask, 
                     center,
                     xsize,
                     ysize,
                     zsize,
                     solventmask,
                     dxout,
                     resolution,
                     padding,
                     radius,
                     cutoff,
                     peakout,
                     top,
                     logfile,
                     cpptraj
                    ):
   """ This sets up the peak file that can be edited """
   # Make sure all trajins exist
   if not isinstance(trajins, list):
      raise SpamTypeError("trajin list is expected to be 'list' object!")
   for fname in trajins:
      if not os.path.exists(fname):
         raise NoFileExists("File [ %s ] cannot be found" % fname)

   try:
      tmpmask = AmberMask(top, gridmask)
   except MaskError:
      raise SpamTypeError("%s is not a valid Amber mask!" % gridmask)
   try:
      tmpmask = AmberMask(top, solventmask)
   except MaskError:
      raise SpamTypeError("%s is not a valid Amber mask!" % solventmask)

   if resolution < 0.01 or resolution > 2:
      raise InputError(("Bad resolution value [%d] -- reasonable values are " +
                        "between 0.01 and 2") % resolution)

   if padding < 0 or padding > max(top.parm_data['BOX_DIMENSIONS'][1:]) / 2:
      raise InputError(("Unreasonable padding value [%f]. It should be no " +
                        "smaller than 0 and no larger than the box") % padding)

   if radius < 1 or radius > 3:
      raise InputError(("Unreasonable oxygen radius [%f]. Pick a value " +
                        "between 1 and 3 Angstroms") % radius)

   # Now call the function
   traj.create_spam_grid(trajins, gridmask=gridmask, solventmask=solventmask,
             dx=dxout, resolution=resolution, cutoff=cutoff, padding=padding,
             radius=radius, peakout=peakout, topology=top, logfile=logfile,
             cpptraj=cpptraj)
   
def reorder_trajectory(trajin,
                       peakin,
                       trajout,
                       solventmask,
                       site_shape,
                       info,
                       site_size,
                       cpptraj,
                       top,
                       logfile,
                       pdbout,
                       dummycrd
                      ):
   """ 
   This is the general wrapper for creating the re-ordered trajectory as well
   as some of the other coordinate files (like a template PDB and a dummy
   input coordinate file) that are needed for the NAMD energy calculation
   """
   # Make sure the peak file exists
   if not os.path.exists(peakin):
      raise NoFileExists("Cannot find peak file %s!" % peakin)
   # Check the solvent mask
   try:
      tmpmask = AmberMask(top, solventmask)
   except MaskError:
      raise SpamTypeError("%s is not a valid Amber mask!" % gridmask)

   # Check for legal input values
   if site_shape.lower() not in ('box', 'sphere'):
      raise InputError("Site shape (%s) must be 'box' or 'sphere'!" % 
                       site_shape.lower())
   # Call the main driver for this functionality
   traj.traj_from_peaks(trajin, peakin, trajout, solventmask=solventmask,
            site_shape=site_shape.lower(), info=info, site_size=site_size,
            cpptraj=cpptraj, topology=top, logfile=logfile, pdbout=pdbout,
            dummycrd=dummycrd)

def run_namd(pdbname, inptraj, top, inpcrd, namd_output, peakfile, logfile,
             progress):
   """ Runs NAMD over a trajectory to generate energies """
   import math
   if not os.path.exists(pdbname):
      raise NoFileExists("Cannot find template PDB file %s!" % pdbname)
   if not os.path.exists(inptraj):
      raise NoFileExists("Cannot find input trajectory %s!" % inptraj)
   # Find out the residue of our first water
   firstwat = top.parm_data['RESIDUE_LABEL'].index('WAT')
   # Load our PDB file
   pdbtemplate = namdpdb.read_pdb(pdbname)
   # Load our peaks file
   peaklist = xyzpeaks.read_xyz_peaks(peakfile)
   # Format our numbers to have the correct number of leading zeroes when
   # necessary, but always the fewest leading zeroes possible.
   numdigits = int(math.log10(len(peaklist)))
   # Loop over every peak we have
   logfile.write("Beginning NAMD calculations on %d sites\n" % len(peaklist))
   progress.initialize(len(peaklist))
   for i in range(len(peaklist)):
      # Generate a PDB file then unlabel the residue
      pdbtemplate.label_residue(firstwat + i)
      tmppdbname = '%s.%s' % (pdbname, str(i).zfill(numdigits))
      tmpoutname = '%s.%s' % (namd_output, str(i).zfill(numdigits))
      pdbtemplate.write_to_pdb(tmppdbname)
      pdbtemplate.unlabel()
      logfile.write("NAMD: Calculating site %%%dd\n" % numdigits % (i+1))
      namdcalc.run_namd(tmppdbname, inptraj, top, incrd_name=inpcrd,
                 input_name=FN_PRE+'namd_input.%s' % (str(i).zfill(numdigits)),
                 namd_output=tmpoutname)
      progress.update()

def spam_energies(namd_output, info, sample_size, num_subsamples, output):
   """ 
   This method calculates all of the SPAM energies and generates an output file
   with all of the statistics.
   """
   import math
   import warnings
   global overwrite
   try:
      sample_size = int(sample_size)
      num_subsamples = int(num_subsamples)
   except TypeError, err:
      raise SpamTypeError(str(err))

   if not hasattr(output, 'write'):
      if not overwrite and os.path.exists(output):
         raise FileExists("%s output file exists. NOT overwriting" % output)
      outfile = open(output, 'w')
   else:
      outfile = output

   infoobj = spaminfo.SpamInfo(info)

   # Write the header
   outfile.write('# SITE %14s %14s %14s %14s %14s\n' % ('<G>', 'Std. Dev. G',
                 '<H>', 'Std. Dev. H', '-T<S>'))
   sfx = int(math.log10(infoobj.peaks))
   # Now loop through every peak and calculate the SPAM energies
   for i in range(infoobj.peaks):
      # Some versions of scipy will spit out a deprecation warning, despite
      # the fact that it is scipy itself that is using a deprecated feature.
      # So squash that warning here, then get rid of that filter
      namdout = namdcalc.NamdPairOutput('%s.%s.out' % (namd_output, 
                                        str(i).zfill(sfx)) )
      namdout.filter_output_file(infoobj, i)
      warnings.filterwarnings(action="ignore", category=DeprecationWarning)
      stats = spamstats.calc_g_wat(namdout.data['TOTAL'],
                                   sample_size, num_subsamples)
      warnings.resetwarnings()
      outfile.write('%6d' % i + (' %14.7f' * 5) % stats + '\n')

def set_overwrite(owrite=True):
   """ Universally sets all overwrite variables in each module """
   global overwrite
   overwrite = owrite
   dx.overwrite = owrite
   namdcalc.overwrite = owrite
   namdpdb.overwrite = owrite
   traj.overwrite = owrite
   xyzpeaks.overwrite = owrite

def main():
   from optparse import OptionParser, OptionGroup
   import signal
   from spam.__init__ import __version__
   from spam.progressbar import ProgressBar

   # Set up a custom excepthook to deal with uncaught exceptions
   debug = True
   def excepthook(exception_type, exception_value, tb):
      """ 
      Replaces excepthook so we can control the printing of tracebacks. Those
      are helpful for debugging purposes, but may be unsightly to users. debug
      set above controls this behavior, and a CL flag allows users to set this.
      """
      import traceback
      if debug: traceback.print_tb(tb)
      sys.stderr.write('%s: %s\n' % (exception_type.__name__, exception_value))
   sys.excepthook = excepthook

   # Set up a signal handler for interrupts
   def interrupt_handler(*args, **kwargs):
      raise BaseSpamError("SPAM interrupted!")
   signal.signal(signal.SIGINT, interrupt_handler)

   usage = '%prog [options] traj1 traj2 traj3 ... trajN'
   epilog = ('This is a wrapper for running SPAM calculations, divided up into',
             'the following steps: (1) Density calculation/grid creation, (2)',
             'Peak identification and trajectory re-ordering, (3) Energy',
             'calculation (via NAMD), parsing, and postprocessing to generate',
             'the final SPAM statistics for each site')

   parser = OptionParser(usage=usage, epilog=' '.join(epilog), 
                         version='SPAM.py Version: %s' % __version__)
   parser.add_option('-O', '--overwrite', dest='owrite', default=False,
                     action='store_true', 
                     help='Allow overwriting of existing files')
   parser.add_option('-d', '--debug', dest='debug', default=False,
                     action='store_true', help='Print verbose tracebacks to ' +
                     'aid in debugging various portions of this script')
   parser.add_option('--cpptraj', dest='cpptraj', metavar='EXE', 
                     default='cpptraj', help='Specific cpptraj program to ' +
                     'use.  If this is not specified, I will search the PATH ' +
                     'for a program called \'cpptraj\'')
   parser.add_option('--namd', dest='namd', metavar='EXE', default='namd',
                     help='Specific NAMD program to use.  If this is not ' +
                     'specified, I will search the PATH for a program called ' +
                     "'namd'.")
   group = OptionGroup(parser, 'Files', 'The options in this group deal with ' +
                 'the names of some of the intermediate files that are ' +
                 'generated. They may apply to multiple parts of the SPAM ' +
                 'calculation (i.e. as input to one and output to another)')
   group.add_option('-p', '--prmtop', dest='prmtop', metavar='FILE',
                    default='prmtop', help='This is the AMBER topology file ' +
                    'for the system you wish to analyze.  It must be a ' +
                    'solvated topology file with periodic boundary conditions' +
                    '. It is used as input in multiple locations. ' +
                    '(Default %default)')
   group.add_option('--logfile', dest='logfile', metavar='FILE', default=None,
                    help='File to dump all of the diagnostic information to ' +
                    'throughout the course of the SPAM calculation. By ' +
                    'default all information is dumped to standard output')
   group.add_option('--peak', dest='peakfile', metavar='FILE',
                    default=FN_PRE+'peaks.xyz', help='XYZ file that contains ' +
                    'a carbon atom at the center of each site location. This ' +
                    'output from the Grid Creation and input to Trajectory ' +
                    'Reordering and Running NAMD.  (Default %default)')
   group.add_option('--spam-info', dest='info', metavar='FILE',
                    default=FN_PRE+'spam.info', 
                    help='File containing information ' +
                    'about which frames are analyzed and omitted in the SPAM ' +
                    'analysis. This is output from Trajectory Reordering and ' +
                    'input for SPAM Energies.  (Default %default)')
   group.add_option('--traj-file', dest='traj', metavar='FILE', 
                    default=FN_PRE+'spam.dcd', 
                    help='Reordered trajectory file used ' +
                    'for energy calculations.  Output from Reorder ' +
                    'Trajectory and input for Running NAMD. (Default ' +
                    '%default)')
   group.add_option('--pdb', dest='pdb', metavar='FILE', 
                    default=FN_PRE+'spam.pdb',
                    help='PDB file to write out. Template needed by NAMD to ' +
                    'compute pair interaction energies.  It is output from ' +
                    'Trajectory Reordering and input for Running NAMD.  ' +
                    '(Default %default)')
   group.add_option('--inpcrd', dest='inpcrd', metavar='FILE',
                    default=FN_PRE+"dummy.inpcrd", help='This dummy inpcrd ' +
                    'file is created by Reorder Trajectory and needed by ' +
                    'Running NAMD, but is not generally useful. (Default ' +
                    '%default)')
   group.add_option('--namd-output', dest='namdout', metavar='FILE_PREFIX',
                    default=FN_PRE+'namd', help='Prefix of the name to apply ' +
                    'to NAMD output files.  Real file names will have ' +
                    '".#.out" appended, where # corresponds to the peak ' +
                    'number.  Created by Running NAMD and used as input for ' +
                    'SPAM Energies.  (Default %default)')
   group.add_option('--spam-prefix', dest='prefix', metavar='STRING',
                    default='_SPAM_', help='Prefix to use for intermediate '
                    'files (Default %default)')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'Grid Creation Options',
                 'These options govern the calculation of the water density ' +
                 'and the identification of where the peaks in the density ' +
                 'are located.  Note, some of the output files in this ' +
                 'section are the same as the input options in others.')
   group.add_option('--calculate-grid', dest='calcgrid', default=False,
                    action='store_true', help='Calculate the grid and peak ' +
                    'locations according to the options below')
   group.add_option('--resolution', dest='resolution', metavar='FLOAT',
                    default=0.5, help='Distance in Angstroms between ' +
                    'adjacent grid points.  (Default %default)')
   group.add_option('--grid-mask', dest='gridmask', metavar='AMBER_MASK',
                    default='!(:WAT,Na+,Cl-,Mg+,Br-,Cs+,F-,I-,Rb+)',
                    help='Mask around which to define the water peak density ' +
                    'grid. (Default %default)')
   group.add_option('--center', dest='center', metavar='X,Y,Z', default=None,
                    help='Center of the grid. If provided, --grid-mask will be '
                    'ignored, and --xsize, --ysize, and --zsize must all be '
                    'provided as well.  By default, use --grid-mask instead')
   group.add_option('--xsize', dest='xsize', default=0, type='float',
                    metavar='FLOAT', help='Size of the grid in the X-dimension.'
                    ' This is only used if --center is provided')
   group.add_option('--ysize', dest='ysize', default=0, type='float',
                    metavar='FLOAT', help='Size of the grid in the Y-dimension.'
                    ' This is only used if --center is provided')
   group.add_option('--zsize', dest='zsize', default=0, type='float',
                    metavar='FLOAT', help='Size of the grid in the Z-dimension.'
                    ' This is only used if --center is provided')
   group.add_option('--solvent-mask', dest='solventmask', metavar='AMBER_MASK',
                    default=':WAT@O=', help='Mask of atoms to use to ' +
                    'calculate the water density. (Default %default)')
   group.add_option('--padding', dest='padding', metavar='FLOAT', default=3.0,
                    help='Distance in Angstroms around --grid-mask to extend ' +
                    'the grid when calculating water densities.  (Default ' +
                    '%default Angstroms)', type='float')
   group.add_option('--radius', dest='radius', metavar='FLOAT', default=1.3,
                    help='How large to consider the Oxygen atom of the ' +
                    'solvent in Ang. VMD uses 1.3.  (Default %default)')
   group.add_option('--cutoff', dest='cutoff', metavar='FLOAT', default=0.05,
                    help='Lowest value of water density to consider eligible ' +
                    'for peak identification. (Default %default)', type='float')
   group.add_option('--dx', dest='dx', default=None, help='A file to dump ' +
                    'the density information in IBM Data Explorer format. ' +
                    'This format is readable in VMD.  Not written by default.')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'Trajectory Reordering', 'This section has the' +
                 ' options pertaining to how hot spots are identified from ' +
                 'an XYZ file containing the peak locations. This trajectory ' +
                 'file is then used to calculate all of the SPAM free ' +
                 'energies. NOTE: --solvent-mask from above options applies ' +
                 'here as well.')
   group.add_option('--reorder-traj', dest='reorder', default=False,
                    action='store_true', help='Flag to enable generating ' +
                    'a reordered trajectory suitable for SPAM energy calcs.')
   group.add_option('--site-shape', dest='site_shape', metavar='BOX|SPHERE',
                    default='box', help='Do we conider the shape of the ' +
                    'various sites to be a sphere or a box (default)?')
   group.add_option('--site-size', dest='site_size', metavar='FLOAT',
                    default=2.5, help='Size of each site (diameter of ' +
                    'sphere or side of box) in Angstroms. (Default %default)')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'Running NAMD', 'This section has the options ' +
                 'pertaining to running NAMD to calculate the energies of ' +
                 'each site')
   group.add_option('--run-namd', dest='run_namd', default=False,
                    action='store_true', help='This option will enable ' +
                    'calculation of interaction energies for each site for ' +
                    'each frame.')
   group.add_option('--nproc', dest='nproc', default=0, type='int',
                    metavar='INT', help='Number of processors to use for ' +
                    'NAMD calculations. By default, use as many processors ' +
                    'as the current host has (including virtual processors)')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'SPAM Energies', 'The options in this section ' +
                 'pertain to parsing NAMD output files and generating the ' +
                 'final SPAM free energies.  It performs statistical ' +
                 'analysis of the results via subsampling (of which boot-' +
                 'strapping is a subset).')
   group.add_option('--spam-energies', dest='spam_energies', default=False,
                    action='store_true', help='Flag to toggle calculation of ' +
                    'SPAM energies.')
   group.add_option('--subsamples', dest='num_samples', type='int', default=1,
                    metavar='INT', help='Number of subsamples to take from ' +
                    'the existing data set. Standard deviations and averages ' +
                    'are calculated from this set. (Default %default)')
   group.add_option('--sample-size', dest='sample_size', type='int', default=-1,
                    metavar='INT', help='How many data points to take at ' +
                    'random, with replacement, from the interaction energy ' +
                    'data set.  (Default is the number of points in the set)')
   group.add_option('--spam-output', dest='spamout', metavar='FILE',
                    default='spam.out', help='Name of the final output file ' +
                    'for SPAM energies. (Default %default)')
   group.add_option('--clean', dest='clean', default=False, action='store_true',
                    help='Remove external files with the %s prefix' % FN_PRE)
   parser.add_option_group(group)

   opt, arg = parser.parse_args()

   debug = opt.debug

   # Set the default overwrites from my CL
   global overwrite
   set_overwrite(opt.owrite)

   # Override default programs
   checkprogs.CPPTRAJ_NAME = opt.cpptraj
   checkprogs.NAMD_NAME = opt.namd

   # Find the programs we need
   programs = checkprogs.check_progs(opt.calcgrid or opt.reorder,
                                     opt.spam_energies)

   # Make sure we supplied at least _some_ input trajectories...
   if not arg and (opt.calcgrid or opt.reorder):
      raise InputError("You gave me no trajectories to process! See the help")

   # Open up the log file unbuffered
   if opt.logfile is None:
      logfile = os.fdopen(sys.stdout.fileno(), 'w', 0)
      progress = ProgressBar(output=logfile)
   elif not overwrite and os.path.exists(opt.logfile):
      raise FileExists("%s exists.  Will not overwrite" % opt.logfile)
   else:
      logfile = open(opt.logfile, 'w', 0)
      progress = ProgressBar(output=logfile, allowbackspace=False)

   # Create the AmberParm object
   topology = AmberParm(opt.prmtop)
   if not topology.valid:
      raise InputError("%s is not a valid Amber topology file!" % opt.prmtop)
   if topology.ptr('ifbox') < 1:
      raise InputError(("Amber topology file %s does not have periodic box " +
                       "information!") % opt.prmtop)

   # Grid setup and creation
   if opt.calcgrid:
      setup_peaks_file(arg, opt.gridmask, opt.center, opt.xsize, opt.ysize,
                       opt.zsize, opt.solventmask, opt.dx, opt.resolution, 
                       opt.padding, opt.radius, opt.cutoff, opt.peakfile, 
                       topology, logfile, programs['cpptraj'])
   
   # Trajectory file reordering
   if opt.reorder:
      reorder_trajectory(arg, opt.peakfile, opt.traj, opt.solventmask,
                         opt.site_shape, opt.info, opt.site_size,
                         programs['cpptraj'], topology, logfile, opt.pdb,
                         opt.inpcrd)

   # running NAMD
   if opt.run_namd:
      namdcalc.MAXPROCS = opt.nproc
      run_namd(opt.pdb, opt.traj, topology, opt.inpcrd, opt.namdout,
               opt.peakfile, logfile, progress)

   # Collecting the statistics
   if opt.spam_energies:
      spam_energies(opt.namdout, opt.info, opt.sample_size, opt.num_samples,
                    opt.spamout)

   # Remove temporary files
   if opt.clean:
      purge_list = [f for f in os.listdir('.') if f.startswith(FN_PRE)]
      for fname in purge_list:
         os.remove(fname)
