"""
This module contains code responsible for creating the SPAM trajectory
"""
from __future__ import division

from os.path import exists
import re
import sys
from subprocess import Popen, PIPE
from spam import AmberParm

from spam.exceptions import (InternalError, FileExists, PeriodicBoundaryError,
                             ExternalProgramError, InputError, VersionError)

overwrite = False

def create_spam_grid(trajin,             # Name of input trajectory(ies)
                     trajout = None,     # Name of output trajectory
                     gridmask = None,    # the mask that defines the grid
                     solventmask = None, # the mask that defines the solvent
                     start = 1,          # The first frame to analyze
                     stop = 10000000,    # The last frame to analyze
                     interval = 1,       # Analyze every 'interval' frame
                     dx = None,          # Name of dx file, if any, to write
                     resolution = 0.5,   # Angstroms between grid points
                     site_shape = 'box', # Shape of site (box or sphere)
                     info = 'spam.info', # Output file with the spam info
                     site_size = 2.5,    # Size of the site in Angstroms
                     cutoff = 0.05,      # Minimum density to consider
                     padding = 3.0,      # Space around gridmask to define grid
                     radius = 1.3,       # How large to consider Oxygen atom 
                     peakout = 'spam_peaks.xyz', # Name of output XYZ peak file
                     cpptraj = None,     # cpptraj executable
                     topology = None,    # topology file (AmberParm class)
                     logfile = None,     # Where to dump the cpptraj information
                     pdbout = None,      # Name of a PDB file to dump out
                     dummycrd = '_SPAM_dummy.inpcrd', # dummy inpcrd file
                     center = None,      # A user-defined center of the grid
                     xsize = 0,          # User-defined size of the grid (X-dim)
                     ysize = 0,          # User-defined size of the grid (Y-dim)
                     zsize = 0           # User-defined size of the grid (Z-dim)
                    ):
   global overwrite

   if cpptraj is None:
      raise InternalError("create_spam_traj: Missing cpptraj!")

   if topology is None:
      raise InternalError("create_spam_traj: Missing topology!")
   elif not isinstance(topology, AmberParm):
      raise TypeError("create_spam_traj: topology must be of type AmberParm!")

   # Only write the dummycrd file if we write the output trajectory
   if trajout is None:
      dummycrd = None

   # Check that we're not overwriting files if we don't want to
   if not overwrite:
      if trajout is not None and exists(trajout):
         raise FileExists("%s exists. Not overwriting" % trajout)
      if dx is not None and exists(dx):
         raise FileExists("%s exists. Not overwriting" % dx)
      if peakout is not None and exists(peakout):
         raise FileExists("%s exists. Not overwriting" % peakout)
      if dummycrd is not None and exists(dummycrd):
         raise FileExists("%s exists. Not overwriting" % dummycrd)

   # Build the spam call for cpptraj
   spamcall = ("spamtraj peakout %s info %s resolution %f site_size %f "
               "radius %f cutoff %f padding %f ") % (
               peakout, info, resolution, site_size, radius, cutoff, padding)
   if gridmask is not None and center is None:
      spamcall += "solute_mask \"%s\" " % gridmask
   if solventmask is not None:
      spamcall += "solvent_mask \"%s\" " % solventmask
   if dx is not None:
      spamcall += "out_dx %s " % dx
   if trajout is not None:
      spamcall += "out %s " % trajout
   if site_shape.lower() == 'sphere':
      spamcall += "sphere "
   elif site_shape.lower() != 'box':
      raise InputError("Site shape must be either 'box' or 'sphere'!")
   if center is not None:
      # Get rid of spaces
      center = center.replace(' ', '')
      # Remove a trailing comma
      if center.endswith(','):
         center = center[:len(center)-2]
      # Check that the format is "#,#,#"
      centerre = re.compile(r'((?:\d*\.\d+)|(?:\d+\.*\d*)),((?:\d*\.\d+)|(?:\d+\.*\d*)),((?:\d*\.\d+)|(?:\d+\.*\d*))')
      rematch = centerre.match(center)
      if not rematch or len(centerre.sub('', center).strip()) != 0:
         raise InputError("Illegal 'center' value: %s" % center)
      # Check xsize, ysize, zsize
      if xsize <= 0 or ysize <= 0 or zsize <= 0:
         raise InputError("If you specify 'center', then xsize, ysize, and "
                          "zsize must all be specified >0")
      spamcall += "center %s xsize %f ysize %f zsize %f " % (center,
            xsize, ysize, zsize)

   spamcall += "dcd" # we want output format to be DCD

   _cpptraj_call(cpptraj, trajin, spamcall, topology, start, stop, interval,
                 logfile, dummycrd, pdbout)


