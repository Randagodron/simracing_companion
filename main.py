#!/usr/bin/env python
"""
DR2 logger with wxPython GUI
Following : https://wiki.wxpython.org/wxPython%20Style%20Guide
"""

import wx
from pubsub import pub

import serial
from serial.tools import list_ports

import os
import sys
import threading
import queue

from source.logger_backend import LoggerBackend

log_raw_data = False
debugging = False

version_string = '(Version 2.0.0, 2022-01-16)'
# TODO: update date

ID_STARTLOG = 100

# Global variables
logger_stared = False

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

def udp_listen(print_function):
    global logger_backend
    
    while logger_stared:
        logger_backend.check_udp_messages()
        print_current_state(logger_backend.get_game_state_str())
        
        message = logger_backend.check_state_changes()
        if len(message) > 0:
            print_function(message)

def thread_dr2logger_init(print_function):
    global logger_backend
    
    end_program = False

    # print_function(commands_hint)
    print_function(intro_text)

    # logger_backend = LoggerBackend(debugging=debugging, log_raw_data=log_raw_data)
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


class PanelSerial(wx.Panel, object):
    """Main panel"""
    def __init__(self, parent, *args, **kwargs):
        """Create the PanelSerial."""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        # COM ports
        # Serial ports
        ports = serial.tools.list_ports.comports()
        ports_list = [] # List of ports references
        ports_description_list = [] # List of serial ports descriptions, for ease of identification on GUI
        
        # Scan for COM ports
        self.scan_com_ports(ports, ports_list, ports_description_list)
        
        # print(ports_description_list) # DEBUG
        # pub.sendMessage("print_console", message=', '.join(ports_description_list)) # DEBUG
        
        buttonRefresh     = wx.Button(self, label="Refresh", size=wx.Size(100, 32))
        buttonRefresh.Bind(wx.EVT_BUTTON, self.OnClickPortsRefresh)
        
        listSerialPorts   = wx.Choice(self, choices=ports_description_list)
        listSerialPorts.Bind(wx.EVT_CHOICE, self.getOnSelectSerial(listSerialPorts))
        
        buttonConnect     = wx.Button(self, label="Connect", size=wx.Size(100, 32))
        buttonConnect.Bind(wx.EVT_BUTTON, self.getOnClickPortsConnect(ports_list, listSerialPorts.GetCurrentSelection()))
        
        sizer      = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listSerialPorts, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer.Add(buttonRefresh, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer.Add(buttonConnect, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.SetSizer(sizer)
        self.Layout()
        
        msg = "test"
        
    
    def OnClickPortsRefresh(self, event):
        # self.scan_com_ports()
        # print("Refresh\n") # DEBUG
        # pub.sendMessage("print_console", message="Refresh") # DEBUG
        pass
        
    
    def getOnClickPortsConnect(self, ports_list, port_current_selection):
        def OnClickPortsConnect(event):
            # pub.sendMessage("print_console", message="Ports connect") # DEBUG
            ser = serial.Serial(ports_list[port_current_selection], 115200)
            # print(ser.name) # DEBUG
            pub.sendMessage("print_console", message=ser.name)
        return OnClickPortsConnect
        
    
    """https://stackoverflow.com/questions/173687/is-it-possible-to-pass-arguments-into-event-bindings"""
    def getOnSelectSerial(self, list_serial_ports):
        def OnSelectSerial(event):
            # pub.sendMessage("print_console", message="Port selected") # DEBUG
            # print("Serial port selected : %d\n" % list_serial_ports.GetCurrentSelection()) # DEBUG
            pub.sendMessage("print_console", message="Serial port selected : %d\n" % (list_serial_ports.GetCurrentSelection()))
            # pub.sendMessage("print_console", message="Serial port selected : %d - %s\n" % (list_serial_ports.GetCurrentSelection(), list_serial_ports[list_serial_ports.GetCurrentSelection()].device % " - " % list_serial_ports[list_serial_ports.GetCurrentSelection()].description))
        return OnSelectSerial
    
    
    def scan_com_ports(self, ports, ports_list, ports_description_list):
        """
        Scans the available COM ports, creates a list and fills the corresponding wx.choice
        """
        # self.consoleTextCtrl.AppendText("Searching for COM ports ...\n")
        # print("Searching for COM ports ...\n") # DEBUG
        pub.sendMessage("print_console", message="Searching for COM ports ...\n")
        for port in ports :
            ports_list.append(port.device) # Get port reference
            ports_description_list.append(port.device + " - " + port.description) # Construct a description for the GUI list
            # self.consoleTextCtrl.AppendText("COM port found : %s\n" % (port.device + " - " + port.description))
            # print("COM port found : %s\n" % (port.device + " - " + port.description)) # DEBUG
            pub.sendMessage("print_console", message="COM port found : %s\n" % (port.device + " - " + port.description))


class PanelConsole(wx.Panel, object):
    """Console panel"""
    def __init__(self, parent, *args, **kwargs):
        """Create the Console panel"""
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        
        self.consoleTextCtrl   = wx.TextCtrl(self, size=wx.Size(600, 600), style=wx.TE_MULTILINE|wx.TE_READONLY)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.consoleTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        self.SetSizer(sizer)
        self.Layout()
        
        pub.subscribe(self.sub_listener, "print_console")
        
    
    def print_console(self, text):
        self.consoleTextCtrl.AppendText(text)
        
    
    def sub_listener(self, message):
        """
        Listener function
        https://github.com/schollii/pypubsub/tree/master/examples/basic_kwargs
        """
        self.print_console(message)


class MainFrame(wx.Frame):
    """
    Main program frame
    """
    
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        # super(MainFrame, self).__init__(*args, **kw, size=(1000, 800))
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
        
        # vbox.Add(self.PanelSerial, 0, wx.EXPAND | wx.UP, 5)
        # vbox.Add(self.PanelConsole, 1, wx.EXPAND)
        # vbox.Add((3, -1))
        
        # panel.SetSizer(vbox)
        
        # self.Fit()
        # self.Layout()
        
        """https://discuss.wxpython.org/t/help-with-paintevents-and-displaying-multiple-panels/34913"""
        self.main_ui_grid_sizer = wx.GridBagSizer(vgap = 0, hgap = 0)
        # self.main_ui_grid_sizer.Add(self.PanelSerial, pos=(0,0), flag=wx.EXPAND)
        self.main_ui_grid_sizer.Add(self.PanelSerial, pos=(0,0))
        self.main_ui_grid_sizer.Add(self.PanelConsole, pos=(0,1), flag=wx.EXPAND)
        
        self.SetSizer(self.main_ui_grid_sizer)
        
        self.Fit()

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
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)


    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)


    def OnHello(self, event):
        """Say hello to the user."""
        wx.MessageBox("Hello again from wxPython")


    def OnAbout(self, event):
        """Display an About Dialog"""
        wx.MessageBox("This is a wxPython adaptation of DR2 logger",
                      "About DR2 logger WX",
                      wx.OK|wx.ICON_INFORMATION)


if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    frm = MainFrame(None, title='DR2 logger WX')
    
    # Set custom icon
    frm.SetIcon(wx.Icon("assets/randagodron_icon_16x16.png"))
    
    frm.Show()
    
    # thread_dr2logger_init()
    
    app.MainLoop()