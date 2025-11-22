@echo off
set FILE="C:\temp\Chapter_4_v8.2.pptx"

start cmd /k python client.py --file "%FILE%" --WindowSize 3
start cmd /k python client.py --file "%FILE%" --WindowSize 4
start cmd /k python client.py --file "%FILE%" --WindowSize 5
start cmd /k python client.py --file "%FILE%" --WindowSize 6