#!/bin/sh

#  -v /Users/vosslab/docker/MRC/06jul12a:/emg/data/leginon/06jul12a/rawdata \
#  -v /Volumes/Downloads/000test/get-flash-videos/flvchats/emg/data/appion:/emg/data/appion \
#  -v /Users/vosslab/emg/data:/emg/data \
#  -v /Users/vosslab/myami/pyami:/emg/sw/myami/pyami \

#  -v $HOME/myami:/emg/sw/myami \

docker run -d -t \
  -w /emg/sw/myami/appion \
  -p 80:80 -p 5901:5901 -p 3306:3306 \
  vosslab/appion_centos6
#  vosslab/artemia3


