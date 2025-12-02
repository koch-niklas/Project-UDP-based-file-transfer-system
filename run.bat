@echo off
set FILE=C:\temp\file.pptx
set CMD=python "C:\Users\Niklas\OneDrive - University of Luxembourg\Local Programs\Networks\Project - Iterations\7.3 ACKS + multi client fixed (ready to push)\client.py" --File "%FILE%" --WindowSize 50 --PacketLoss 5 --Timeout 0.01

wt -M ^
    cmd /k "timeout /t 1 >nul & %CMD%" ^
    ; split-pane -H cmd /k "timeout /t 1 >nul & %CMD%" ^
    ; split-pane -V cmd /k "timeout /t 1 >nul & %CMD%" ^
    ; focus-pane -t 0 ; split-pane -V cmd /k "timeout /t 1 >nul & %CMD%"