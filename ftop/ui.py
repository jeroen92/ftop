# Copyright (c) 2015 Jeroen Schutrup
# See LICENSE for licensing information

import curses, time, Queue, select, sys
from ftop.obj import *

class UI(object):

  # In order to create a new column in the UI view, add a tuple to this array.
  # ( (number of characters + spacing!); columnname; object property that holds the value; Reverse ordering (False != int) )
  columns = [
    ( 7, 'PID', lambda statEntry: statEntry.pid, False ),
    ( 7, 'UID', lambda statEntry: statEntry.uid, False ),
    ( 20, 'EXECUTABLE', lambda statEntry: statEntry.execname, False),
    ( 10, 'KiB_READ', lambda statEntry: int(statEntry.bytesRead) / 1024, True ),
    ( 11, 'KiB_WRITE', lambda statEntry: int(statEntry.bytesWrite) / 1024, True ),
    ( 10, 'OPS_READ', lambda statEntry: statEntry.iopsRead, True ),
    ( 11, 'OPS_WRITE', lambda statEntry: statEntry.iopsWrite, True ),
    ( 0, 'FILENAME', lambda statEntry: statEntry.filename, False ),
  ]

  def __init__(self, window, options, statisticList):
    self.window = window
    self.options = options
    self.sharedStatistics = statisticList
    self.localStatistics = list()
    self.sortingColumn = 4
    self.sortingInverse = False

  ###
  # In/decrement the sortingColumn index by one.
  # Triggered when using the LEFT/RIGHT arrow keys
  ###
  def adjustColumnSorting(self, delta):
    previousSortingColumn = self.sortingColumn
    self.sortingColumn += delta
    self.sortingColumn = self.sortingColumn % len(UI.columns)

  ###
  # Inverse the sorting order from a -> z | z -> a
  ###
  def inverseColumnSorting(self):
    self.sortingInverse = not self.sortingInverse

  ###
  # Perform action corresponding to the key
  ###
  def handleUserInput(self, key):
    keyBindings = {
      curses.KEY_LEFT: lambda: self.adjustColumnSorting(-1),
      curses.KEY_RIGHT: lambda: self.adjustColumnSorting(1),
      curses.KEY_UP: lambda: self.inverseColumnSorting(),
      curses.KEY_DOWN: lambda: self.inverseColumnSorting(),
    }
    action = keyBindings.get(key)
    if action != None: action()

  ###
  # Infinite loop, continually polling for user input and refreshing the screen
  ###
  def startUI(self):
    poll = select.poll()
    poll.register(sys.stdin.fileno(), select.POLLIN | select.POLLPRI)
    while True:
      self.printScreen()
      try:
        events = poll.poll(self.options.interval * 1000)
      except Exception as ex:
        if ex.args[0] == 4: pass
        else: raise
      if events:
        key = self.window.getch()
        self.handleUserInput(key)

  ###
  # The shared object sharedStatistics has all (new) statEntry objects. If cumulative mode is set, all new objects
  # are merged into the local list of existing objects. Otherwise, copy the shared list to the local list.
  # Afterwards, the sharedList is emptied.
  ###
  def collectStatistics(self):
    if self.options.cumulative:
      localSet = set(self.localStatistics)
      sharedSet = set(self.sharedStatistics)
      # Create a set of duplicate entries
      duplicates = localSet.intersection(sharedSet)
      # Iterate over all duplicates, then find duplicate entry. Sum both and save them in localSet
      for obj in duplicates:
        for item in localSet:
          if item == obj: item.updateStats(obj)
      self.localStatistics = self.localStatistics + list(sharedSet - localSet)
    else:
      self.localStatistics = self.sharedStatistics[:]
    # While sorting, cast column value to int, if it is of type int
    if UI.columns[self.sortingColumn][3]:
      self.localStatistics.sort(key = lambda statEntry: int(apply(UI.columns[self.sortingColumn][2], [statEntry])), reverse=UI.columns[self.sortingColumn][3])
    else:
      self.localStatistics.sort(key = lambda statEntry: apply(UI.columns[self.sortingColumn][2], [statEntry]), reverse=UI.columns[self.sortingColumn][3])    
    # Inverse the sorting order, if inverse is set
    if self.sortingInverse:
      self.localStatistics = self.localStatistics[::-1]
    self.sharedStatistics[:] = []

  ###
  # Print the first two lines of the GUI
  ###
  def printHeader(self, windowDimensions):
    self.window.addstr(0, 2, "FTOP, version 0.1")
    self.window.addstr(1, 2, "Launch with --help for available options")
    totalIOHeader = "VFS I/O since last interval (%ss):" % self.options.interval
    # Iterate the sharedStatistics and sum all bytes read/write. Then, divide the sum by the interval (no. of seconds).
    totalIOValuesHeader = "Read: %s KiB/s, Write: %s KiB/s" % (
      (sum(int(statEntry.bytesRead) for statEntry in self.sharedStatistics) / int(self.options.interval)) / 1024,
      (sum(int(statEntry.bytesWrite) for statEntry in self.sharedStatistics) / int(self.options.interval)) / 1024
    )
    self.window.addstr(0, ( windowDimensions[1] / 2 ) - len(totalIOHeader) / 2 - 1, "%s" % totalIOHeader, curses.A_BOLD)
    self.window.addstr(1, ( windowDimensions[1] / 2 ) - len(totalIOValuesHeader) / 2 - 1, "%s" % totalIOValuesHeader)
    mountpointHeader = "Monitoring mountpoint: %s" % self.options.pathname
    lookupDepthHeader = "Name lookup depth: %s vnodes" % self.options.lookupDepth
    self.window.addstr(0, windowDimensions[1] - len(mountpointHeader) , "%s" % mountpointHeader)
    self.window.addstr(1, windowDimensions[1] - len(lookupDepthHeader), "%s" % lookupDepthHeader)

  ###
  # Key method to print all headers and statistics to the screen.
  ###
  def printScreen(self):
    curses.curs_set(0)
    maximumXY = self.window.getmaxyx()
    self.window.erase()
    self.printHeader(maximumXY)
    # Loop through all the columns
    for index, column in enumerate(UI.columns):
      if column[0] != 0:
        # Print the column with the defined length
        columnText = "%-*s" % ( column[0], column[1] )
      else:
        # If no length is defined (last column to the right), calculate it in order to use all available space on the screen
        length = maximumXY[1] - (sum([c[0] for c in UI.columns]))
        columnText = "%-*s" % ( length, column[1] )
      if index == self.sortingColumn: self.window.addstr(columnText, curses.A_BOLD)
      else: self.window.addstr(columnText, curses.A_REVERSE)

    self.collectStatistics()
    # Iterate all statistics
    for i in range(len(self.localStatistics)):
      if i + 1 >= ( maximumXY[0] - 3 ): break
      line = ''
      # Iterate column by column
      for column in UI.columns:
        # Format the current column's text
        columnText = "%-*s" % ( column[0], str(apply(column[2], [ self.localStatistics[i] ] )) )
        if column[0] != 0: padding = column[0] - len(columnText)
        # If the column length defined in UI.columns is zero, calculate maximum width to utilize all available space on the screen
        else: padding = maximumXY[1] - (sum([c[0] for c in UI.columns]) + len(columnText))
        # Append the spacing to the column text
        columnText = columnText + (' ' * padding)
        line += columnText
      self.window.addstr(i + 3, 0, line)
      line = ''
    self.window.refresh()

###
# Instantiate and start the user interface
# This function is consumed by the curses.wrapper
###
def startUI(window, options, statistics):
  ui = UI(window, options, statistics)
  ui.startUI()
