###
# All output of Dtrace is saved into statEntries, which will be consumed by the GUI.
# StatEntries are equal if the uid, pid, execname and filename(pathname) is identical.
###
class statEntry():
  def __init__(self, uid, pid, execname, filename, bytesRead, bytesWrite, iopsRead, iopsWrite):
    self.uid = str(uid)
    self.pid = str(pid)
    self.execname = execname
    self.filename = filename
    self.bytesRead = str(bytesRead)
    self.bytesWrite = str(bytesWrite)
    self.bytesTotal = int(bytesRead) + int(bytesWrite)
    self.iopsRead = str(iopsRead)
    self.iopsWrite = str(iopsWrite)
    #self.latencyRead = str(latencyRead)
    #self.latencyWrite = str(latencyWrite)
    self.count = 1

  ###
  # Merge two statEntries.
  ###
  def updateStats(self, entry):
    self.count += entry.count
    self.bytesRead = int(self.bytesRead) + int(entry.bytesRead)
    self.bytesWrite = int(self.bytesWrite) + int(entry.bytesWrite)
    self.bytesTotal = self.bytesRead + self.bytesWrite
    self.iopsRead = int(self.iopsRead) + int(entry.iopsRead)
    self.iopsWrite = int(self.iopsWrite) + int(entry.iopsWrite)
    #self.latencyRead = str(int(self.latencyRead) + int(entry.latencyRead) / self.count)
    #self.latencyWrite = str(int(self.latencyWrite) + int(entry.latencyWrite) / self.count)

  def __hash__(self):
    return (self.uid, self.pid, self.filename).__hash__()

  def __eq__(self, other):
    return self.__hash__() == other.__hash__()
