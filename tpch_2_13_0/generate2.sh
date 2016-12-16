#!/bin/sh

if [ -z "$CHUNKS" ]; then
  echo Need to specify CHUNKS
  exit 1
fi

export NUM_WORKERS=${NUM_WORKERS:-1}
export NUM_PROCS=${NUM_PROCS:-4}
export SCALE_FACTOR=${SCALE_FACTOR:-1}
export ROLE=${ROLE:-1}

export R=$(($ROLE-1))
export W=$NUM_WORKERS
export SF=$SCALE_FACTOR

# D = chunks per worker
# M = remaining chunks
# S = first chunk
# E = last chunk

echo $CHUNKS \
| xargs -r -n 2 sh -c 'D=$(($1/$W)) M=$(($1%$W)) S=$(( $R>=$M ? $M+$R*$D+1 : $R*($D+1)+1 )) E=$(( $R>=$M ? $S+$D-1 : $S+$D )) E=$(( $E>$1 ? $1 : $E)); (for c in `seq $S $E`; do echo $0 $1 $c; done)' \
| xargs -r -n 3 -P $NUM_PROCS sh -c 'if [ $1 = "1" ]; then ./dbgen -q -f -T $0 -s $SF; else ./dbgen -q -f -T $0 -C $1 -S $2 -s $SF; fi'

if [ "$ROLE" = "1" ]
then
  ./dbgen -q -f -T l -s $SCALE_FACTOR
fi

chmod 644 *.tbl*
