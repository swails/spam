"""
This module holds the global variables, like constants and file names
"""

from spam.checkprogs import CPPTRAJ_NAME, NAMD_NAME, which
from spam.main import FN_PRE

ENTRY_SIZE = 30

global_spam_files = {
   'cpptraj' : which(CPPTRAJ_NAME),
   'namd'    : which(NAMD_NAME),
   'prmtop'  : 'prmtop',
   'inptraj' : [],
   'dx'      : None,
   'output'  : None,
   'xyz'     : FN_PRE + 'peaks.xyz',
   'spaminfo': FN_PRE + 'spam.info',
   'traj'    : FN_PRE + 'spam.dcd',
   'pdb'     : FN_PRE + 'spam.pdb',
   'incrd'   : FN_PRE + 'dummy.inpcrd',
   'namdout' : FN_PRE + 'namd'
}
