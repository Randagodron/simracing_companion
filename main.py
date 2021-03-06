#!/usr/bin/env python
"""
DR2 logger with wxPython GUI
Following : https://wiki.wxpython.org/wxPython%20Style%20Guide
"""

"""
    Libraries
"""

# WX and inter-frame communication
import wx
import wx.lib.agw.speedmeter as SM
import wx.lib.gizmos as gizmos
from pubsub import pub

# Serial communication
import serial
from serial.tools import list_ports

# General OS libs
import io
import os
import sys
import threading
import queue

# For settings file read
import os.path
from source import settings

# Misc. imports
from math import pi, sqrt
import struct
import random

# Dr2_logger classes
from source.logger_backend import LoggerBackend


"""
  Code start
"""

log_raw_data = False
debugging = False

version_string = '(Version 2.0.0, 2022-01-16)'
# TODO: update date

ID_STARTLOG = 100

# Global variables
logger_started = False

logger_backend = LoggerBackend(debugging=debugging, log_raw_data=log_raw_data)

intro_text = '''
Dirt Rally 2.0 Logger {}
https://github.com/ErlerPhilipp/dr2_logger

Make sure, UDP data is enabled in the hardware_settings_config.xml 
Default: C:\\Users\\ [username] \\Documents\\My Games\\DiRT Rally 2.0\\hardwaresettings\\hardware_settings_config.xml
<motion_platform>
    <dbox enabled="false" />
    <udp enabled="true" extradata="3" ip="127.0.0.1" port="20777" delay="1" />
    <custom_udp enabled="False" filename="packet_data.xml" ip="127.0.0.1" port="20777" delay="1" />
    <fanatec enabled="false" pedalVibrationScale="1.0" wheelVibrationScale="1.0" ledTrueForGearsFalseForSpeed="true" />
</motion_platform>
'''.format(version_string)

commands_hint = '''
Enter:
"e" or "exit" to exit the program
"c" or "clear" to clear the current run
"p" or "plot" to show the important plots
"pa" or "plot_all" to show all plots
"s" or "save" to save the current run
"l" or "load" to load a saved run
"g game_name" to switch the target game, values for game_name: {}
'''.format(LoggerBackend.get_all_valid_games())

def udp_listen():
    global logger_backend
    
    while logger_started:
        logger_backend.check_udp_messages()
        msg = logger_backend.check_state_changes()
        if len(msg) > 0:
            # pub.sendMessage("print_console", message=msg)
            print(msg)

def thread_dr2logger_init():
    global logger_backend
    
    end_program = False

    # print_function(commands_hint)
    pub.sendMessage("print_console", message=intro_text)

    logger_backend.start_logging()
    
def print_current_state(state_str):
    if state_str is not None:
        try:
            if os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetConsoleTitleW(state_str)
            else:
                # for Linux terminals:
                # while both Gnome Terminal and KDE's Konsole report TERM=xterm-256color,
                # Konsole needs different control chars
                # to change the terminal title
                if 'KONSOLE_VERSION' in os.environ:
                    # https://stackoverflow.com/questions/19897787/change-konsole-tab-title-from-command-line-and-make-it-persistent
                    # TODO this works only once per stage where it's updated at the very beginning
                    sys.stdout.write('\033]30;{}\007'.format(state_str))
                else:
                    # https://stackoverflow.com/questions/25872409/set-gnome-terminal-window-title-in-python/47262154#47262154
                    sys.stdout.write('\33]0;{}\a'.format(state_str))
                sys.stdout.flush()
        finally:
            pass


