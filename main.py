#!/usr/bin/env python
"""
DR2 logger with wxPython GUI
"""

import wx
import serial

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

class MainFrame(wx.Frame):
    """
    Main program frame
    """
    
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        # super(MainFrame, self).__init__(*args, **kw, size=(1000, 800))
        super(MainFrame, self).__init__(*args, **kw)

        # create a panel in the frame
        pnl = wx.Panel(self)

        # put some text with a larger bold font on it
        # st = wx.StaticText(pnl, label="DR2 logger WX")
        # font = st.GetFont()
        # font.PointSize += 10
        # font = font.Bold()
        # st.SetFont(font)

        topSizer          = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer       = wx.BoxSizer(wx.VERTICAL)
        topleftSizer      = wx.BoxSizer(wx.VERTICAL)
        toprightSizer     = wx.BoxSizer(wx.VERTICAL)
        middleSizer       = wx.BoxSizer(wx.HORIZONTAL)
        sizer             = wx.BoxSizer(wx.VERTICAL)
        
        # Top left sizer : serial config
        self.buttonRefresh     = wx.Button(pnl, label="Refresh", size=wx.Size(100, 32))
        self.buttonConnect     = wx.Button(pnl, label="Connect", size=wx.Size(100, 32))
        self.listSerialPorts   = wx.Choice(pnl, choices=["COMx", "COMy", "COMz"])
        
        topleftSizer.Add(self.listSerialPorts, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        topleftSizer.Add(self.buttonRefresh, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        topleftSizer.Add(self.buttonConnect, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        # Top right sizer : application parameters
        button1     = wx.Button(pnl, label="1", size=wx.Size(100, 30), style = wx.ALIGN_LEFT)
        button2     = wx.Button(pnl, label="2", size=wx.Size(100, 30), style = wx.ALIGN_LEFT)
        button3     = wx.Button(pnl, label="3", size=wx.Size(100, 30), style = wx.ALIGN_LEFT)
        button4     = wx.Button(pnl, label="4", size=wx.Size(100, 30), style = wx.ALIGN_LEFT)
        
        toprightSizer.Add(button1, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        toprightSizer.Add(button2, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        toprightSizer.Add(button3, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        toprightSizer.Add(button4, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        # Top sizer
        topSizer.Add(topleftSizer, 1, wx.ALL|wx.EXPAND|wx.CENTER)
        topSizer.Add(toprightSizer, 1, wx.ALL|wx.EXPAND|wx.CENTER)
        
        # Middle sizer : logger controls
        self.listGame        = wx.Choice(pnl, choices=["DiRT 1", "DiRT 2.0", "Richard Burns Rally"])
        self.buttonClearRun  = wx.Button(pnl, label="Clear run", size=wx.Size(100, 32))
        self.buttonPlot      = wx.Button(pnl, label="Plot", size=wx.Size(100, 32))
        self.buttonPlotAll   = wx.Button(pnl, label="PlotAll", size=wx.Size(100, 32))
        self.buttonSave      = wx.Button(pnl, label="Save", size=wx.Size(100, 32))
        self.buttonLoad      = wx.Button(pnl, label="Load", size=wx.Size(100, 32))
        
        middleSizer.Add(self.listGame, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        middleSizer.Add(self.buttonClearRun, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        middleSizer.Add(self.buttonPlot, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        middleSizer.Add(self.buttonPlotAll, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        middleSizer.Add(self.buttonSave, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        middleSizer.Add(self.buttonLoad, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        # Bottom sizer : console output
        self.button_loggerStart  = wx.Button(pnl, label="Start logging", size=wx.Size(100, 30), style = wx.ALIGN_LEFT)
        self.consoleTextCtrl   = wx.TextCtrl(pnl, size=wx.Size(600, 600), style=wx.TE_MULTILINE|wx.TE_READONLY)
        
        bottomSizer.Add(self.button_loggerStart, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        bottomSizer.Add(self.consoleTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        # Main frame sizer
        sizer.Add(topSizer, 1, wx.ALL|wx.EXPAND|wx.CENTER)
        sizer.Add(wx.StaticLine(pnl,), 0, wx.ALL|wx.EXPAND, 5)
        sizer.Add(middleSizer, 1, wx.ALL|wx.EXPAND|wx.CENTER)
        sizer.Add(wx.StaticLine(pnl,), 0, wx.ALL|wx.EXPAND, 5)
        sizer.Add(bottomSizer, 2, wx.ALL|wx.EXPAND|wx.CENTER)
        
        # create a menu bar
        self.makeMenuBar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("Welcome to DR2 logger WX!")
        
        pnl.SetSizer(sizer)
        pnl.SetAutoLayout(1)
        # pnl.SetSize((1000, 800))
        sizer.Fit(self)
        
        self.Show()
        
        # Bind start logging button
        self.Bind(wx.EVT_BUTTON, self.OnClickStartLogging, self.button_loggerStart)
        self.Bind(wx.EVT_BUTTON, self.OnClickClearRun, self.buttonClearRun)
        self.Bind(wx.EVT_BUTTON, self.OnClickPlot, self.buttonPlot)
        self.Bind(wx.EVT_BUTTON, self.OnClickPlotAll, self.buttonPlotAll)
        self.Bind(wx.EVT_BUTTON, self.OnClickSave, self.buttonSave)
        self.Bind(wx.EVT_BUTTON, self.OnClickLoad, self.buttonLoad)
        self.Bind(wx.EVT_CHOICE, self.OnSelectGame, self.listGame)
        self.Bind(wx.EVT_CHOICE, self.OnSelectSerial, self.listSerialPorts)
        
        self.thread_udp = threading.Thread(target=udp_listen(self.print_log))

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

    def OnClickStartLogging(self, event):
        global logger_backend
        # Start / Stop DR2logger process
        global logger_stared
        if logger_stared==False:
            logger_stared=True
            self.button_loggerStart.SetLabel("Stop logging")
            thread_dr2logger_init(self.print_log)
            self.thread_udp.daemon = True
            self.thread_udp.start()
        else:
            logger_stared=False
            self.button_loggerStart.SetLabel("Start logging")
            self.thread_udp.join()
            logger_backend.end_logging()
    
    def print_log(self, text):
        self.consoleTextCtrl.AppendText(text)
        
    def OnClickClearRun(self, event):
        global logger_backend
        logger_backend.clear_session_collection()
        self.consoleTextCtrl.AppendText("Clear run\n") # DEBUG
    
    def OnClickPlot(self, event):
        global logger_backend
        self.consoleTextCtrl.AppendText("Plot relevant data\n") # DEBUG
        if logger_backend.get_num_samples() == 0:
            self.consoleTextCtrl.AppendText('No data points to plot\n')
        else:
            self.consoleTextCtrl.AppendText('Plotting {} data points\n'.format(logger_backend.get_num_samples()))
            logger_backend.show_plots(True)
        
    def OnClickPlotAll(self, event):
        global logger_backend
        self.consoleTextCtrl.AppendText("Plot all data\n") # DEBUG
        logger_backend.save_run()
    
    def OnClickSave(self, event):
        global logger_backend
        self.consoleTextCtrl.AppendText("Save run\n") # DEBUG
        logger_backend.save_run()
    
    def OnClickLoad(self, event):
        global logger_backend
        self.consoleTextCtrl.AppendText("Load run\n") # DEBUG
        logger_backend.load_run()
        print_current_state(logger_backend.get_game_state_str())
    
    def OnSelectGame(self, event):
        global logger_backend
        self.consoleTextCtrl.AppendText("Game selected : %d\n" % self.listGame.GetCurrentSelection()) # DEBUG
        if self.listGame.GetCurrentSelection() < len(LoggerBackend.get_all_valid_games()):
            new_game_name = LoggerBackend.get_all_valid_games()[self.listGame.GetCurrentSelection()]
            logger_backend.change_game(new_game_name)
            self.consoleTextCtrl.AppendText('Switched game to "{}"\n'.format(logger_backend.game_name))
        else:
            self.consoleTextCtrl.AppendText('Incorrect game index\n')
    
    def OnSelectSerial(self, event):
        self.consoleTextCtrl.AppendText("Serial port selected : %d\n" % self.listSerialPorts.GetCurrentSelection()) # DEBUG


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