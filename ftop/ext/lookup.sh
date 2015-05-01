#!/bin/sh

usage () {
  echo "USAGE: $0 [-m <mountpoint>]" 1>&2; exit 1;
}

while getopts ":m:" opt;
do
  case $opt in
  m ) LOOKUP_PATH=$OPTARG
      ;;
  h ) usage
      ;;
  esac
done

if [ -z "$LOOKUP_PATH" ];
then
  exit
fi
find $LOOKUP_PATH | xargs stat > /dev/null
return 0
