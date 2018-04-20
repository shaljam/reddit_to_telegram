#!/bin/bash
nohup python -u ./bot.py >> ./log/log &
touch "./log/start-$(date "+%Y-%m-%dT%H:%M:%S")"
echo $! > ./log/id
