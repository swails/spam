"""
This module contains classes and subroutines for manipulating the peaks file
that is dumped in an XYZ format with each peak labeled as a carbon atom
"""
from __future__ import division
import os
from spam.exceptions import (SpamUninitializedPeak, NoFileExists, SpamPeakError,
                             SpamLoopBreak, SpamTypeError, FileExists,
                             SpamPeakWarning)

TINY = 1e-10
overwrite = False

class XyzPeak(object):
   """ This class is an X, Y, Z peak. Comparisons are done based on density """
   def __init__(self, x, y, z, density=-1.0):
      """ 
      Set up the cartesian coordinates and optionally the density of the peak
      """
      self.x, self.y, self.z = float(x), float(y), float(z)
      self.density = float(density)

   def set_density(self, density):
      """ Set the density of this peak """
      self.density = density

   def __eq__(self, other):
      global TINY
      _check_initialized(self, other)
      return abs(self.density - other.density) < TINY
   def __ge__(self, other):
      return self == other or self.density > other.density
   def __le__(self, other):
      return self == other or self.density < other.density
   def __gt__(self, other):
      return not self <= other
   def __lt__(self, other):
      return not self >= other

class XyzPeakList(list):
   """ This holds a list of XyzPeak objects """
   def append(self, obj):
      """ Override list append to make sure we only add XyzPeak objects """
      if not isinstance(obj, XyzPeak):
         raise SpamTypeError("Can only add XyzPeak objects to XyzPeakList!")
      list.append(self, obj)

   def extend(self, obj):
      """ Override list extend to make sure we only add XyzPeak objects """
      if not hasattr(obj, '__iter__'):
         raise SpamTypeError("Cannot 'extend' without iterable object!")
      for o in obj:
         if not isinstance(o, XyzPeak):
            raise SpamTypeError("Can only add XyzPeak objects to XyzPeakList!")
      list.extend(self, obj)

   def write_peaks(self, dest):
      """ Write the peaks to a destination """
      global overwrite
      if hasattr(dest, 'write'):
         outfile = dest
      else:
         if not overwrite and os.path.exists(str(dest)):
            raise FileExists("%s exists. Not overwriting" % dest)
         outfile = open(str(dest), 'w')
      if len(self) == 0:
         raise SpamPeakWarning("There are no peaks left!")
      outfile.write("%d\n\n" % len(self))
      for pk in self:
         outfile.write("C %f %f %f %f\n" % (pk.x, pk.y, pk.z, pk.density))
      

def _check_initialized(*args):
   """ Check that an object's density is > 0 """
   for obj in args:
      if obj.density < 0:
         raise SpamUninitializedPeak("Density of peak not set!")

def read_xyz_peaks(fname):
   """ Read a file with the number of peaks and return a list of XyzPeaks """
   if not os.path.exists(fname):
      raise NoFileExists("%s does not exist." % fname)
   infile = open(fname, 'r')

   # The first line has the number of peaks, the second is blank, and the
   # remaining lines contain all of the peaks in the format:
   # C <x> <y> <z> <density>
   # where they are whitespace-delimited.
   npeaks = int(infile.readline().strip())
   infile.readline() # eat the next line
   return_peaks = XyzPeakList()
   try:
      for line in infile:
         try:
            words = line.split()[1:]
            if not words: continue
            return_peaks.append(XyzPeak(*words))
         except TypeError, err:
            raise err
   except SpamLoopBreak:
      pass

   if len(return_peaks) != npeaks:
      raise SpamPeakError("Unexpected number of peaks. Found %d, expected %d" %
                          (len(return_peaks), npeaks))
   infile.close()
   return return_peaks

def test(args):
   from optparse import OptionParser, OptionGroup
   import sys

   usage = '%prog [options] [peak] [peak] ... [peak]'
   epilog = 'Will optionally remove the given list of [peak]s for output'
   parser = OptionParser(usage=usage, epilog=epilog)
   parser.add_option('-O', '--overwrite', dest='owrite', default=False,
                    action='store_true', help='Allow overwriting files')
   group = OptionGroup(parser, 'XYZ File', 
                       'This test the XYZ file manipulations')
   group.add_option('-i', '--input-peaks', dest='infile', metavar='FILE',
                    default=None, help='Input XYZ file with peak locations')
   group.add_option('-o', '--output-peaks', dest='outfile', metavar='FILE',
                    default=None, help='Output XYZ file with removed peaks')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   global overwrite
   overwrite = opt.owrite

   if opt.outfile is not None and opt.infile is None:
      print 'I need an input XYZ file to output one!'
      sys.exit(1)

   if opt.infile is not None:
      if not os.path.exists(opt.infile):
         print '%s does not exist!' % opt.infile

      peaks = read_xyz_peaks(opt.infile)

      # Now print out some info about the peaks
      print '%s peak file statistics:' % opt.infile
      print '   Number of peaks: %d' % len(peaks)
      print '   Largest density: %f' % max(peaks).density
      # Determine where the largest peak is
      maxpeak = max(peaks)
      for peak in peaks:
         if peak == maxpeak:
            tup = (peak.x, peak.y, peak.z)
            print '   Location of largest peak: {%f, %f, %f}' % tup

   if opt.outfile is not None:
      removals = [int(a) for a in arg]
      removals.sort()
      print '\nRemoving elements %s' % (' '.join(arg))
      while removals:
         del peaks[removals.pop()-1]
      print 'Writing peak output file %s' % opt.outfile
      # Now output our new file
      peaks.write_peaks(opt.outfile)