def _cpptraj_call(cpptraj, trajin, spamcall, topology, start, stop, interval,
                  logfile, dummycrd=None, pdbout=None):
   """ Actually calls cpptraj from a given Spam call """
   cpptraj_call = ''
   if type(trajin).__name__ == 'list':
      for fname in trajin:
         cpptraj_call += "trajin %s %d %d %d\n" % (fname, start, stop, interval)
   else:
      cpptraj_call += "trajin %s %d %d %d\n" % (trajin, start, stop, interval)
   
   # Ensure proper imaging.  autoimage should do the trick sans arguments
   cpptraj_call += "autoimage\n"

   # Add the spam call to the input stream
   cpptraj_call += spamcall + "\n"
   if dummycrd is not None:
      cpptraj_call += 'outtraj %s restart onlyframes 1\n' % dummycrd
   if pdbout is not None:
      cpptraj_call += 'outtraj %s pdb onlyframes 1\n' % pdbout

   # Open our output file, and determine if we have to keep it open afterwards
   if logfile is None:
      output = sys.stdout
   elif hasattr(logfile, 'write'):
      output = logfile
   elif type(logfile).__name__ == 'str':
      if exists(logfile):
         raise FileExists("%s exists. Not overwriting." % logfile)
      output = open(logfile, 'w')
   # Now it's time to spawn this process and create the trajectory
   process = Popen([cpptraj, str(topology)], stdin=PIPE,stdout=PIPE,stderr=PIPE)
   out, err = process.communicate(cpptraj_call)
   if process.wait():
      # cpptraj failed. Write to the output and raise an exception
      output.write('\n'.join((out, err)))
      raise ExternalProgramError("cpptraj failed creating SPAM trajectory!")


   # Scan the output file for a missing command -- that means we don't have the
   # cpptraj version with the spamtraj command available
   notfoundre = re.compile("Warning: Unknown Command spamtraj")
   if notfoundre.findall(out):
      output.write('\n'.join((out, err)))
      raise VersionError("cpptraj does not have the command spamtraj!")

   # Otherwise, it seemed to work. Write the output and bail
   output.write('\n'.join((out, err)))

def traj_from_peaks(trajin,             # Name of input trajectory(ies)
                    peakin,             # Name of input XYZ file with peaks
                    trajout,            # Name of output trajectory
                    solventmask = None, # the mask that defines the solvent
                    start = 1,          # The first frame to analyze
                    stop = 10000000,    # The last frame to analyze
                    interval = 1,       # Analyze every 'interval' frame
                    site_shape = 'box', # Shape of site (box or sphere)
                    info = 'spam.info', # Output file with the spam info
                    site_size = 2.5,    # Size of the site in Angstroms
                    cpptraj = None,     # cpptraj executable
                    topology = None,    # topology file (AmberParm class)
                    logfile = None,     # Where to dump the cpptraj information
                    pdbout = None,      # Name of a PDB file to dump out
                    dummycrd = '_SPAM_dummy.inpcrd' # dummy inpcrd file for NAMD
                   ):
   """ This function will generate a topology file from an input XYZ peak """
   from spam.xyzpeaks import read_xyz_peaks

   global overwrite
   try:
      peaks = read_xyz_peaks(peakin)
   except (SpamBaseWarning, SpamBaseException), err:
      raise type(err)("Badly formatted (or non-existing) XYZ peak file!")
   
   if cpptraj is None:
      raise InternalError("create_spam_traj: Missing cpptraj!")

   if topology is None:
      raise InternalError("create_spam_traj: Missing topology!")
   elif not isinstance(topology, AmberParm):
      raise TypeError("create_spam_traj: topology must be of type AmberParm!")

   if trajout is None:
      raise InputError("Expected output trajectory in traj_from_peaks!")

   # Check that we're not overwriting files if we don't want to
   if not overwrite:
      if exists(trajout):
         raise FileExists("%s exists. Not overwriting" % trajout)
      if dummycrd is not None and exists(dummycrd):
         raise FileExists("%s exists. Not overwriting" % dummycrd)

   spamcall = "spamtraj out %s peakin %s site_size %f info %s " % (trajout, 
                              peakin, site_size, info)
   if solventmask is not None:
      spamcall += "solvent_mask \"%s\" " % solventmask
   if site_shape.lower() == 'sphere':
      spamcall += "sphere "
   elif site_shape.lower() != 'box':
      raise InputError("Site shape must be either 'box' or 'sphere'!")

   spamcall += 'dcd'

   _cpptraj_call(cpptraj, trajin, spamcall, topology, start, stop, interval,
                 logfile, dummycrd, pdbout)

