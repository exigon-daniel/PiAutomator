"""
This input module supports getting data from pilight (http://http://www.pilight.org/) and triggering rules accordingly
"""
from itertools import dropwhile
import logging
import tempfile
import threading
import re
import serial
import sys
from inputs import AnInput

def _true(value = None):
    return True

def _false(value = None):
    return False

lllap_sensors = {}
__logger__ = logging.getLogger('llap-receiver')
__logger__.setLevel(logging.INFO)

llap_commands = {
    'BATTLOW': ['lowbattery', _true],
    'BATT': ['batterylevel', float],
    'STARTED': ['lowbattery', _false],
    'LVAL': ['lightlevel', float],
    'TEMP': ['temperature', float],
    'TMPA': ['temperature', float],
    'ANA': ['analog', int],
    'BUTTON': ['button', str]
}

def init(config):
    """
    Initializes the pilight receiver connection. Sets up a heartbeat

    @type config: config.AutomationConfig
    """

    receiver = LLAPDaemon(
        config.getSetting(['llap','device'], '/dev/ttyAMA0'),
        config.getSetting(['llap','print-debug'], False)
    )
    thread = threading.Thread(target=receiver.receive)
    thread.daemon = True
    thread.start()

class LLAP(AnInput):
    def __init__(self,  name, context, settings):
        super(LLAP, self).__init__(name, context, settings)
        self.device_id = settings['device-id']
        self.values = None
        lllap_sensors[self.device_id] = self

    def update(self, sentcommand):
        if not self.started: return
        for command in sorted(llap_commands, key=lambda x: len(x), reverse=True):
            if sentcommand.startswith(command):
                value = sentcommand[len(command):]
                key = llap_commands[command][0]
                converter = llap_commands[command][1]
                self.publish({key: converter(value)})
                return

class LLAPDaemon(object):
    def __init__(self, device, debug):
        self.p = re.compile('a[A-Z][A-Z][A-Z0-9.-]{9,}.*')
        self.ser = serial.Serial(device, 9600)
        self.debug = debug
        self.current_buffer = ""
        if (debug):
            self.debug_file = tempfile.NamedTemporaryFile()
            __logger__.info("Debugging serial input to %s", self.debug_file.name)
            self.debug_file.write("----- Serial input debug file -----\n")
            self.debug_file.flush()

    def receive(self):
        __logger__.info("Starting in receiving mode for llap")
        try:
            while True:
                self.current_buffer += self.__read__(1)
                n = self.ser.inWaiting()
                if (n > 0):
                    self.current_buffer += self.__read__(n)
                self.find_messages()
        except:
            __logger__.exception(sys.exc_info()[0])
            __logger__.warn("exception happened")

    def __read__(self, size = 1):
        result = self.ser.read(size)
        if self.debug:
            # Nice thing about tmp files is that Python will clean them on
            # system close
            self.debug_file.write(result)
            self.debug_file.flush()
        return result

    def find_messages(self):
        try:
            self.current_buffer = ''.join(dropwhile(lambda x: not x == 'a', (i for i in self.current_buffer)))
            if len(self.current_buffer) >= 12:  # 12 is the LLAP message length
                 if self.p.match(self.current_buffer):
                     self.process_device_message(self.current_buffer[0:12])
                     self.current_buffer = self.current_buffer[12:]
                 else:
                     self.current_buffer = self.current_buffer[1:]
                     self.find_messages()
        except:
            __logger__.exception(sys.exc_info()[0])
            __logger__.warn("exception happened")

    def process_device_message(self, message):
        device = message[1:3]
        command = message[3:].replace('-','')
        if command == 'HELLO':
            __logger__.info("%s said hello", device)
        elif command.startswith("CHDEVID"):
            __logger__.info("We were asked to change our device id, but we're only listening:), %s", command)
        elif device in lllap_sensors:
            llap_sensor = lllap_sensors[device]
            llap_sensor.update(command)
