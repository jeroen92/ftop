# Copyright (c) 2015 Jeroen Schutrup
# See LICENSE for licensing information

import sys, subprocess, atexit, signal, time, multiprocessing, os, Queue
from ftop.proc import *
from ftop.ui import *

###
# The ProcessManager is responsible for IPC, and the forking and terminating of subprocesses.
###
class ProcessManager():
  def __init__(self, options):
    self.processes = []
    self.parsingQueue = multiprocessing.Queue()
    # The Manager() spawns another subprocess. See if it's possible to optimize this shared memory a bit.
    self.statisticList = multiprocessing.Manager().list()
    self.options = options

  ###
  # Spawn subprocesses and start GUI
  ###
  def startMainProgram(self):
    self.processes = [
      TraceFileIO(self.options, self.parsingQueue),
      ParseFileIO(self.parsingQueue, self.statisticList)]
    if self.options.forceLookup:
      statMountpoint = StatMountpoint(self.options)
      statMountpoint.start()
      print "Performing lookups. This may take a while, depending on the number of underlying objects."
    for process in self.processes:
      process.start()
    curses.wrapper(startUI, self.options, self.statisticList)

  ###
  # Sets the Event semaphore in all subprocesses and terminates the program
  ###
  def quitMainProgram(self):
    for process in self.processes:
      #print "Exiting %s with PID  %d" % ( process.name, process.pid )
      process.terminate()
      process.join()
      #print "Process %s with PID %d exited successfully" % ( process.name, process.pid )

class StatMountpoint(multiprocessing.Process):
  def __init__(self, options):
    multiprocessing.Process.__init__(self)
    self.name = 'StatMountpoint'
    self.exit = multiprocessing.Event()
    self.options = options
    args = './ftop/ext/lookup.sh -m %s' % self.options.pathname
    self.process = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  ###
  # Stat all files in the filesystem mounted under the specified mountpoint. Will terminate when finished.
  # See ftop/ext/lookup.sh for detailed info
  ###
  def run(self):
    try:
      while not self.exit.is_set():
        self.process.communicate()
        if not self.process.poll() is None:
          break
    except KeyboardInterrupt, SystemExit:
      self.terminate()

  ###
  # Set the Event mutex, and exit gracefully
  ###
  def terminate(self):
    if self.process.poll() is None:
      self.process.terminate()
      self.process.communicate()
    self.exit.set()
 
class TraceFileIO(multiprocessing.Process):
  def __init__(self, options, queue):
    multiprocessing.Process.__init__(self)
    self.name = 'TraceFileIO'
    self.exit = multiprocessing.Event()
    self.queue = queue
    self.options = options
    args = './ftop/ext/vfs.sh -d %2d -m %s' % ( self.options.lookupDepth, self.options.pathname )
    self.process = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=5)

  ###
  # Start the DTrace script located in ftop/ext/vfs.sh.
  # Poll for output and redirect it to the parsingQueue
  ###
  def run(self):
    try:
      out = ''
      while not self.exit.is_set():
        char = self.process.stdout.read(1)
        if char == '' and self.process.poll() != None:
          print "Dtrace exited"
          break
        if char == "\n":
          self.queue.put(out, False)
          out = ''
        else: out += char
    except KeyboardInterrupt, SystemExit:
      pass

  ###
  # Set the Event mutex, and exit gracefully
  ###
  def terminate(self):
    if self.process.poll() is None:
      # Process is still running
      self.process.terminate()
      self.process.communicate()
    self.exit.set()

class ParseFileIO(multiprocessing.Process):
  def __init__(self, parsingQueue, statistics):
    multiprocessing.Process.__init__(self)
    self.name = 'ParseFileIO'
    self.exit = multiprocessing.Event()
    self.parsingQueue = parsingQueue
    self.statistics = statistics

  ###
  # Poll the parsingQueue and create a statEntry object for every line in Dtrace's output
  # self.statistics is a list shared with the GUI. If the created object is equal to an
  # object in the queue, merge it into the existing obj.
  ###
  def run(self):
    try:
      while not self.exit.is_set():
        try:
          item = self.parsingQueue.get(False)
          item = item.split("\t")
          item = statEntry(
            item[0],
            item[1],
            item[2],
            item[3],
            item[4],
            item[5],
            item[6],
            item[7]
          )
          if item in self.statistics:
            for statIndex, statItem in enumerate(self.statistics):
              if statItem == item:
                statItem.updateStats(item)
                self.statistics[statIndex] = statItem
                break
          else:
            self.statistics.append(item)
        except Queue.Empty:
          pass
        time.sleep(0.2)
    except KeyboardInterrupt:
      pass

  ###
  # Set the Event mutex, and exit gracefully
  ###
  def terminate(self):
    self.exit.set()
