#!/usr/bin/env python
"""El Torito Boot Record Extractor

Extracts first boot record from bootable 'El Torito' CD-ROM.
Writes boot record to stdout unless -o, --outfile option specified.

Usage: python pytorito.py [OPTIONS]... SOURCE

Options:
      --help              show this help
  -i, --info              show information about the boot record
  -o ..., --outfile=...   write boot record to specified file
"""

__author__ = "Mitch Contla (mitch@barkingants.com)"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2011/08/23 17:52:00 $"
__copyright__ = "Copyright (c) 2011 Mitch Contla"
__license__ = "GPL 3 <http://www.gnu.org/licenses/>"

import os
import sys
import struct
import getopt
from UserDict import UserDict

secSize = 0x0800
vSecSize = 0x0200

def stripnulls(data):
    """Strip spaces and null characters."""
    return data.replace("\0", "").strip()

def getSector(filename, offset, size=vSecSize, count=1):
    """Read sector from device or file.

    Takes filename, (sector) offset, size, and count."""
    try:
	f = open(filename, "rb", 0)
	try:
	    f.seek(offset * secSize, 0)
	    sector = f.read(size * count)
	finally:
	    f.close()
	return sector
    except IOError:
	print "Error accessing file."

def writeOutput(filename, data):
    try:
	f = open(filename, "wb")
	try:
	    f.write(data)
	finally:
	    f.close()
    except IOError:
	print "Error writing file."

def getCatalogAddress(filename):
    sector = getSector(filename, 17, secSize)
    if len(sector) == secSize:
	volDescriptor, isoIdent, version, elToritoIdent, address = struct.unpack('<B5sB32s32xL1973x', sector)
	if volDescriptor == 0 and isoIdent == "CD001" and version == 1 and stripnulls(elToritoIdent) == "EL TORITO SPECIFICATION":
	    return address
    else:
	return 0

class BootImageInfo(UserDict):
    def __init__(self, filename=None):
	UserDict.__init__(self)
	self["source"] = filename

class ElToritoCatalog(BootImageInfo):

    entryDataMap = {"header"		:   (  0,  1, "<B"   ),
		   "platform"		:   (  1,  2, "<B"   ),
		   "manufacturer"	:   (  4, 28, "<24s" ),
		   "checksum"		:   ( 28, 30, "<H"   ),
		   "key_bytes"		:   ( 30, 32, "<H"   ),
		   "bootable"		:   ( 32, 33, "<B"   ),
		   "media_type"		:   ( 33, 34, "<B"   ),
		   "load_seg"		:   ( 34, 36, "<H"   ),
		   "sector_cnt"		:   ( 38, 40, "<H"   ),
		   "load_addr"		:   ( 40, 44, "<L"   )}

    def __parse(self, filename):
	self.clear()
	self["cat_addr"] = getCatalogAddress(filename)
	if self["cat_addr"]:
	    catalog = getSector(filename, self["cat_addr"])[:64]
	    for entry, (start, end, format) in self.entryDataMap.items():
		self[entry] = struct.unpack(format, catalog[start:end])[0]
	    self["data_words"] = struct.unpack("<14H36x", catalog)

    def __setitem__(self, key, item):
	if key == "source" and item:
	    self.__parse(item)
	BootImageInfo.__setitem__(self, key, item)

    def isValid(self):
	if self["cat_addr"] != 0 and self["key_bytes"] == 0xAA55:
	    sum = 0
	    sum = sum + self["checksum"] + self["key_bytes"]
	    for n in self["data_words"]:
		sum += n
	    return not (sum & 0xffff)
	else:
	    return 0

    def isBootable(self):
	if self["bootable"] == 0x0088:
	    return 1
	else:
	    return 0

    def getDiskImage(self):
	"""Returns bootable disk image as string"""
	if self.isValid():
	    return getSector(self["source"], self["load_addr"], count=self["sector_cnt"])
	else:
	    return None

def usage():
    print __doc__

def main(argv):
    outfile = ''
    try:
        opts, args = getopt.getopt(argv, "hio:", ["help", "info", "outfile="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
	elif opt in ("-i", "--info"):
	    pass
        elif opt in ("-o", "--outfile"):
            outfile = os.path.normcase(arg)
    
    if not (len(args) == 1):
	print sys.argv[0] + ": Incorrect number of arguments.\n"
	usage()
	sys.exit()

    catalog = ElToritoCatalog(args[0])

    if catalog.isValid():
	print catalog
	if outfile:
	    if catalog.isBootable():
		writeOutput(outfile, catalog.getDiskImage())
	    else:
		print catalog["source"], ': Does not appear to be a bootable "El Torito" CD image.'
    else:
	print catalog["source"], ': "Booting catalog" does not validate.'
    
if __name__ == "__main__":
    main(sys.argv[1:])