# ======================================================================================
class PanelSerial(wx.Panel, object):
    """Serial panel - Manages the serial communication, scans the available ports"""
    def __init__(self, parent, *args, **kwargs):
        """Create the PanelSerial."""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        self.port_open = False
        self.debug_enable = False
        
        # COM ports
        # Serial ports
        ports = serial.tools.list_ports.comports()
        ports_list = [] # List of ports references
        ports_description_list = [] # List of serial ports descriptions, for ease of identification on GUI
        
        # Scan for COM ports
        self.scan_com_ports(ports, ports_list, ports_description_list)
        
        buttonRefresh     = wx.Button(self, label="Refresh", size=wx.Size(100, 32))
        buttonRefresh.Bind(wx.EVT_BUTTON, self.OnClickPortsRefresh)
        
        self.buttonDebug     = wx.Button(self, label="Debug info", size=wx.Size(100, 32))
        self.buttonDebug.SetBackgroundColour('green')
        self.buttonDebug.Bind(wx.EVT_BUTTON, self.OnClickDebug)
        
        listSerialPorts   = wx.Choice(self, choices=ports_description_list)
        listSerialPorts.Bind(wx.EVT_CHOICE, self.getOnSelectSerial(listSerialPorts))
        
        self.buttonConnect     = wx.Button(self, label="Connect", size=wx.Size(100, 32))
        self.buttonConnect.SetBackgroundColour('green')
        self.buttonConnect.Bind(wx.EVT_BUTTON, self.getOnClickPortsConnect(ports_list, listSerialPorts.GetCurrentSelection()))
        
        boxSizerSerial = wx.StaticBoxSizer(wx.VERTICAL, self, "Serial communication")
        boxSizerSerial.Add(listSerialPorts, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerSerial.Add(buttonRefresh, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerSerial.Add(self.buttonDebug, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerSerial.Add(self.buttonConnect, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.SetSizer(boxSizerSerial)
        self.Layout()
        
        # Subscribe to general config and serial config
        pub.subscribe(self.sub_listener, "config_general")
        pub.subscribe(self.sub_listener, "config_serial")
        pub.subscribe(self.sub_listener_send, "serial_tx")
    
    def OnClickPortsRefresh(self, event):
        # TODO
        # self.scan_com_ports()
        # print("Refresh\n") # DEBUG
        # pub.sendMessage("print_console", message="Refresh") # DEBUG
        pass
        
    def OnClickDebug(self, event):
        if (self.debug_enable):
            self.buttonDebug.SetBackgroundColour('green')
            self.buttonDebug.SetLabel("Debug info")
            self.debug_enable = False
        else:
            self.buttonDebug.SetBackgroundColour('red')
            self.buttonDebug.SetLabel("Debug stop")
            self.debug_enable = True
        
    def getOnClickPortsConnect(self, ports_list, port_current_selection):
        def OnClickPortsConnect(event):
            if self.port_open: # Check if a port is already opened
                self.port_open = False
                self.ser.close()
                pub.sendMessage("print_console", message="Disconnecting port: %s - Bandrate: %d" % (self.ser.name, 115200))
                self.buttonConnect.SetBackgroundColour('green')
                self.buttonConnect.SetLabel('Connect')
            else:
                self.ser = serial.Serial(ports_list[port_current_selection], 115200)
                
                if self.ser.is_open: # Check if port was successfully opened
                    self.port_open = True
                    pub.sendMessage("print_console", message="Connection to port: %s - Bandrate: %d" % (self.ser.name, 115200))
                    self.buttonConnect.SetBackgroundColour('red')
                    self.buttonConnect.SetLabel('Disconnect')
                else: # Otherwise print error message
                    self.port_open = False
                    pub.sendMessage("print_console", message="Error while opening serial port !")
                    self.buttonConnect.SetBackgroundColour('green')
                    self.buttonConnect.SetLabel('Connect')
        return OnClickPortsConnect
        
    
        
    """https://stackoverflow.com/questions/173687/is-it-possible-to-pass-arguments-into-event-bindings"""
    def getOnSelectSerial(self, list_serial_ports):
        def OnSelectSerial(event):
            pub.sendMessage("print_console", message="Serial port selected : %d\n" % (list_serial_ports.GetCurrentSelection()))
        return OnSelectSerial
    
    def scan_com_ports(self, ports, ports_list, ports_description_list):
        """
        Scans the available COM ports, creates a list and fills the corresponding wx.choice
        """
        pub.sendMessage("print_console", message="Searching for COM ports ...\n")
        for port in ports :
            ports_list.append(port.device) # Get port reference
            ports_description_list.append(port.device + " - " + port.description) # Construct a description for the GUI list
            pub.sendMessage("print_console", message="COM port found : %s\n" % (port.device + " - " + port.description))
            
    def sub_listener(self, message):
        """
        Listener function
        """
        print(message)
        
    def sub_listener_send(self, message):
        """
        Send data to serial port
        """
        if self.port_open:
            self.ser.write(message)
        else:
            pass


class PanelDeviceCommunication(wx.Panel, object):
# ======================================================================================
    """Device Communication Module (DCM) panel - Parses received serial messages, construct sent serial messages"""
    def __init__(self, parent, *args, **kwargs):
        """Create the PanelDeviceCommunication."""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        self.Bind(wx.EVT_CLOSE, self.OnClosePanel)
        
        self.periodic_send_enable = True
        self.timer_send_period = 0.1
        self.test_enable = False
        self.debug_index = 0
        
        # self.speed_modifier = speed_units == 'mph' and 0.6214 or 1
        self.speed_modifier = 1
        
        self.gear = 0
        self.speed = 0
        self.rpm = 0
        self.max_rpm = 10000
        self.data = {
        'speed': int(self.speed * self.speed_modifier),
        'gear': int(self.gear),
        'rpm': int(self.rpm),
        'max_rpm': int(self.max_rpm)
        }
        
        # Subscribe to general config and serial config
        pub.subscribe(self.sub_listener_gear, "telemetry_gear")
        pub.subscribe(self.sub_listener_speed, "telemetry_speed")
        pub.subscribe(self.sub_listener_rpm, "telemetry_rpm")
        
        # Control for communication periodicity
        self.controlCommunicationPeriod = wx.SpinCtrl(self, size=wx.Size(50, 20), min=0, max=1000, initial=50)
        self.controlCommunicationPeriod.Bind(wx.EVT_SPINCTRL, self.getOnPeriodChange())
        
        # DEBUG
        self.buttonTest     = wx.Button(self, label="Test", size=wx.Size(100, 32))
        self.buttonTest.SetBackgroundColour('green')
        self.buttonTest.Bind(wx.EVT_BUTTON, self.getOnClickTest())
        
        # self.controlDebugIndex = wx.SpinCtrl(self, size=wx.Size(50, 20), min=0, max=1024, initial=1)
        # self.controlDebugIndex.Bind(wx.EVT_SPINCTRL, self.getOnDebugChange())
        
        boxSizerDCM = wx.StaticBoxSizer(wx.VERTICAL, self, "Device Communication Module")
        boxSizerDCM.Add(self.controlCommunicationPeriod, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        #DEBUG
        boxSizerDCM.Add(self.buttonTest, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        # boxSizerDCM.Add(self.controlDebugIndex, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.SetSizer(boxSizerDCM)
        self.Layout()
        
        self.timer_send_period = self.controlCommunicationPeriod.GetValue() / 1000.0
        
        # Start cyclic thread for serial communication
        self.thread_lock = threading.Lock()
        self.serial_send_thread_timer = threading.Timer(self.timer_send_period, self.serial_send)
        self.serial_send_thread_timer.start()
        pub.sendMessage("print_console", message="Periodic serial communication thread started with period %d" % (self.controlCommunicationPeriod.GetValue()))
    
    def OnClosePanel(self, event):
        self.serial_send_thread_timer.cancel()
        print("Closing communication")
        self.Destroy()
    
    def getOnClickTest(self):
        def OnClickTest(event):
            if self.test_enable :
                # Disable test sends
                self.test_enable = False
                self.buttonTest.SetBackgroundColour('green')
                self.buttonTest.SetLabel('Test')
                print("Stopping test messages")
            else:
                self.test_enable = True
                self.buttonTest.SetBackgroundColour('red')
                self.buttonTest.SetLabel('Test stop')
                print("Starting test messages")
        return OnClickTest
        
    def getOnPeriodChange(self):
        def OnPeriodChange(event):
            self.timer_send_period = self.controlCommunicationPeriod.GetValue() / 1000.0
            pub.sendMessage("print_console", message="trest")
            # print("test")
        return OnPeriodChange
        
    # def getOnDebugChange(self):
        # def OnDebugChange(event):
            # self.debug_index = self.controlDebugIndex.GetValue()
            # pub.sendMessage("debug_index", message=self.debug_index)
        # return OnDebugChange
        
    def serial_send(self):
        # TODO : add check that the port exists and is opened
        if self.test_enable :
            pub.sendMessage("serial_tx", message=struct.pack('>cHHchcB', bytes('R', "utf-8"), random.randint(100, 8000), 8000, bytes('S', "utf-8"), random.randint(1, 180), bytes('G', "utf-8"), random.choice([0,1,2,3,4,5,6,7,10])))
 # DEBUG
        else :
            
            if self.rpm < 0:
                self.rpm = 0
            
            if self.speed < 0:
                self.speed = self.speed * (-1)
            
            if self.gear < 0:
                self.gear = 10
            
            pub.sendMessage("serial_tx", message= struct.pack('>cHHchcB', bytes('R', "utf-8"), self.rpm, self.max_rpm, bytes('S', "utf-8"), self.speed, bytes('G', "utf-8"), self.gear))
        
        with self.thread_lock:
            if self.periodic_send_enable:
                self.serial_send_thread_timer = threading.Timer(self.timer_send_period, self.serial_send)
                self.serial_send_thread_timer.start() # Restart timer
            else:
                self.serial_send_thread_timer.cancel()
        
    def sub_listener_gear(self, message):
        self.gear = int(message)
    
    def sub_listener_rpm(self, message):
        self.rpm = int(message)
    
    def sub_listener_max_rpm(self, message):
        self.max_rpm = int(message)
        
    def sub_listener_speed(self, message):
        self.speed = int(message)
        

# ======================================================================================
class PanelConsole(wx.Panel, object):
    """Console panel - Displays messages, replaces print"""
    def __init__(self, parent, *args, **kwargs):
        """Create the Console panel"""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        self.consoleTextCtrl   = wx.TextCtrl(self, size=wx.Size(600, 400), style=wx.TE_MULTILINE|wx.TE_READONLY)
        
        boxSizerConsole = wx.StaticBoxSizer(wx.VERTICAL, self, "Console output")
        boxSizerConsole = wx.BoxSizer(wx.VERTICAL)
        boxSizerConsole.Add(self.consoleTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.SetSizer(boxSizerConsole)
        self.Layout()
        
        # Subscribe to general config and console outputs
        pub.subscribe(self.sub_listener, "print_console")
        
        self.Bind(wx.EVT_CLOSE, self.OnClosePanel)
        
        # Overload print to redirect stdout to the console panel
        """https://stackoverflow.com/questions/550470/overload-print-python"""
        old_stdout = sys.stdout
        new_stdout = self
        sys.stdout = new_stdout
        
        self.write_length = 0
    
    def write(self, text):
        self.consoleTextCtrl.AppendText(text)
        self.write_length = len(text)
    
    def print_console(self, text):
        self.consoleTextCtrl.AppendText(text)
    
    def sub_listener(self, message):
        """
        Listener function
        https://github.com/schollii/pypubsub/tree/master/examples/basic_kwargs
        """
        self.print_console(message)
        self.print_console("\n")
        
    def flush(self):
        # self.consoleTextCtrl.flush()
        # self.consoleTextCtrl.Remove(self.consoleTextCtrl.GetLastPosition() - self.write_length, self.consoleTextCtrl.GetLastPosition())
        pass
        
    def OnClosePanel(self, event):
        # Rollback to standard stdout
        sys.stdout = old_stdout
        self.Destroy()


# ======================================================================================
class PanelLogger(wx.Panel, object):
    """Logger panel - Manages telemtry logger"""
    def __init__(self, parent, *args, **kwargs):
        """Create the Console panel"""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        self.listGame   = wx.Choice(self, choices=LoggerBackend.get_all_valid_games())
        buttonClearRun  = wx.Button(self, label="Clear run", size=wx.Size(100, 32))
        buttonPlot      = wx.Button(self, label="Plot", size=wx.Size(100, 32))
        buttonPlotAll   = wx.Button(self, label="PlotAll", size=wx.Size(100, 32))
        buttonSave      = wx.Button(self, label="Save", size=wx.Size(100, 32))
        buttonLoad      = wx.Button(self, label="Load", size=wx.Size(100, 32))
        
        self.buttonStartLogging     = wx.Button(self, label="Start logging", size=wx.Size(100, 32))
        self.buttonStartLogging.SetBackgroundColour('green')
        self.buttonStartLogging.Disable()
        
        boxSizerLogger = wx.StaticBoxSizer(wx.VERTICAL, self, "Logger")
        boxSizerLogger.Add(self.listGame, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(self.buttonStartLogging, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(buttonClearRun, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(buttonPlot, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(buttonPlotAll, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(buttonSave, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        boxSizerLogger.Add(buttonLoad, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.buttonStartLogging.Bind(wx.EVT_BUTTON, self.getOnClickStartLogging())
        buttonClearRun.Bind(wx.EVT_BUTTON, self.getOnClickClearRun())
        buttonPlot.Bind(wx.EVT_BUTTON, self.getOnClickPlot())
        buttonPlotAll.Bind(wx.EVT_BUTTON, self.getOnClickPlotAll())
        buttonSave.Bind(wx.EVT_BUTTON, self.getOnClickSave())
        buttonLoad.Bind(wx.EVT_BUTTON, self.getOnClickLoad())
        self.listGame.Bind(wx.EVT_CHOICE, self.getOnSelectGame())
        
        self.SetSizer(boxSizerLogger)
        self.Layout()
        
        # Check availability of settings for each game
        for game in LoggerBackend.get_all_valid_games():
            if settings.settings.has_section(game):
                print("Configuration found for ", game)
                if not settings.settings.has_option(game, 'ip_in'):
                    print("*** Error *** No 'ip_in' option found for ", game, " -> Loading default values")
                    settings.init_settings_input_socket(game)
                
                if not settings.settings.has_option(game, 'port_in'):
                    print("*** Error *** No 'port_in' option found for ", game, " -> Loading default values")
                    settings.init_settings_input_socket(game)
                
            else:
                print("*** Error *** No configuration found for ", game, " -> Loading default values")
                settings.settings[game] = {}
                settings.init_settings_input_socket(game)
            
            print("Input IP address : ", settings.settings[game]['ip_in'])
            print("Input port : ", settings.settings[game]['port_in'])
        
        # Start logger thread
        self.thread_udp = threading.Thread(target=udp_listen, daemon=True)
        
        # Subscribe to general config
        pub.subscribe(self.sub_listener, "config_general")
        pub.subscribe(self.sub_listener, "config_logger")
        
        # DEBUG
        pub.subscribe(self.sub_listener, "debug")
        
    def getOnClickStartLogging(self):
        def OnClickStartLogging(event):
            global logger_backend
            # Start / Stop DR2logger process
            global logger_started
            if logger_started==False:
                pub.sendMessage("print_console", message="Start logging")
                logger_started=True
                self.buttonStartLogging.SetLabel("Stop logging")
                self.buttonStartLogging.SetBackgroundColour('red')
                thread_dr2logger_init()
                self.thread_udp.start()
            else:
                pub.sendMessage("print_console", message="Stop logging")
                logger_started=False
                self.buttonStartLogging.SetLabel("Start logging")
                self.buttonStartLogging.SetBackgroundColour('green')
                self.thread_udp.join()
                logger_backend.end_logging()
        return OnClickStartLogging
        
    def getOnClickClearRun(self):
        def OnClickClearRun(event):
            global logger_backend
            pub.sendMessage("print_console", message='Cleared {} data points\n'.format(logger_backend.get_num_samples()))
            logger_backend.clear_session_collection()
        return OnClickClearRun
    
    def getOnClickPlot(self):
        def OnClickPlot(event):
            pub.sendMessage("print_console", message="Plot")
            if logger_backend.get_num_samples() == 0:
                pub.sendMessage("print_console", message='No data points to plot\n')
            else:
                pub.sendMessage("print_console", message='Plotting {} data points\n'.format(logger_backend.get_num_samples()))
                logger_backend.show_plots(False)
        return OnClickPlot
    
    def getOnClickPlotAll(self):
        def OnClickPlotAll(event):
            pub.sendMessage("print_console", message="PlotAll")
            if logger_backend.get_num_samples() == 0:
                pub.sendMessage("print_console", message='No data points to plot\n')
            else:
                pub.sendMessage("print_console", message='Plotting {} data points\n'.format(logger_backend.get_num_samples()))
                logger_backend.show_plots(True)
        return OnClickPlotAll
    
    def getOnClickSave(self):
        def OnClickSave(event):
            pub.sendMessage("print_console", message="Save")
            logger_backend.save_run()
        return OnClickSave
    
    def getOnClickLoad(self):
        def OnClickLoad(event):
            pub.sendMessage("print_console", message="Load")
            logger_backend.load_run()
            print_current_state(logger_backend.get_game_state_str())
        return OnClickLoad
    
    def getOnSelectGame(self):
        def OnSelectGame(event):
            pub.sendMessage("print_console", message="Game selected")
            new_game_name = self.listGame.GetString(self.listGame.GetCurrentSelection())
            logger_backend.change_game(new_game_name)
            print('Switched game to "{}"'.format(logger_backend.game_name))
            self.buttonStartLogging.Enable()
        return OnSelectGame
        
    def sub_listener(self, message):
        """
        Listener function
        """
        # pass
        self.debug = message
        print(self.debug)
        

# ======================================================================================
class PanelDashboard(wx.Panel, object):
    """Logger panel - Manages telemtry logger"""
    def __init__(self, parent, *args, **kwargs):
        """Create the Console panel"""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        # https://stackoverflow.com/questions/51141085/using-wxpython-speedmeter-within-a-panel
        
        panel = wx.Panel(self, wx.ID_ANY)
        panel1 = wx.Panel(panel, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        
    # Speedometer
    #############
        self.speed_max_meter = 200
        self.speedMeter = SM.SpeedMeter(panel1, -1, agwStyle=SM.SM_DRAW_HAND|SM.SM_DRAW_SECTORS|SM.SM_DRAW_MIDDLE_TEXT|SM.SM_DRAW_SECONDARY_TICKS, size = (300,300), mousestyle=0)

        self.speedMeter.SetAngleRange(-pi/6, 7*pi/6)
        intervals = range(0, (self.speed_max_meter + 1), int(self.speed_max_meter / 10))
        self.speedMeter.SetIntervals(intervals)
        colours = [wx.BLACK]*10
        self.speedMeter.SetIntervalColours(colours)
        ticks = [str(interval) for interval in intervals]
        self.speedMeter.SetTicks(ticks)
        self.speedMeter.SetTicksColour(wx.WHITE)
        self.speedMeter.SetNumberOfSecondaryTicks(3)
        self.speedMeter.SetTicksFont(wx.Font(7, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.speedMeter.SetMiddleText("Speed")
        self.speedMeter.SetMiddleTextColour(wx.WHITE)
        self.speedMeter.SetMiddleTextFont(wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.speedMeter.SetHandColour(wx.Colour(255, 50, 0))
        self.speedMeter.DrawExternalArc(False)
        self.speedMeter.SetSpeedValue(44)
        
    # Rpmmeter
    #############
        self.rpm_max = 9500
        self.rpm_max_meter = 10000
        self.rpmMeter = SM.SpeedMeter(panel1, -1, agwStyle=SM.SM_DRAW_HAND|SM.SM_DRAW_SECTORS|SM.SM_DRAW_MIDDLE_TEXT|SM.SM_DRAW_SECONDARY_TICKS, size = (300,300), mousestyle=0)

        self.rpmMeter.SetTicksFont(wx.Font(7, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.rpmMeter.SetMiddleText("RPM")
        self.rpmMeter.SetMiddleTextColour(wx.WHITE)
        self.rpmMeter.SetMiddleTextFont(wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.rpmMeter.SetHandColour(wx.Colour(255, 50, 0))
        
        self.RpmMeterConfig(self.rpm_max)
        self.rpmMeter.SetSpeedValue(2500)
    
    # Gear display
    ##############
        self.gearLed = gizmos.LEDNumberCtrl(self, -1, (300,300), (25, 200),
                              gizmos.LED_ALIGN_CENTER)# | gizmos.LED_DRAW_FADED)
        self.gearLed.SetForegroundColour('red')
        self.gearLed.SetBackgroundColour('black')
        self.gearLed.SetValue("1")
    
    # Race time display
    ###################
        self.raceTimeLed = gizmos.LEDNumberCtrl(self, -1, (300,300), (25, 50),
                              gizmos.LED_ALIGN_CENTER)# | gizmos.LED_DRAW_FADED)
        self.raceTimeLed.SetForegroundColour('red')
        self.raceTimeLed.SetBackgroundColour('black')
        self.raceTimeLed.SetValue("00:00")
        
    # Track progress bar
    ####################
        self.progressBar = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL|wx.GA_TEXT)
        self.progressBar.SetValue(0)
    
    # Create required sizers
    ########################
        # Speedometer sizer
        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer1.Add(self.speedMeter, 0, wx.EXPAND)
        vsizer1.Add(hsizer1, 0, wx.EXPAND)
        
        # Gearbox display sizer
        vsizer2 = wx.BoxSizer(wx.VERTICAL)
        vsizer2.Add(self.gearLed, 0, wx.EXPAND)
        vsizer2.Add(self.raceTimeLed, 0, wx.EXPAND)
        vsizer2.Add(self.progressBar, 0, wx.EXPAND)
        
        # RPM meter sizer
        vsizer3 = wx.BoxSizer(wx.VERTICAL)
        hsizer3 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer3.Add(self.rpmMeter, 0, wx.EXPAND)
        vsizer3.Add(hsizer3, 0, wx.EXPAND)
        
        # Main dashboard sizer
        hsizermain = wx.BoxSizer(wx.HORIZONTAL)
        hsizermain.Add(vsizer1, 1, wx.EXPAND)
        hsizermain.Add(vsizer2, 1, wx.EXPAND)
        hsizermain.Add(vsizer3, 1, wx.EXPAND)
        
        #Set the panel1 sizer
        panel1.SetSizer(hsizermain)
        
        #Fit contents
        panel1.Fit()
        
        #Implement the main sizer
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(mainSizer)
        mainSizer.Layout()
        
        pub.subscribe(self.sub_listener_track_progress, "telemetry_track_progress")
        pub.subscribe(self.sub_listener_track_duration, "telemetry_track_duration")
        pub.subscribe(self.sub_listener_gear, "telemetry_gear")
        pub.subscribe(self.sub_listener_speed, "telemetry_speed")
        pub.subscribe(self.sub_listener_rpm, "telemetry_rpm")
        # pub.subscribe(self.sub_listener_max_rpm, "telemetry_max_rpm") # To be adapted if rpm_max data is not available
        
    def RpmMaxUpdate (self, rpm_max):
        """Updates the max RPM value for the meter display by rounding to the immediate thousands up"""
        self.rpm_meter_ticks_number = (int(rpm_max / 1000) + 1)
        self.rpm_max_meter = self.rpm_meter_ticks_number * 1000
    
    def RpmMeterConfig(self, rpm_max):
        self.RpmMaxUpdate (rpm_max)
        intervals = range(0, int(self.rpm_max_meter + 1), int(self.rpm_max_meter / self.rpm_meter_ticks_number))
        self.rpmMeter.SetIntervals(intervals)
        colours = [wx.BLACK]*self.rpm_meter_ticks_number
        self.rpmMeter.SetIntervalColours(colours)
        ticks = [str(interval) for interval in intervals]
        self.rpmMeter.SetTicks(ticks)
        self.rpmMeter.SetTicksColour(wx.WHITE)
        self.rpmMeter.SetNumberOfSecondaryTicks(1)
        self.rpmMeter.DrawExternalArc(False)
    
    def sub_listener_track_progress(self, message):
        self.progressBar.SetValue(int(message * 100))
    
    def sub_listener_track_duration(self, message):
        sec = message % 60
        min = int(message / 60)
        self.raceTimeLed.SetValue("{:0>2d}".format(min) + ':' + "{:0>2d}".format(sec))
        
    def sub_listener_gear(self, message):
        if (int(message) == 10):
            self.gearLed.SetValue(str(9))
        else:
            self.gearLed.SetValue(str(int(message)))
        
    def sub_listener_rpm(self, message):
        if (message < self.rpm_max_meter) and (message > 0):
            self.rpmMeter.SetSpeedValue(int(message))
        else:
            self.rpmMeter.SetSpeedValue(self.rpm_max_meter)
        
    def sub_listener_max_rpm(self, message):
        if (message != self.rpm_max):
            self.rpm_max = message
            self.RpmMeterConfig(message)
        else:
            pass
        
    def sub_listener_speed(self, message):
        if message > 0:
            if message < self.speed_max_meter:
                self.speedMeter.SetSpeedValue(int(message))
            else:
                self.speedMeter.SetSpeedValue(self.speed_max_meter)
        else:
            self.speedMeter.SetSpeedValue(int(message) * (-1))


# ======================================================================================
class MainFrame(wx.Frame):
    """
    Main program frame
    """
    
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(MainFrame, self).__init__(*args, **kw)
        
        # create a menu bar
        self.makeMenuBar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("Welcome to DR2 logger WX!")
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Add console panel
        self.PanelConsole = PanelConsole(self)
        
        # Add main panel
        self.PanelSerial = PanelSerial(self)
        
        # Add Logger panel
        self.PanelLogger = PanelLogger(self)
        
        # Add Dashboard panel
        self.PanelDashboard = PanelDashboard(self)
        
        # Add CMD panel
        self.PanelDeviceCommunication = PanelDeviceCommunication(self)
        
        vbox.Add(self.PanelSerial, 0, wx.EXPAND | wx.UP, 5)
        vbox.Add(self.PanelDeviceCommunication, 1, wx.EXPAND)
        
        
        """https://discuss.wxpython.org/t/help-with-paintevents-and-displaying-multiple-panels/34913"""
        self.main_ui_grid_sizer = wx.GridBagSizer(vgap = 0, hgap = 0)
        self.main_ui_grid_sizer.Add(vbox, pos=(0,0))
        self.main_ui_grid_sizer.Add(self.PanelConsole, pos=(0,1), flag=wx.EXPAND)
        self.main_ui_grid_sizer.Add(self.PanelLogger, pos=(1,0), flag=wx.EXPAND)
        self.main_ui_grid_sizer.Add(self.PanelDashboard, pos=(1,1), flag=wx.EXPAND)
        
        self.SetSizer(self.main_ui_grid_sizer)
        
        self.Fit()
        
        # Subscribe to general configs
        pub.subscribe(self.sub_listener, "config_general")

    def makeMenuBar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """

        # Make a file menu with Hello and Exit items
        fileMenu = wx.Menu()
        # The "\t..." syntax defines an accelerator key that also triggers
        # the same event
        helloItem = fileMenu.Append(-1, "&Hello...\tCtrl-H",
                "Help string shown in status bar for this menu item")
        loadConfigItem = fileMenu.Append(-1, "&Load configuration...\tCtrl-L",
                "Loads a configuration file")
        fileMenu.AppendSeparator()
        # When using a stock ID we don't need to specify the menu item's
        # label
        exitItem = fileMenu.Append(wx.ID_EXIT)

        # Now a help menu for the about item
        helpMenu = wx.Menu()
        aboutItem = helpMenu.Append(wx.ID_ABOUT)

        # Make the menu bar and add the two menus to it. The '&' defines
        # that the next letter is the "mnemonic" for the menu item. On the
        # platforms that support it those letters are underlined and can be
        # triggered from the keyboard.
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(helpMenu, "&Help")

        # Give the menu bar to the frame
        self.SetMenuBar(menuBar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        self.Bind(wx.EVT_MENU, self.OnHello, helloItem)
        self.Bind(wx.EVT_MENU, self.OnLoadConfig, loadConfigItem)
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)

    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)
    
    def OnCloseFrame(self, event):
        """Function bound to the close event"""
        self.PanelDeviceCommunication.Close()
        self.Destroy()

    def OnHello(self, event):
        """Say hello to the user."""
        wx.MessageBox("Hello again from wxPython")

    def OnAbout(self, event):
        """Display an About Dialog"""
        wx.MessageBox("This is a wxPython adaptation of DR2 logger",
                      "About DR2 logger WX",
                      wx.OK|wx.ICON_INFORMATION)
    
    def OnLoadConfig(self, event):
        """Display a load dialog"""
        with wx.FileDialog(self, "Open configuration file", wildcard="YAML files (*.yml)|*.yml",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, 'r') as file:
                    self.ParseConfigFile(file)
                    pass
            except IOError:
                # wx.LogError("Cannot open file '%s'." % newfile)
                print("Cannot open file '%s'." % newfile)
    
    def ParseConfigFile(self, file):
        print("Loading new configuration ...")
        # Load YAML file
        # Dump all categories and publish to each channel
        print(file.name)
        stream = yaml.full_load(file)
        for item, doc in stream.items():
            print(item, ":", doc) # DEBUG
            for obj in doc:
                pub.sendMessage(item, message=obj)
                # TODO : modify listener functions to accept data
    
    def sub_listener(self, message):
        """
        Listener function
        """
        pass


if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    
    frm = MainFrame(None, title='DR2 logger WX')
    
    # Set custom icon
    frm.SetIcon(wx.Icon("assets/randagodron_icon_16x16.png"))
    
    frm.Show()
    
    # # Overload print to redirect stdout to the console panel
    # """https://stackoverflow.com/questions/550470/overload-print-python"""
    # old_stdout = sys.stdout
    # new_stdout = frm.PanelConsole
    # sys.stdout = new_stdout
    
    app.MainLoop()
    
    # # Rollback to standard stdout
    # sys.stdout = old_stdout