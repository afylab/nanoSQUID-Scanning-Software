'''
Code for creating a layer of abstraction between the labrad connections and the
GUI modules to enable smarter scripting and having multiple different systems.
'''

from customwidgets import ServerStatusWidget
from twisted.internet.defer import inlineCallbacks
#from traceback import format_exc
from nSOTScannerFormat import printErrorInfo

class EquipmentController():
    '''
    Generic base class for Controllers for equipment through labrad servers.
    Controllers provide a layer of abstraction to enable smarter scripting and
    generalize code to multiple different systems.

    Args:
        widget : The GUI widget for displaying the status
    '''
    def __init__(self, widget, device_info, config, reactor):
        self.server = None # When not connected the server is None
        self.widget = widget
        self.device_info = device_info
        self.config = config
        self.reactor = reactor
    #

    def connect(self, server):
        '''
        Connect to the device for the given server by calling select_device
        with the given selection info (if present). Override for more complex
        startup procedures.
        '''
        self.server = server
        try:
            if hasattr(server, 'select_device'):
                if self.device_info is None:
                    server.select_device()
                else:
                    server.select_device(self.device_info)
            self.widget.connect(self.device_info)
        except Exception as inst:
            print("Error connecting labrad servers")
            print(str(inst))
            printErrorInfo()
            self.widget.error()
    #

    def disconnect(self):
        '''
        Disconnect to the device for the given server. This funciton is always called
        before a general disconnect on the equipment handler, so overide this to
        add more complex shutdown behavior if needed.
        '''
        if self.server is None:
            return
        if hasattr(self.server, 'deselect_device'):
            self.server.deselect_device()
        self.server = None
        self.widget.disconnected()
    #

