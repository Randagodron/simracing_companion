#!/usr/bin/env python
"""
Hello World, but with more meat.
"""

import wx
import serial

class MainFrame(wx.Frame):
    """
    A Frame that says Hello World
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
        sizer             = wx.BoxSizer(wx.VERTICAL)
        
        # Top left sizer : serial config
        buttonRefresh     = wx.Button(pnl, label="Refresh", size=wx.Size(100, 32))
        buttonConnect     = wx.Button(pnl, label="Connect", size=wx.Size(100, 32))
        serialList        = wx.Choice(pnl, choices=["COMx", "COMy", "COMz"])
        
        topleftSizer.Add(serialList, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        topleftSizer.Add(buttonRefresh, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        topleftSizer.Add(buttonConnect, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
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
        
        # Bottom sizer : console output
        consoleTextCtrl   = wx.TextCtrl(pnl, size=wx.Size(600, 600), style=wx.TE_MULTILINE|wx.TE_READONLY)
        
        bottomSizer.Add(consoleTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        # Main frame sizer
        sizer.Add(topSizer, 1, wx.ALL|wx.EXPAND|wx.CENTER)
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
        
        # self.Update()
        # self.Layout()
        # self.Refresh()
        # self.Center()
        self.Show()
        # self.Layout()
        # self.Update()

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
    frm.SetIcon(wx.Icon("randagodron_icon_16x16.png"))
    
    frm.Show()
    app.MainLoop()