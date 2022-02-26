DR2 logger WX
=============

Simracing companion software for telemetry logging and accessories management.

![Preview of the GUI](/assets/screenshot_gui.PNG)

This program is a mix of [Billiam's pygauge](https://github.com/Billiam/pygauge) and [ErlerPhilipp's dr2_logger](https://github.com/ErlerPhilipp/dr2_logger). The aim of this program is to read and record telemtry data from racing video games (using dr2_logger) and, in parallel, send data to an external device through UART, while also receiving data from UART. You can see this as a free and open-source cheap alternative to [Simhub](https://www.simhubdash.com/).

And when I mean "cheap", I mean "it really does the bare minimum".

My original goal with this program was to have a tool for communication with external devices through serial communication, allowing easy development of companion applications for embedded systems. The basic architecture is designed in order to allow further customisation of the interface for adaptation to other applications.

Here, application is:
- Read and log telemetry data coming from the game, by reading ad-hoc UDP port,
- Display relevant data in real time, like speed, RPM, track progress, gear, hopefully in a fancy way,
- Format these data and send them to an external device through UART, in order to allow the usage of an external "basic" dashboard,

Additional and future features include:
- Extend compatibility to Richard Burns Rally (I don't plan to extend further than Dirt 1, 2 and RBR),
- Receive data from the external dashboard, for inputs like handbrake, gear shaft, buttons ... and transmit commands to the game.

Usage
-----

Run:

    python3 main.py

Upper-left : serial module, manages the serial communication. The drop-down menu contains the list of detected serial devices. "Connect" button initiates the connection to the selected device. The value selector changes the UART message sending periodicity (in milliseconds). The "Test" button allows automatic sending of random values for test purposes.

Upper-right : console output.

Lower-left : Logger controls (main menu of dr2_loger).

Lower-right : dash display, shows SPeed, RPMs, gear, track progress, time in seconds. RPM meter automatically scales according to the max_rpm value received from the game.

Architecture
------------

This program is written in Python 3 (side note : I am bad at writing code in Python) using threading, pyserial, [WXpython](https://www.wxpython.org/) for the GUI.

The main philosophy for the GUI is to use dedicated panels for each macro function : serial communication, serial data parsing and formatting, logging, dash display inside the GUI, console prints ...

The communication between the panels and other modules is done through the use of [pubsub](https://wiki.wxpython.org/Controlling%20GUI%20with%20pubsub). This allows flexible non-blocking communication : channels are attached to functionalities rather than the objects or modules themselves, allowing multiple modules to have simultaneous asynchronous access to the same data. This dissociates the modules from the mechanisms that allow communication between them and makes architecture easier to build. It has to be noted that pubsub has performance issues. I will use it as long as it is bearable for my use, but I shall switch to another more efficient mechanism if required.

It basically re-uses the code from [dr2_logger](https://github.com/ErlerPhilipp/dr2_logger) with some modifications:
- Same architecture with a main interface, logger_backend, and custom classes for each different game,
- Main is completely replaced in order to integrate in the WX GUI,
- Console output / print function is redirected in order to be displayed in the console display of the GUI,
- Console display of the track time and progression is removed since flush() is not working correctly in WX text control objects. I tried to implement it, result is jerky and highly CPU intensive, not worth it.
- More methods are added in order to get relevant specific info from the telemetry datagram.

Support for Richard Burns Rally will be added in the future by creating a new class, similar to those for Dirt 1 and 2.

For the external device communication, I took as first step the protocol used in [pygauge](https://github.com/Billiam/pygauge), for simplicity's sake. I plan to modify the protocol in order to have easier compatibility with Simhub.

Companion embedded software
---------------------------

Soon ! But this will be released in a separate repository.

I have build a dash screen based on the [STMicroelectronics Discovery STM32F746NG demo board](https://www.st.com/en/evaluation-tools/32f746gdiscovery.html), using [STM32CubeIDE](https://www.st.com/en/development-tools/stm32cubeide.html) for the development of the embedded software, and [TouchGFX](https://www.st.com/en/development-tools/touchgfxdesigner.html) for the development of the GUI. The case is made from laser cut wood from a console2 design in [boxes.py](https://www.festi.info/boxes.py/?language=en).

![External dashboard](/assets/dash_external.jpg)

My approach is to have a single external device that will manage the external display and the reading of the accessories inputs. At the moment I use the USB device library in order to provide a HID connection to the PC for the inputs, the serial data for the dash display being sent through the VCOM of the debug USB. My goal is to have everything multiplexed in the VCOM, in order to have only one USB cable.

