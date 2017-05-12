"""Client tests that run against the standard TangoTest device.

Due to a TANGO 9 issue (#821), the device is run without any database.
Note that this means that various features won't work:

 * No device configuration via properties.
 * No event generated by the server.
 * No memorized attributes.
 * No device attribute configuration via the database.

So don't even try to test anything of the above as it will not work
and is even likely to crash the device (!)

"""

from distutils.spawn import find_executable
from subprocess import Popen
import platform
from time import sleep

import psutil
import pytest
from functools import partial
from tango import DeviceProxy, DevFailed, GreenMode
from tango import DeviceInfo, AttributeInfo, AttributeInfoEx
from tango.utils import is_str_type, is_int_type, is_float_type, is_bool_type

from tango.gevent import DeviceProxy as gevent_DeviceProxy
from tango.futures import DeviceProxy as futures_DeviceProxy
from tango.asyncio import DeviceProxy as asyncio_DeviceProxy

ATTRIBUTES = [
    'ampli',
    'boolean_scalar',
    'double_scalar',
    'double_scalar_rww',
    'double_scalar_w',
    'float_scalar',
    'long64_scalar',
    'long_scalar',
    'long_scalar_rww',
    'long_scalar_w',
    'no_value',
    'short_scalar',
    'short_scalar_ro',
    'short_scalar_rww',
    'short_scalar_w',
    'string_scalar',
    'throw_exception',
    'uchar_scalar',
    'ulong64_scalar',
    'ushort_scalar',
    'ulong_scalar',
    'boolean_spectrum',
    'boolean_spectrum_ro',
    'double_spectrum',
    'double_spectrum_ro',
    'float_spectrum',
    'float_spectrum_ro',
    'long64_spectrum_ro',
    'long_spectrum',
    'long_spectrum_ro',
    'short_spectrum',
    'short_spectrum_ro',
    'string_spectrum',
    'string_spectrum_ro',
    'uchar_spectrum',
    'uchar_spectrum_ro',
    'ulong64_spectrum_ro',
    'ulong_spectrum_ro',
    'ushort_spectrum',
    'ushort_spectrum_ro',
    'boolean_image',
    'boolean_image_ro',
    'double_image',
    'double_image_ro',
    'float_image',
    'float_image_ro',
    'long64_image_ro',
    'long_image',
    'long_image_ro',
    'short_image',
    'short_image_ro',
    'string_image',
    'string_image_ro',
    'uchar_image',
    'uchar_image_ro',
    'ulong64_image_ro',
    'ulong_image_ro',
    'ushort_image',
    'ushort_image_ro',
    'wave',
    'State',
    'Status',
]

device_proxy_map = {
    GreenMode.Synchronous: DeviceProxy,
    GreenMode.Futures: futures_DeviceProxy,
    GreenMode.Asyncio: partial(asyncio_DeviceProxy, wait=True),
    GreenMode.Gevent: gevent_DeviceProxy}


# Helpers

def get_ports(pid):
    p = psutil.Process(pid)
    conns = p.connections(kind="tcp")
    # Sorting by family in order to make any IPv6 address go first.
    # Otherwise there's a 50% chance that the proxy will just
    # hang (presumably because it's connecting on the wrong port)
    # This works on my machine, not sure if it's a general
    # solution though.
    conns = reversed(sorted(conns, key=lambda c: c.family))
    return [c.laddr[1] for c in conns]


def start_server(server, inst, device):
    exe = find_executable(server)
    cmd = ("{0} {1} -ORBendPoint giop:tcp::0 -nodb -dlist {2}"
           .format(exe, inst, device))
    proc = Popen(cmd.split())
    proc.poll()
    return proc


def get_proxy(host, port, device, green_mode):
    access = "tango://{0}:{1}/{2}#dbase=no".format(
        host, port, device)
    return device_proxy_map[green_mode](access)


def wait_for_proxy(host, proc, device, green_mode, retries=100, delay=0.01):
    for i in range(retries):
        ports = get_ports(proc.pid)
        if ports:
            try:
                proxy = get_proxy(host, ports[0], device, green_mode)
                proxy.ping()
                proxy.state()
                return proxy
            except DevFailed:
                pass
        sleep(delay)
    else:
        raise RuntimeError("TangoTest device did not start up!")


# Fixtures

@pytest.fixture(params=[GreenMode.Synchronous,
                        GreenMode.Asyncio,
                        GreenMode.Gevent],
                scope="module")
