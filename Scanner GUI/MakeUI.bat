@ECHO OFF
call activate Python27

pyuic4 MainWindow.ui -o MainWindowUI.py & pyuic4 ScanControlWindow.ui -o ScanControlWindowUI.py & pyuic4 LabRADConnect.ui -o LabRADConnectUI.py 
