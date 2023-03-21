#!/bin/bash

while :
do
    killall -s SIGKILL -o 5m java
    sleep 1m
done