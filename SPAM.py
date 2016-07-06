#!/usr/bin/env python

import sys
import spam

if __name__ == '__main__':
   # No CL arguments means we use the GUI
   if len(sys.argv) < 2:
      from spam.gui.toplevel_app import SpamApp
      from Tkinter import Tk
      root = Tk()
      root.title('SPAM.Pie')
      root.resizable(False, False)
      app = SpamApp(root)
      root.mainloop()

   # CL arguments mean we use the CL interface
   else:
      # Go through the CL arguments and see if we tweaked our file name prefix.
      # Do it here before calling main so it will take effect.
      for i, arg in enumerate(sys.argv):
         key = arg
         if i >= len(sys.argv)-1:
            value = None
         else:
            value = sys.argv[i+1]
         if '=' in arg:
            # If it ends with "=", get rid of it and pull the next argument
            # Otherwise, split on the "=" and make the value
            if arg.endswith('='):
               key = arg[:len(arg)-1]
         # See if this is the key we're looking for
         if key.startswith('--spam-p') and key == '--spam-prefix'[:len(key)]:
            if value is not None and not sys.argv[i+1].startswith('-'):
               main.FN_PRE = value
      spam.main.main()
