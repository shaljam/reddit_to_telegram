#!/bin/bash
nohup python -u ./bot.py >> ./log/log &
touch "./log/start $(date)"
