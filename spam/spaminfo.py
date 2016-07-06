"""
This module contains classes that interact with the SPAM information file that
cpptraj prints out detailing which frames are analyzed, omitted, etc.
"""
from __future__ import division
import os
import re
from spam.exceptions import (NoFileExists, SpamInfoError)

class SpamInfo(object):
   """ Class dealing with spam info file """
   def __init__(self, fname = None):
      """ Constructor """
      # Keeps track of the sites and the omitted points for each site
      self.sites = []
      if fname is not None:
         self.parse_spam_info(fname)

   def parse_spam_info(self, fname):
      """ Parses the spam info file and populates sites """
      if not os.path.exists(fname):
         raise NoFileExists("SPAM info file %s cannot be found" % fname)
      infile = open(fname, 'r')
      line1re = re.compile(r'# There are (\d+) density peaks and (\d+) frames')
      line2re = re.compile(r'# Peak (\d+) has (\d+) omitted frames')

      rematch = line1re.match(infile.readline())
      if rematch is None:
         raise SpamInfoError("SPAM Info file %s is corrupt!" % fname)
      peaks, frames = rematch.groups()
      self.peaks, self.frames = int(peaks), int(frames)
      # Now we know how many peaks we have. Allocate our self.sites acoordingly
      self.sites = [[] for i in range(self.peaks)]
      # Parse every block now
      rawline = infile.readline()
      while rawline:
         rematch = line2re.match(rawline)
         if rematch is None:
            rawline = infile.readline()
            continue
         pknum, nf = rematch.groups()
         pknum, nf = int(pknum), int(nf)
         rawline = infile.readline()
         while rawline.strip():
            self.sites[pknum].extend([abs(int(i)) for i in rawline.split()])
            rawline = infile.readline()

   def num_included_frames(self, peaknum):
      """ Returns the number of valid frames for a given peak number """
      return self.frames - len(self.sites[peaknum])

   def num_excluded_frames(self, peaknum):
      """ Returns the number of invalid frames for a given peak number """
      return len(self.sites[peaknum])

   def excluded_frames(self, peaknum):
      """ Generator that returns an iterable list of excluded peak numbers """
      for val in self.sites[peaknum]:
         yield val

   def included_frames(self, peaknum):
      """ Generator that returns an iterable list of included peak numbers """
      # This one is more difficult. For performance, we will take advantage of
      # self.sites[] being sorted for every site, and yield every number from
      # 0 to frames, skipping a tracked frame number. When that tracked frame
      # number is skipped, we pick the next frame in the omitted list to track

      omit = self.sites[peaknum]
      nomit = len(omit)
      # If we have no omitted frames, special-case this
      if nomit == 0:
         for i in range(self.frames): yield i
      # Otherwise we have omitted frames, so 
      else:
         idx, fr = 0, omit[0]

         for i in range(self.frames):
            if i == fr:
               try:
                  idx += 1
                  fr = omit[idx]
               except IndexError:
                  idx = fr = 0 # done with omitted frames
               continue
            yield i

def test(args):
   """ Test the SpamInfo class """
   from optparse import OptionParser, OptionGroup

   parser = OptionParser()
   group = OptionGroup(parser, 'Spam Info', 
                       'Options to analyze the SPAM info file')
   group.add_option('-i', '--info', dest='info', default=None, 
                    metavar='FILE', help='Input spam.info file')     
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args)

   if opt.info is not None:
      info = SpamInfo(opt.info)
      print 'Analyzed SPAM info file [%s]:'
      print '   Number of sites:             %d' % info.peaks
      print '   Number of frames:            %d' % info.frames

      for i in range(info.peaks):
         print '   Number Excluded (site %3d) : %d' % (i,
               info.num_excluded_frames(i))
         print '   Number Included (site %3d) : %d' % (i,
               info.num_included_frames(i))

         # Now test the generators
         save = list(info.included_frames(i))
         omit = list(info.excluded_frames(i))
         thesum = save + omit
         thesum.sort()
         print '   Do the generators work? [%s]' % (
               (len(save) == info.num_included_frames(i)) and
               (len(omit) == info.num_excluded_frames(i)) and
               (thesum == range(info.frames))
                                                   )
