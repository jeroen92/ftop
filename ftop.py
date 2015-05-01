#!/usr/local/bin/python

# Copyright (c) 2015 Jeroen Schutrup
# See LICENSE for licensing information

from ftop.proc import *
import time, optparse

VERSION = '0.1'

USAGE = 'ftop.py [-ch] [-d lookupdepth] [-i interval] [-m mountpoint]\n\n\
ftop, version %s - Copyright (c) 2015 Jeroen Schutrup\n\
ftop is a filesystem monitoring tool for FreeBSD, operating at the VFS layer. It\'s main purpose is to monitor I/O by filename \
' % VERSION

parser = optparse.OptionParser(usage=USAGE)
parser.add_option('-c', '--cumulative', action='store_true', dest='cumulative', help='Display cumulative statistics, instead of purging existing data at every refresh.')
parser.add_option('-i', '--interval', type='int', dest='interval', default=2, help='The refresh interval.')
parser.add_option('-l', '--lookupdepth', type='int', dest='lookupDepth', default=5, help='Number of parent folder names to lookup per file.')
parser.add_option('-f', '--forcelookup', action='store_true', dest="forceLookup", help="Perform a namelookup of all objects under the specified mountpoint. Doing so will cause extra I/O!.")
parser.add_option('-m', '--mountpoint', type='str', dest='pathname', default='/', help='Mountpoint of filesystem to monitor. Defaults to `/`.')
options, args = parser.parse_args()

procMgr = ProcessManager(options)

try:
  procMgr.startMainProgram()
except KeyboardInterrupt:
  procMgr.quitMainProgram()
  exit()
