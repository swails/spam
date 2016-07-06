"""
This module provides a nifty progress bar for those parts of the calculation
that can be tracked for completion.
"""
from __future__ import division
import sys
from spam.exceptions import SpamProgressError

BAR_SIZE = 50

class ProgressBar(object):
   """ Progress bar class """
   def __init__(self, output=sys.stdout, end_count=None, allowbackspace=True):
      """ Instantiates the ProgressBar """
      self.output = output
      self.allowbackspace = allowbackspace
      if end_count is not None:
         self.initialize(end_count)

      self.count = 0

   def initialize(self, end_count):
      """ Load how many end counts we have """
      if self.allowbackspace:
         self.printmethod = self.print_backspace
         self.output.write('Progress: [' + ' '*BAR_SIZE + ']   0.0%')
         self.ndrawn = 0
      else:
         self.printmethod = self.print_nobackspace
         self.output.write('Progress: [   0% ')
         self.percent_done = 0

      self.end_count = end_count

   def printmethod(self):
      """ If we hit this, we haven't initialized our progress bar yet """
      raise SpamProgressError("Uninitialized progress bar!")

   def print_nobackspace(self):
      """ Prints an increment of the progress """
      percent_done = int(self.count / self.end_count * 100)
      if self.count == self.end_count:
         self.output.write("100%  ] Done.\n")
         return
      if percent_done - 10 >= self.percent_done:
         self.output.write('%d%% ' % percent_done)
         self.percent_done = percent_done // 10 * 10

   def print_backspace(self):
      """ Prints an increment of the progress """
      frac_done = self.count / self.end_count
      ndraw = int(frac_done * BAR_SIZE)
      new_to_draw = ndraw - self.ndrawn
      if new_to_draw:
         # Back up to where we need to update
         n_backups = 8 + BAR_SIZE - self.ndrawn
         self.output.write('\b'*n_backups + ':' * new_to_draw + ' ' *
               (n_backups - 8 - new_to_draw) + '] %5.1f%%' % (frac_done * 100))
      else:
         # Just update the percentage
         self.output.write('\b' * 6 + '%5.1f%%' % (frac_done * 100))
      
      self.ndrawn = ndraw
      # We are done!
      if frac_done == 1:
         self.output.write(' Done.\n')

   def update(self):
      """ Adds 1 to the progress counter """
      self.count += 1
      self.printmethod()

   def reset(self, end_count=None):
      """ Allow resetting of the progress bar """
      # Delete the end_count and reset the printmethod to the original
      if end_count is None:
         self.initialize(self.end_count)
      else:
         self.initialize(end_count)

      self.count = 0

def test(args):
   """ Tests the progress bar """
   from optparse import OptionParser, OptionGroup
   import os
   from time import sleep

   parser = OptionParser()
   group = OptionGroup(parser, "Testing the Progress Bar",
                       "These options test how the progress bar updates and "
                       "appears")
   group.add_option('--no-backspace', dest='backspace', default=True,
                    action='store_false', help='Allow back-spacing in the '
                    'Progress Bar.')
   group.add_option('--size', dest='size', metavar='INT', default=10,type='int',
                    help='How many events until completion? (Default %default)')
   group.add_option('-t', '--time', dest='time', default=1.0, type='float',
                    metavar='FLOAT', help='Number of seconds between progress '
                    'updates. (Default %default)')
   group.add_option('-r', '--repeat', dest='repeat', type='int', metavar='INT',
                    default=1, help='Number of times to run/display the '
                    'progress bar. (Default %default)')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   def run(progress):

      for i in range(opt.size):
         sleep(opt.time)
         progress.update()

   sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

   progress = ProgressBar(sys.stdout, opt.size, opt.backspace)

   for i in range(opt.repeat):
      if i > 0: progress.reset(opt.size)
      run(progress)
