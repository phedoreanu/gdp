'''
            GDP - The Generic Device Programmer.

    By Dean Camera (dean [at] fourwalledcubicle [dot] com)
'''

from devices import *
from formats import *
from tools import *


class SessionError(Exception):
    pass


class SessionMissingParamError(SessionError):
    def __init__(self, paramtype):
        self.message = "No %s specified." % paramtype


class SessionSupportError(SessionError):
    def __init__(self, paramtype, requested, supportlist=None):
        self.message = "Unknown or unsupported %s \"%s\"." % \
                       (paramtype, requested)

        if not supportlist is None:
            self.message += "\n\nSupported %ss are:" % paramtype

            if isinstance(supportlist, dict):
                for k in supportlist:
                    for v in supportlist[k]:
                        self.message += "\n  - %s (%s)" % (v, k)
            else:
                for s in supportlist:
                    self.message += "\n  - %s" % s


class Session(object):
    def __init__(self, options):
        try:
            tool_type = get_gdp_tool(options.tool)
        except KeyError:
            raise SessionSupportError("tool", options.tool,
                                      get_gdp_tool_aliases())

        if options.device is None:
            raise SessionMissingParamError("device")

        if options.tool is None:
            raise SessionMissingParamError("tool")

        if options.interface is None:
            tool_supported_interfaces = tool_type.get_supported_interfaces()

            if len(tool_supported_interfaces) == 1:
                options.interface = tool_supported_interfaces[0]
            else:
                raise SessionMissingParamError("interface")

        try:
            self.device = DeviceAtmelStudio(part=options.device)
        except DeviceError:
            raise SessionSupportError("device", options.device)

        self.tool = tool_type(device=self.device,
                              port=options.port,
                              serial=options.serial,
                              baud=options.baud,
                              interface=options.interface)
        self.protocol = self.tool.get_protocol()
        self.options = options


    def open(self):
        self.tool.open()

        if not self.options.no_verify_vtarget:
            device_vtarget = self.protocol.get_vtarget()
            dev_vccrange = self.device.get_vcc_range()

            if device_vtarget is not None and \
                not dev_vccrange[0] <= device_vtarget <= dev_vccrange[1]:
                raise SessionError("Device VCC range of (%0.2fV-%0.2fV) is outside "
                                   "the measured VTARGET of %0.2fV." %
                                   (dev_vccrange[0], dev_vccrange[1], device_vtarget))

        self.protocol.set_interface_frequency(self.options.frequency)
        self.protocol.enter_session()

        if not self.options.no_verify_signature:
            expected_signature = self.device.get_signature(self.options.interface)
            read_signature = self.protocol.read_memory("signatures", 0, len(expected_signature))

            if expected_signature[0 : len(read_signature)] != read_signature:
                raise SessionError("Read device signature [%s] does not match the "
                                   "expected signature [%s]." %
                                   (' '.join('0x%02X' % b for b in read_signature),
                                    ' '.join('0x%02X' % b for b in expected_signature)))


    def close(self):
        self.protocol.exit_session()
        self.tool.close()


    def get_protocol(self):
        return self.protocol


    def get_device(self):
        return self.device


    def get_tool(self):
        return self.tool
