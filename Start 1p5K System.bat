start labrad

TIMEOUT /T 3

start labrad-web
start python -m labrad.node

python nSOTScanner.py


