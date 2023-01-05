@ECHO OFF

start labrad

C:\windows\system32\timeout /t 4 /NOBREAK

start python "C:\Software\nanoSQUID-Scanning-Software\Servers\serial_server.py"

C:\windows\system32\timeout /t 1 /NOBREAK

start python "C:\Software\nanoSQUID-Scanning-Software\Servers\serial_server.py"

C:\windows\system32\timeout /t 1 /NOBREAK

start python "C:\Software\nanoSQUID-Scanning-Software\Servers\data_vault.py"

C:\windows\system32\timeout /t 1 /NOBREAK

start python "C:\Software\nanoSQUID-Scanning-Software\Servers\dac_adc.py"

C:\windows\system32\timeout /t 1 /NOBREAK

start python "C:\Software\nanoSQUID-Scanning-Software\Servers\Mercury IPS MAgnet Supply.py"

C:\windows\system32\timeout /t 1 /NOBREAK
start python "C:\Software\nanoSQUID-Scanning-Software\GUI\nanoSQUID_mobile.py"


