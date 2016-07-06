"""
This file is responsible for calculating the statistics of the free energy of
each water site.
"""
from __future__ import division
import numpy as np
from scipy.stats.kde import gaussian_kde
from spam.exceptions import SpamKdeError
from math import log10, exp

DG_BULK = -30.3 # Free energy of bulk water
DH_BULK = -22.2 # Enthalpy of bulk water

def calc_g_wat(enevec, sample_size, sample_num):
   """ Calculate the DELTA G of an individual water site """
   global DG_BULK, DH_BULK, BW
   kde1 = gaussian_kde(enevec)

   # Set up defaults
   if sample_size < 1: sample_size = len(enevec)
   sample_size = min(len(enevec), sample_size)
   sample_num = max(1, sample_num)

   enthalpy = np.zeros(sample_num)
   free_energy = np.zeros(sample_num)
   # We want to do "sample_num" subsamples with "sample_size" elements in each
   # subsample.  Loop over those now
   for ii in range(sample_num):
      # If sample_num is 1, then don't resample
      if sample_num == 1:
         skde = gaussian_kde(enevec)
      else:
         # Generate the subsample kernel
         skde = gaussian_kde(kde1.resample(sample_size))
      # Determine the widths of the bins from the covariance factor method
      binwidth = skde.covariance_factor()
      # Determine the number of bins over the range of the data set
      nbins = int(((skde.dataset.max() - skde.dataset.min()) / binwidth) + 0.5) \
            + 100
      # Make a series of points from the minimum to the maximum
      pts = np.zeros(nbins)
      for i in range(nbins): pts[i] = skde.dataset.min() + (i-50) * binwidth
      # Evaluate the KDE at all of those points
      kdevals = skde.evaluate(pts)
      # Get the enthalpy and free energy
      enthalpy[ii] = np.sum(skde.dataset) / sample_size
      free_energy[ii] = -1.373 * log10(binwidth * 
                                      np.sum(kdevals * np.exp(-pts / 0.596)))

   # Our subsampling is over, now find the average and standard deviation
   dg_avg = np.sum(free_energy) / sample_num - DG_BULK
   dg_std = free_energy.std()
   dh_avg = np.sum(enthalpy) / sample_num - DH_BULK
   dh_std = enthalpy.std()
   ntds = dg_avg - dh_avg

   return (dg_avg, dg_std, dh_avg, dh_std, ntds)

def test(args):
   """ Sets up a test for calculating the spam statistics """
   from optparse import OptionParser, OptionGroup
   import sys, os
   from spam.namdcalc import NamdPairOutput
   from spam.spaminfo import SpamInfo

   parser = OptionParser()
   group = OptionGroup(parser, 'calc_g_wat',
                       'Tests the calc_g_wat function')
   group.add_option('-n', '--namd-out', dest='namdout', metavar='FILE',
                    default=None, help='Name of NAMD output file with energies')
   group.add_option('-i', '--info', dest='info', metavar='FILE',
                    default='SPAM info file')
   group.add_option('-s', '--site-id', dest='site', type='int', metavar='INT',
                    default=0, help='Site number that the NAMD output file ' +
                    'corresponds to starting from 0.  (Default %default)')
   group.add_option('--num-subsamples', dest='subsamples', type='int',
                    metavar='INT', default=1, help='Number of subsamples to ' +
                    'take of the data.  (Default %default)')
   group.add_option('--size-subsample', dest='subsize', type='int',
                    metavar='INT', default=0, help='How many points to ' +
                    'include in each subsample.  (Default %default)')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args)

   if opt.namdout is not None or opt.info is not None:
      if opt.namdout is None or opt.info is None:
         print 'I need both a NAMD output file and a SPAM info file!'
         sys.exit(1)
      print 'I am analyzing the %d-th site with the NAMD output ' % opt.site
      print 'file %s and SPAM info file %s\n' % (opt.namdout, opt.info)
      namdout = NamdPairOutput(opt.namdout)
      namdout.filter_output_file(SpamInfo(opt.info), opt.site)
      print len(namdout.data['TOTAL'])
      for val in namdout.data['TOTAL']: print val
      retvals = calc_g_wat(namdout.data['TOTAL'], opt.subsize, opt.subsamples)
      print '%14s |%14s |%14s |%14s | %14s' % ('<G>', 'Std. Dev. G.',
                                               '<H>', 'Std. Dev. H.', '-TS')
      print '-' * (80)
      print '%14.4f |%14.4f |%14.4f |%14.4f | %14.4f' % retvals
