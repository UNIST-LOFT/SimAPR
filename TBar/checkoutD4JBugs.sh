#!/bin/bash

export PATH=$(pwd)/D4J/defects4j/framework/bin/:$PATH

dir=D4J/projects/ # Store the buggy projects.


proj=Chart
for bug in $(seq 1 26)
do
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done

proj=Lang
lang_deprecated=(  )
for bug in 2
do
  for deprecated in "${lang_deprecated[@]}"
  do
    if [ $bug == $deprecated ]
    then
      continue 2
  fi
  done
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done

proj=Math
for bug in $(seq 1 106)
do
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done

proj=Closure
closure_deprecated=(  )
for bug in 63 93
do
  for deprecated in "${closure_deprecated[@]}"
  do
    if [ $bug == $deprecated ]
    then
      continue 2
  fi
  done
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done

proj=Mockito
for bug in $(seq 1 38)
do
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done

proj=Time
time_deprecated=(  )
for bug in 21
do
  for deprecated in "${time_deprecated[@]}"
  do
    if [ $bug == $deprecated ]
    then
      continue 2
  fi
  done
	defects4j checkout -p $proj -v ${bug}b -w ${dir}${proj}_${bug}
	cd ${dir}${proj}_${bug}
	defects4j compile
	cd ../../../
done