def test(args):
   """ Testing suite """
   from optparse import OptionParser, OptionGroup
   import os

   from spam.exceptions import BaseSpamError
   from spam.checkprogs import which

   usage = 'python %prog [Options] [traj1] [traj2] ... [trajN]'
   parser = OptionParser(usage=usage)
   group = OptionGroup(parser, 'create_spam_traj',
                       'Input options for create_spam_traj')
   group.add_option('-O', '--overwrite', dest='owrite', default=False,
                    action='store_true', help='Allow file overwriting')
   group.add_option('-o', '--outtraj', dest='outtraj', metavar='FILE',
                    default='spam.dcd', 
                    help='Output trajectory. Default (%default)')
   group.add_option('-g', '--gridmask', dest='gridmask', metavar='MASK',
                    default=None, help='Mask around which to draw the grid')
   group.add_option('-s', '--solventmask', dest='solventmask', metavar='MASK',
                    default=None, help='Mask of atoms to consider as solvent')
   group.add_option('-b', '--begin', dest='startframe', metavar='INT', 
                    default=1, type='int',
                    help='First frame to read in to cpptraj (Default %default)')
   group.add_option('-e', '--end', dest='endframe', metavar='INT', type='int',
                    default=10000000, help='Last frame to read in to cpptraj ' +
                    '(Default %default)')
   group.add_option('-i', '--interval', dest='interval', metavar='INT',
                    type='int', default=1, help='Interval between adjacent ' +
                    'frames we analyze (Default %default)')
   group.add_option('-x', '--dx', dest='dx', default=None, metavar='FILE',
                    help='Output DX file')
   group.add_option('-r', '--resolution', dest='res', type='float', default=0.5,
                    help='Grid spacing (Angstroms) in each coordinate ' +
                    '(Default %default Angstroms)')
   group.add_option('--info', dest='info', metavar='FILE', default='spam.info',
                    help='Output file with SPAM information (Default %default)')
   group.add_option('--site-size', dest='sitesize', type='float', default=2.5,
                    metavar='FLOAT',
                    help='Size of the water sites (Default %default)')
   group.add_option('-c', '--cutoff', type='float', dest='cut', metavar='FLOAT',
                    default=0.05, help='Cutoff to determine background from ' +
                    'peaks. (Default %default)')
   group.add_option('-p', '--padding', default=3.0, dest='padding',
                    type='float', metavar='FLOAT',
                    help='Buffer around gridmask to include in grid ' +
                    '(Default %default Angstroms)')
   group.add_option('--radius', metavar='FLOAT', default=1.3, dest='radius',
                    type='float', help='Radius of oxygen atom for density ' +
                    'calculation. (Default %default for VMD compatibility)')
   group.add_option('--peakout', metavar='FILE', default=None, dest='peakout',
                    help='XYZ output file with carbons at peak centers.')
   group.add_option('-t', '--topology', dest='topology', default='prmtop',
                    metavar='FILE', help='Amber topology file corresponding ' +
                    'to input trajectories (Default %default)')
   group.add_option('--shape', dest='shape', default='box', 
                    metavar='BOX|SPHERE', help='Is our site defined by a box ' +
                    '(default) or a sphere?')
   group.add_option('--pdb', dest='pdb', default=None, metavar='FILE',
                    help='Name of PDB file to output')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'Input Peaks', 
                       'Options to read in existing peak locations from XYZ')
   group.add_option('--peakin', dest='peakin', default=None, metavar='FILE',
                    help='Input peak file to generate trajectory from')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   global overwrite
   overwrite = opt.owrite

   # Unbuffer stdout
   sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

   # Make sure we got some input trajectories
   if not arg:
      print >> sys.stderr, 'Error: No input trajectories supplied!'
      sys.exit(1)

   parm = AmberParm(opt.topology)
   
   if not parm.valid:
      print >> sys.stderr, 'Error: Invalid prmtop [%s]' % parm
      sys.exit(1)

   # Create the peak/traj/grid
   if opt.peakout is not None:
      create_spam_grid(arg, opt.outtraj, gridmask=opt.gridmask,
                    solventmask=opt.solventmask, start=opt.startframe,
                    stop=opt.endframe, interval=opt.interval, dx=opt.dx,
                    resolution=opt.res, site_shape=opt.shape.lower(),
                    info=opt.info, site_size=opt.sitesize, cutoff=opt.cut,
                    padding=opt.padding, radius=opt.radius, peakout=opt.peakout,
                    topology=parm, cpptraj=which('cpptraj'), pdbout=opt.pdb)

   if opt.peakin is not None:
      if opt.outtraj is None:
         print 'You MUST have an output trajectory for peakin!'
         sys.exit(1)
      traj_from_peaks(arg, opt.peakin, opt.outtraj, solventmask=opt.solventmask,
                      start=opt.startframe, stop=opt.endframe,
                      interval=opt.interval, site_shape=opt.shape.lower(),
                      info=opt.info, site_size=opt.sitesize, topology=parm,
                      cpptraj=which('cpptraj'), pdbout=opt.pdb)
