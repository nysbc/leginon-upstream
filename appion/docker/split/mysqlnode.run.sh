#!/bin/sh

#  -v /Users/vosslab/docker/MRC/06jul12a:/emg/data/leginon/06jul12a/rawdata \
#  -v /Volumes/Downloads/000test/get-flash-videos/flvchats/emg/data/appion:/emg/data/appion \
#  -v /Users/vosslab/emg/data:/emg/data \
#  -v /Users/vosslab/myami/pyami:/emg/sw/myami/pyami \

#  --cap-add SYS_ADMIN --security-opt seccomp:unconfined \
#  --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
#  -e 'container=docker' \
#  --tmpfs /run --tmpfs /run/lock \

docker run -d -t \
  -p 3306:3306 \
  myami_dbnode
