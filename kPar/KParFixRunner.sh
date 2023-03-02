#!/bin/bash
bugDataPath=$1
bugID=$2
defects4jHome=$3
out=$4

java -Xmx100g -jar target/kPAR-0.0.1-SNAPSHOT-jar-with-dependencies.jar $bugDataPath $bugID $defects4jHome $out
# ./KParFixRunner.sh /root/project/TBarCopy/D4J/projects/ Math_16 /root/project/TBarCopy/D4J/defects4j/ /root/project/kParCopy/results/
