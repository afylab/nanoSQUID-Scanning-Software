from Equipment.Equipment import EquipmentController
from twisted.internet.defer import inlineCallbacks
from nSOTScannerFormat import printErrorInfo

class HF2LI_Controller(EquipmentController):
    @inlineCallbacks
    def connect(self, server, device_info):
        try:
            self.server = server
            yield self.server.detect_devices()
            yield self.server.select_device()
            self.widget.connected(device_info)
        except Exception as inst:
            print("Error connecting labrad servers")
            print(str(inst))
            printErrorInfo()
            self.widget.error()
    #
#

class ANC350_Controller(EquipmentController):
    @inlineCallbacks
    def connect(self, server, device_info):
        self.server = server
        num_devs = yield self.server.discover()
        if num_devs > 0:
            yield self.server.connect()
            self.widget.connected(device_info)
        else:
            self.widget.error()
    #

    @inlineCallbacks
    def disconnect(self):
        try:
            yield self.server.disconnect()
            print('Disconnected ANC350')
        except:
            print('Error disconnecting the ANC350 server.')
            printErrorInfo()
        super().disconnect()
#
