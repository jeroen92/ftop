#!/bin/sh

# Copyright (c) 2015 Jeroen Schutrup
# See LICENSE for licensing information

usage () {
  echo "USAGE: $0 [-d 0..10] [-m <mountpoint>]" 1>&2; exit 1;
}


while getopts ":d:m:" opt;
do
  case $opt in
  d ) LOOKUP_DEPTH=$OPTARG
      if [ "$LOOKUP_DEPTH" -gt 10 ]
      then
        usage
      fi
      ;;
  m ) LOOKUP_PATH=$OPTARG
      ;;
  h ) usage
      ;;
  esac
done

LOOKUP="
vfs:vop:vop_read:entry, vfs:vop:vop_write:entry 
/this->namecache != NULL/{
  this->namecache = this->namecache != NULL ? (
    this->namecache->nc_dvp != NULL ? (
      this->namecache->nc_dvp->v_cache_dst.tqh_first != NULL ? this->namecache->nc_dvp->v_cache_dst.tqh_first : NULL
    ) : NULL
  ) : NULL;
  this->filename = this->namecache != NULL ? strjoin(this->namecache->nc_name, strjoin(\"/\", this->filename)) : this ->filename;
}
"

#for (( i = 0; i < $LOOKUP_DEPTH; i++ ))
if [ $LOOKUP_DEPTH -gt 0 ]
then
  for i in $(seq 1 $LOOKUP_DEPTH)
    do
      LOOKUPS="${LOOKUPS}${LOOKUP}"
  done
fi
dtrace -n '


#pragma D option quiet
#pragma D option strsize=4k

inline string MOUNT = "'$LOOKUP_PATH'";

vfs:vop:vop_read:entry, vfs:vop:vop_write:entry {
  this->bytes_read = this->bytes_write = 0;
}

vfs:vop:vop_read:entry, vfs:vop:vop_write:entry {
  this->namecache = args[0]->v_cache_dst.tqh_first != NULL ? args[0]->v_cache_dst.tqh_first : NULL;
  this->filename = this->namecache != NULL ? this->namecache->nc_name : "- Unknown -";
  this->mnt_name = stringof(args[0]->v_mount->mnt_stat.f_mntonname);
  this->vnode_hash = args[0]->v_hash;
}

vfs:vop:vop_read:entry {
  this->bytes_read = args[1]->a_uio->uio_resid;
}

vfs:vop:vop_write:entry {
  this->bytes_write = args[1]->a_uio->uio_resid;
}

'"$LOOKUPS"'

vfs:vop:vop_read:entry, vfs:vop:vop_write:entry
/this->mnt_name == MOUNT && this->filename != "- Unknown -"/ {
  this->filename = this->namecache != NULL ? (
    this->namecache->nc_dvp != NULL ? (
      this->namecache->nc_dvp->v_cache_dst.tqh_first != NULL ? strjoin(".../", this->filename) : this->filename
    ) : this->filename
  ) : this->filename;
  this->filename = this->mnt_name != "/" ? strjoin(this->mnt_name, strjoin("/", this->filename)) : strjoin(this->mnt_name, this->filename);
}

vfs:vop:vop_read:entry
/this->mnt_name == MOUNT/ {
  @iops_read[uid, pid, execname, this->filename] = count();
}

vfs:vop:vop_write:entry
/this->mnt_name == MOUNT/ {
  @iops_write[uid, pid, execname, this->filename] = count();
}

vfs:vop:vop_read:entry, vfs:vop:vop_write:entry
/this->mnt_name == MOUNT/ {
  @bytes_read[uid, pid, execname, this->filename] = sum(this->bytes_read);
  @bytes_write[uid, pid, execname, this->filename] = sum(this->bytes_write);
}

profile:::tick-1s {
  printa("%d\t%d\t%s\t%s\t%@d\t%@d\t%@d\t%@d\n", @bytes_read, @bytes_write, @iops_read, @iops_write);
  trunc(@bytes_read); trunc(@bytes_write); trunc(@iops_read); trunc(@iops_write);
}'
