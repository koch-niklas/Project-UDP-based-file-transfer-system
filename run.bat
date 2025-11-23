@echo off
set FILE="C:\temp\Chapter_4_v8.2.pptx"

start cmd /k python client.py --FILE "%FILE%" --WindowSize 3 --PacketLoss 1 --Timeout 0.5
start cmd /k python client.py --File "%FILE%" --WindowSize 4 --PacketLoss 1 --Timeout 0.5
start cmd /k python client.py --File "%FILE%" --WindowSize 5 --PacketLoss 1 --Timeout 0.5
start cmd /k python client.py --File "%FILE%" --WindowSize 6 --PacketLoss 1 --Timeout 0.5