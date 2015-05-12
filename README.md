# ftop
ftop is a filesystem monitoring tool for FreeBSD, tracing read and write calls to the Virtual File System. It's main feature is to trace I/O by filename.

### Usage
Make sure the DTrace kernel module is loaded. Use `kldload dtraceall` if it's not. For more information, launch ftop with *--help* to see all available flags and arguments.

### Issues
**Ftop isn't showing me any I/O activity, while there is certainly some I/O going on**

If the I/O is occuring on a volume which is not mounted on '/', then specify the mountpoint using the *--mountpoint* argument.

**Some filenames are marked as < Unknown >**

VFS didn't cache the filenames for those files. This can be caused if:
- The files are newly created
- The files are located on an exported share, i.e. NFS export, and besides nfsd no local processes are using the file

In order to solve this issue, launch ftop with the *--forcelookup* flag. This will effectively perform a `find <mountpoint> | xargs stat`. Beware that this operation will cause some I/O to be performed.

**Some pathnames are not fully displayed**

Ftop will lookup a maximum of 5 parent folders by default. To increment this value, use the *--lookupdepth* argument.

### License
See the LICENSE file, located in the root of the git repository for licensing information.
