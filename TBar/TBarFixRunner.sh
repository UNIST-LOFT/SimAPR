#!/bin/bash

bugDataPath=$1
bugID=$2
defects4jHome=$3
out=$4

java -Xmx100g -Xss500M -jar TBar-0.0.1-SNAPSHOT-jar-with-dependencies.jar $bugDataPath $bugID $defects4jHome $out
