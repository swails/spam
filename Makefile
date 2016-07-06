# This makefile will install SPAM as though it's part of AmberTools
include ../config.h

SHELL = /bin/sh

install:
	./setup.sh $(BINDIR) $(PYTHON)

serial: install

parallel:
	@echo "SPAM does not install in parallel"

docs:
	doxygen spamscript.Doxyfile

clean:
	-(find . -name "*.pyc" | /usr/bin/xargs /bin/rm)

uninstall:
	-/bin/rm -fr $(BINDIR)/spam $(BINDIR)/SPAM.py