def tango_test(request):
    green_mode = request.param
    server = "TangoTest"
    inst = "test"
    device = "sys/tg_test/17"
    host = platform.node()
    proc = start_server(server, inst, device)
    proxy = wait_for_proxy(host, proc, device, green_mode)

    yield proxy

    proc.terminate()
    # let's not wait for it to exit, that takes too long :)


@pytest.fixture(params=ATTRIBUTES)
def attribute(request):
    return request.param


@pytest.fixture(params=[a for a in ATTRIBUTES
                        if a not in ("no_value", "throw_exception")])
def readable_attribute(request):
    return request.param


@pytest.fixture(params=[a for a in ATTRIBUTES
                        if "scalar" in a and
                        a.split("_")[-1] not in ("ro", "rww")])
def writable_scalar_attribute(request):
    return request.param


# Tests

def test_ping(tango_test):
    duration = tango_test.ping(wait=True)
    assert isinstance(duration, int)


def test_info(tango_test):
    info = tango_test.info()
    assert isinstance(info, DeviceInfo)
    assert info.dev_class == "TangoTest"
    # ...


def test_read_attribute(tango_test, readable_attribute):
    "Check that readable attributes can be read"
    # This is a hack:
    # Without this sleep, the following error is very likely to be raised:
    # -> MARSHAL CORBA system exception: MARSHAL_PassEndOfMessage
    if readable_attribute in ["string_image_ro", "string_spectrum_ro"]:
        sleep(0.05)
    tango_test.read_attribute(readable_attribute, wait=True)


def test_write_scalar_attribute(tango_test, writable_scalar_attribute):
    "Check that writable scalar attributes can be written"
    attr_name = writable_scalar_attribute
    config = tango_test.get_attribute_config(writable_scalar_attribute)
    if is_bool_type(config.data_type):
        tango_test.write_attribute(attr_name, True, wait=True)
    elif is_int_type(config.data_type):
        tango_test.write_attribute(attr_name, 76, wait=True)
    elif is_float_type(config.data_type):
        tango_test.write_attribute(attr_name, -28.2, wait=True)
    elif is_str_type(config.data_type):
        tango_test.write_attribute(attr_name, "hello", wait=True)
    else:
        pytest.xfail("Not currently testing this type")


def test_read_attribute_config(tango_test, attribute):
    tango_test.get_attribute_config(attribute)


def test_attribute_list_query(tango_test):
    attrs = tango_test.attribute_list_query()
    assert all(isinstance(a, AttributeInfo) for a in attrs)
    assert set(a.name for a in attrs) == set(ATTRIBUTES)


def test_attribute_list_query_ex(tango_test):
    attrs = tango_test.attribute_list_query_ex()
    assert all(isinstance(a, AttributeInfoEx) for a in attrs)
    assert set(a.name for a in attrs) == set(ATTRIBUTES)


def test_device_proxy_dir_method(tango_test):
    lst = dir(tango_test)
    attrs = tango_test.get_attribute_list()
    cmds = tango_test.get_command_list()
    pipes = tango_test.get_pipe_list()
    methods = dir(type(tango_test))
    internals = tango_test.__dict__.keys()
    # Check attributes
    assert set(attrs) < set(lst)
    assert set(map(str.lower, attrs)) < set(lst)
    # Check commands
    assert set(cmds) < set(lst)
    assert set(map(str.lower, cmds)) < set(lst)
    # Check pipes
    assert set(pipes) < set(lst)
    assert set(map(str.lower, pipes)) < set(lst)
    # Check internals
    assert set(methods) <= set(lst)
    # Check internals
    assert set(internals) <= set(lst)


def test_device_polling_command(tango_test):

    dct = {"SwitchStates": 1000, "DevVoid": 10000, "DumpExecutionState": 5000}

    for command, period in dct.items():
        tango_test.poll_command(command, period)

    ans = tango_test.polling_status()
    for info in ans:
        lines = info.split('\n')
        command = lines[0].split('= ')[1]
        period = int(lines[1].split('= ')[1])
        assert dct[command] == period


def test_device_polling_attribute(tango_test):

    dct = {"boolean_scalar": 1000, "double_scalar": 10000, "long_scalar": 5000}

    for attr, poll_period in dct.items():
        tango_test.poll_attribute(attr, poll_period)

    ans = tango_test.polling_status()
    for x in ans:
        lines = x.split('\n')
        attr = lines[0].split('= ')[1]
        poll_period = int(lines[1].split('= ')[1])
        assert dct[attr] == poll_period