class EquipmentHandler():
    def __init__(self, default_frame, remote_frame, computer, reactor):
        '''
        Handels the various system specific equipment and the configuration.

        When connected EquipmentHandler.servers is a dictionary that contains
        (server, labrad_name, device_info, controller, config_dict) where
        server: is the connection to a labRAD server
        labrad_name : is the name on the labrad connection object of the server, generic
            name if it requires the computer name.
        device_info: is the information to connect to a specific device, if None
            select_device is called with no arguments.
        controller: the controller object, if applicable
        config_dict : A dictionary of any additional configuration information
            that might be needed, such as indexes of specific channels.

        Args:
            primary_frame (QFrame) : The defautlt frame to place new widgets into.
            computer (str) : The name of the computer, required for serial and gpib servers
            remote_ip (str) : If this is a remote conneciton, the IP for the remote
                labrad connection.
        '''

        # Labrad Connections, initilized to None if they have not been connected
        self.servers = dict() # Connections to the various labrad servers

        self.cxn = False
        self.dv = False
        self.ip = '127.0.0.1'
        self.compname = computer
        self.reactor = reactor

        self.cxnr = False
        self.remote_ip = None
        self.remote_compname = None
        self.remote_servers = []

        # Disply the widgets
        self.widgets = dict()
        self.default_frame = default_frame
        self.remote_frame = remote_frame
        self.widget_frames_ix = dict() # Allows you to keep track of widgets in multiple frames
        self.widget_frames_ix[self.default_frame] = 0
    #

    def add_server(self, name, labrad_name, device_info=None, controller=None, config=None, display_frame=None):
        '''
        Add a labrad server to the Equipment Handler

        Args:
            name (str) : The name that will be used to reference this server
            labrad_name (str) : The name of the attribute of the labrad connection
                object that refers to this server.
            device_info : Any information needed to connect to the device, usually a COM or GPIB port etc.
            controller : The EquipmentController object reference, will be instantiated here
            config (dict) : A dictionary that will be accessible to modules containing any additional information
                that may be needed.
            display_frame : The QtFrame object to place the corresponding widget into, if other than default.
        '''
        self.add_server_widget(name, display_frame=display_frame)
        if name in ["Serial Server", "GPIB Server"]: # These have special names based on the system
            self.servers[name] = (False, self.compname.lower() + "_" + labrad_name, None, None, None)
        elif name != "LabRAD":
            if controller is not None:
                controller = controller(self.widgets[name], device_info, config, self.reactor)
            self.servers[name] = (False, labrad_name, device_info, controller, config)
    #

    def configure_remote_host(self, remote_ip, remote_computer_name):
        '''
        Add a labrad server to the Equipment Handler that is hosted on the remote connection

        Args:
            remote_ip (str) : The hostname or ip address of the remote computer, called to make the labrad connection
            remote_computer_name (str) : The name of the remote computer, required for serial and gpib servers
        '''
        self.remote_ip = remote_ip
        self.remote_compname = remote_computer_name
        self.remote_servers = []
    #

    def add_remote_server(self, name, labrad_name, device_info=None, controller=None, config=None, display_frame=None):
        '''
        Add a labrad server to the Equipment Handler that is hosted on the remote connection

        Args:
            name (str) : The name that will be used to reference this server
            labrad_name (str) : The name of the attribute of the labrad connection
                object that refers to this server.
            device_info : Any information needed to connect to the device, usually a COM or GPIB port etc.
            controller : The EquipmentController object reference, will be instantiated here
            config (dict) : A dictionary that will be accessible to modules containing any additional information
                that may be needed.
            display_frame : The QtFrame object to place the corresponding widget into, if other than default.
        '''
        if self.remote_ip is None:
            print("Error trying to add remote server before the remote host has been configured.")
            raise ValueError("Invalid remote host")


        if display_frame is not None:
            self.add_server_widget(name, display_frame=self.remote_frame)
        else:
            self.add_server_widget(name, display_frame=self.remote_frame)
        if name in ["Serial Server", "GPIB Server"]: # These have special names based on the system
            self.servers[name] = (False, self.remote_compname.lower() + "_" + labrad_name, None, None, None)
        elif name != "Remote LabRAD":
            if controller is not None:
                controller = controller(self.widgets[name], device_info, config, self.reactor)
            self.servers[name] = (False, labrad_name, device_info, controller, config)
        self.remote_servers.append(name)
    #

    @inlineCallbacks
    def connect_all_servers(self):
        # Get the main labrad connection
        try:
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(host=self.ip, password='pass')
            if "LabRAD" in self.widgets:
                self.widgets["LabRAD"].connected()

            if self.remote_ip is not None:
                self.cxnr = yield connectAsync(host=self.remote_ip, password='pass')
                if "Remote LabRAD" in self.widgets:
                    self.widgets["LabRAD"].connected()

        except Exception as inst:
            print("Error connecting to labrad")
            print(str(inst))
            print("Cannot connect any servers")
            if "LabRAD" in self.widgets:
                self.widgets["LabRAD"].error()
            return

        # Loop through servers and connect
        for name in self.servers.keys():
            if name == "LabRAD":
                continue
            try:
                svr, labrad_name, device_info, cnt, config = self.servers[name]
                # Need to get each server with an individual connection, otherwise
                # a server will switch between the same type of device when select_device
                # is called. I.e. you couldn't use references to two DAC_ADCs at the same time
                if name in self.remote_servers:
                    cxnr = yield connectAsync(host=self.remote_ip, password='pass')
                    server = getattr(cxnr, labrad_name)
                else:
                    cxn = yield connectAsync(host=self.ip, password='pass')
                    server = getattr(cxn, labrad_name)

                if name == "Data Vault":
                    self.dv = server
                    self.changeDVSession()

                # Configure the device, either through a controller or the
                # select_device function in most servers.
                if cnt is not None:
                    yield cnt.connect(server)
                elif hasattr(server, 'select_device'):
                    if device_info is None:
                        server.select_device()
                    else:
                        server.select_device(device_info)
                    if name in self.widgets:
                        self.widgets[name].connected(device_info)
                else:
                    if name in self.widgets:
                        self.widgets[name].connected(device_info)

                self.servers[name] = (server, labrad_name, device_info, cnt, config)

            except Exception as inst:
                print("Error connecting labrad server", name)
                print(str(inst))
                if name in self.widgets:
                    self.widgets[name].error()
                self.servers[name] = (False, labrad_name, device_info, cnt, config) # Set the server to be false
    #

    @inlineCallbacks
    def disconnect_servers(self):
        try:
            for k in self.servers.keys():
                server, labrad_name, device_info, cnt, config = self.servers[k]
                if cnt is not None:
                    cnt.disconnect()
                self.servers[k] = (False, labrad_name, device_info, cnt, config)
                self.widgets[k].disconnected()
        except Exception as inst:
            print("Error disconnecting device controllers")
            print(str(inst))
            printErrorInfo()

        self.dv = False
        if self.cxn is not False:
            try:
                yield self.cxn.disconnect()
                self.cxn = False
                if 'LabRAD' in self.widgets:
                    self.widgets['LabRAD'].disconnected()
            except Exception as inst:
                print("Error disconnecting labrad connection")
                print(str(inst))
                printErrorInfo()
    #

    def get(self, name):
        '''
        Returns the controller or labrad server corresponding to a certain name.
        If a controller is present, will return it, otherwise it will return a
        labrad server.
        '''
        svr, labrad_name, device_info, cnt, config = self.servers[name]
        if cnt is None:
            return svr
        else:
            return cnt

    @inlineCallbacks
    def get_datavault(self):
        '''
        Gets a new connection to the datavault that matches the directory of the
        equipment handler vault.
        '''
        from labrad.wrappers import connectAsync
        cxn_dv = yield connectAsync(host = '127.0.0.1', password = 'pass')
        dv = yield cxn_dv.data_vault
        curr_folder = yield self.dv.cd()
        yield self.dv.cd(curr_folder)
        return dv

    def add_server_widget(self, name, display_frame=None):
        if display_frame is None:
            display_frame = self.default_frame
        elif display_frame not in self.widget_frames_ix:
            self.widget_frames_ix[display_frame] = 0
        ix = self.widget_frames_ix[display_frame]
        self.widgets[name] = ServerStatusWidget(display_frame, name)
        self.widgets[name].move(5+250*(ix%2),20+20*(ix//2))
        self.widget_frames_ix[display_frame] = ix + 1
    #

    def setSession(self, session):
        '''
        Configure the session folder that Data Vault saves to.
        '''
        self.session = session
        if self.dv is not False:
            self.changeDVSession()
    #

    @inlineCallbacks
    def changeDVSession(self):
        '''
        Change the data vault to the right folder
        '''
        if self.dv is not False:
            try:
                yield self.dv.cd('')
                sess = self.session
                yield self.dv.cd(sess, True)
                curr = yield self.dv.cd()
            except Exception as inst:
                print(inst)
                printErrorInfo()
    #
#
