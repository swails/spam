"""
This file provides the list of exceptions to be used throughout the SPAM
calculation in the various modules/packages
"""

class BaseSpamError(Exception):
   """ Raise this for a fatal error """
   pass

class BaseSpamWarning(Warning):
   """ Raise this for a non-fatal warning """
   pass

class SpamLoopBreak(Exception):
   """ This is an exception thrown to break out of a loop """
   pass

class ExternalProgramError(BaseSpamError):
   """ If an external program cannot be found """
   pass

class InternalError(BaseSpamError):
   """ This is raised if an API is used incorrectly """
   pass

class FileExists(BaseSpamError):
   """ This is raised if a file already exists """
   pass

class NoFileExists(BaseSpamError):
   """ This is raised if a file is needed, but is not there """
   pass

class WarnFileExists(BaseSpamWarning):
   """ This is a non-fatal file exist warning """
   pass

class PeriodicBoundaryError(BaseSpamError):
   """ This is raised if there is a problem with PBCs """
   pass

class VersionError(BaseSpamError):
   """ Raise this if our external program is a bad version """
   pass

class InputError(BaseSpamError):
   """ If an input variable for spam is no good... """
   pass

class MissingFile(BaseSpamError):
   """ If a necessary file is missing """
   pass

class UsageError(BaseSpamError):
   """ If you use something wrong """
   pass

class PDBRecordWarning(BaseSpamWarning):
   """ If the PDB line is not what we expect """
   pass

class SpamTypeError(BaseSpamError, TypeError):
   """ TypeError, but inherits from BaseSpamError as well """
   pass

class SpamAtomsWarning(BaseSpamWarning):
   """ If there is a problem with a collection of _Atoms """
   pass

class DxFileError(BaseSpamError):
   """ If there is a problem with a DX file """
   pass

class SpamGridError(BaseSpamError):
   """ If there is a problem with the grid """
   pass

class OutOfBoundsWarning(BaseSpamWarning):
   """ The grid doesn't extend quite as far as we'd like/think """
   pass

class SpamUninitializedPeak(BaseSpamError):
   """ If a peak has not been initialized """
   pass

class SpamPeakError(BaseSpamError):
   """ If there is an issue with the peak file """
   pass

class VersionWarning(BaseSpamWarning):
   """ 
   If there is a non-fatal version dependency that isn't quite met, but that
   can be dealt with via a (probably less-than-ideal) workaround
   """
   pass

class SpamVariableWarning(BaseSpamWarning):
   """ If there is a non-fatal error with a variable """
   pass

class SpamPeakWarning(BaseSpamWarning):
   """ If there is a non-fatal, but unusual issue with peaks """
   pass

class SpamNamdWarning(BaseSpamWarning):
   """ If there is a problem with NAMD """
   pass

class SpamNamdError(BaseSpamError):
   """ If there is a fatal problem with NAMD """
   pass

class SpamInfoError(BaseSpamError):
   """ If the SPAM info file is no good """
   pass

class SpamKdeError(BaseSpamError):
   """ If the KDE calculation botches up for some reason... """
   pass

class SpamProgressError(BaseSpamError):
   """ If there is a problem with the progress bar """
   pass

# Import MaskError from __init__.py (which imported from chemistry package)
from spam import _maskerr as MaskError
