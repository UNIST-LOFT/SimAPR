#!/bin/bash

bugDataPath=$1
bugID=$2
defects4jHome=$3
out=$4

java -Xmx100g -Xss500M -cp "target/dependency/*" edu.lu.uni.serval.tbar.main.MainPerfectFLPatchSpace $bugDataPath $bugID $defects4jHome $out
