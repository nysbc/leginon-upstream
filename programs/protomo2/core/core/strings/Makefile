#
# Makefile [core/strings]
#
# Copyright ? 2012 Hanspeter Winkler
#


#
# definitions
#

include   ../../Makedefs

PRFX = strings

INCS = $(PRFX).h $(PRFX)module.h

OBJS = $(PRFX).o $(PRFX)module.o stringconcat.o stringreverse.o \
       stringseparate.o

EXTRAOBJS =

CFLAGS = $(CLIBOPT)
CPPFLAGS = -I../config -I../../include -I../../$(LIBPRFX)include $(CPPOPT)

EXTRACLEAN =


#
# make rules
#

include ../../make/Makecommon.dirs


#
# build dependencies
#

-include Makedeps
