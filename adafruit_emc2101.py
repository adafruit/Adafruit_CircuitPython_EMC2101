# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_emc2101`
================================================================================

Brushless fan controller


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit EMC2101 Breakout <https://adafruit.com/product/47nn>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import struct

from micropython import const
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits, ROBits
import adafruit_bus_device.i2c_device as i2cdevice

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EMC2101.git"

_INTERNAL_TEMP = const(0x00)
_EXTERNAL_TEMP_MSB = const(0x01)
_EXTERNAL_TEMP_LSB = const(0x10)

_STATUS = const(0x02)
_REG_CONFIG = const(0x03)
_TEMP_FORCE = const(0x0C)
_TACH_LSB = const(0x46)
_TACH_MSB = const(0x47)
_TACH_LIMIT_LSB = const(0x48)
_TACH_LIMIT_MSB = const(0x49)
_FAN_CONFIG = const(0x4A)
_FAN_SPINUP = const(0x4B)
_REG_FAN_SETTING = const(0x4C)
_LUT_HYSTERESIS = const(0x4F)

_TEMP_FILTER = const(0xBF)
_REG_PARTID = const(0xFD)  # 0x16
_REG_MFGID = const(0xFE)  # 0xFF16

MAX_LUT_SPEED = 0x3F  # 6-bit value
MAX_LUT_TEMP = 0x7F # 7-bit

_I2C_ADDR = const(0x4C)
_FAN_RPM_DIVISOR = const(5400000)
_TEMP_LSB = 0.125
def _h(val):
    return "0x{:02X}".format(val)


def _b(val):
    return "{:#010b}".format(val)
def _b16(val):
    return "{:#018b}".format(val)

def _speed_to_lsb(percentage):
    return round((percentage/100.0) * MAX_LUT_SPEED)

def _lsb_to_speed(lsb_speed):
    return round((lsb_speed/MAX_LUT_SPEED) * 100.0)
class FanSpeedLUT:
    def __init__(self, fan_obj):
        self.emc_fan = fan_obj
        self.lut_values = {}

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise IndexError
        if not index in self.lut_values:
            raise IndexError
        raise RuntimeError("not implemented")

    def __setitem__(self, index, value):
        print("SET ITEM[%d] => %f"%(index, value))
        if not isinstance(index, int):
            raise IndexError
        self.lut_values[index] = value
        self._set_lut(self.lut_values)

    def __repr__(self):
        """return the official string representation of the LUT"""
        return "FanSpeedLUT <%x>"%id(self)

    def __str__(self):
        """return the official string representation of the LUT"""
        value_strs = []
        for i in range(len(self.lut_values)):
            value_str = "%d : "%self.emc_fan._lut_temp_setters[i].__get__(self.emc_fan)
            value_str += str(_lsb_to_speed(self.emc_fan._lut_speed_setters[i].__get__(self.emc_fan)))
            value_strs.append(value_str)
        return "{"+", ".join(value_strs)+"}\nORRRRRR:"+str(self.lut_values)

    def __len__(self):
        return len(self.lut_values)

    def _set_lut(self, lut_dict):
        lut_keys = list(lut_dict.keys())
        lut_size =len(lut_dict)
        # Make sure we're not going to try to set more entries than we have slots
        if lut_size > 8:
            raise AttributeError("LUT can only contain a maximum of 8 items")

        # we want to assign the lowest temperature to the lowest LUT slot, so we sort the keys/temps
        for k in lut_keys:
            # Verify that the value is a correct amount
            lut_value = lut_dict[k]
            if lut_value > 100.0 or lut_value < 0:
                raise AttributeError("LUT values must be a fan speed from 0-100%")

            # add the current temp/speed to our internal representation
            self.lut_values[k] = lut_value
        current_mode = self.emc_fan.lut_enabled
        for k, v in self.lut_values.items():
            print(k,"=>", v)
        # Disable the lut to allow it to be updated
        self.emc_fan.lut_enabled = False

        # get and sort the new lut keys so that we can assign them in order
        lut_keys = list(self.lut_values.keys())
        lut_keys.sort()
        #print("sorted:", lut_keys)
        for idx in range(lut_size):
            current_temp = lut_keys[idx]
            current_speed = _speed_to_lsb(self.lut_values[current_temp])
            self.emc_fan._lut_temp_setters[idx].__set__(self.emc_fan, current_temp)
            self.emc_fan._lut_speed_setters[idx].__set__(self.emc_fan, current_speed)

        # Set the remaining LUT entries to the default (Temp/Speed = max value)
        for idx in range(8)[lut_size:]:
            #print("updating lut setters:", idx)
            self.emc_fan._lut_temp_setters[idx].__set__(self.emc_fan, MAX_LUT_TEMP)
            self.emc_fan._lut_speed_setters[idx].__set__(self.emc_fan, MAX_LUT_SPEED)
        self.emc_fan.lut_enabled = current_mode

# TODO:
# lut hysteresis
# data rate
# _CONV_RATE = const(0x04)
# _CONV_RATE = const(0x0A)
# DAC output
# pwm polarity
# temp filter
# high low alerts
# min fan speed setter (max TACH counts)
# _TACH_LIMIT_LSB = const(0x48)
# _TACH_LIMIT_MSB = const(0x49)
# spinup config
# diode tuning
#
class EMC2101:  # pylint: disable=too-many-instance-attributes
    """Driver for the EMC2101 Fan Controller.
        :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.
    """

    _part_id = ROUnaryStruct(_REG_PARTID, "<B")
    _mfg_id = ROUnaryStruct(_REG_MFGID, "<B")
    _int_temp = ROUnaryStruct(_INTERNAL_TEMP, "<b")

    # IMPORTANT! the sign bit for the external temp is in the msbyte so mark it as signed
    # and lsb as unsigned
    _ext_temp_msb = ROUnaryStruct(_EXTERNAL_TEMP_MSB, "<b")
    _ext_temp_lsb = ROUnaryStruct(_EXTERNAL_TEMP_LSB, "<B")
    # _tach_read = ROUnaryStruct(_TACH_LSB, "<H")
    _tach_read_lsb = ROUnaryStruct(_TACH_LSB, "<B")
    _tach_read_msb = ROUnaryStruct(_TACH_MSB, "<B")
    _tach_mode_enable = RWBit(_REG_CONFIG, 2)
    _tach_limit_lsb = UnaryStruct(_TACH_LIMIT_LSB, "<B")
    _tach_limit_msb = UnaryStruct(_TACH_LIMIT_MSB, "<B")
    # temp used to override current external temp measurement
    _forced_ext_temp = UnaryStruct(_TEMP_FORCE, "<b")
    _enabled_forced_temp = RWBit(_FAN_CONFIG, 6)

    # speed to use when LUT is disabled in programming mode, default speed
    # uses 6 lsbits
    _fan_setting = UnaryStruct(_REG_FAN_SETTING, "<B")
    _fan_lut_prog = RWBit(_FAN_CONFIG, 5)
    _fan_polarity = RWBit(_FAN_CONFIG, 4)
    # _fan_pwm_clock_slow = RWBit(_FAN_CONFIG, 3)
    _fan_pwm_clock_override = RWBit(_FAN_CONFIG, 2)
    _fan_tach_mode = RWBits(2, _FAN_CONFIG, 0)

    # status register: reading clears so read together
    _status_byte= ROUnaryStruct(_STATUS, "<B")

    #config register
    _mask = RWBit(_REG_CONFIG, 7)
    _standby = RWBit(_REG_CONFIG, 6)
    _fan_standby = RWBit(_REG_CONFIG, 5)
    _dac = RWBit(_REG_CONFIG, 4)
    _dis_to = RWBit(_REG_CONFIG, 3)
    _alt_tch = RWBit(_REG_CONFIG, 2)
    _tcrit_ovrd = RWBit(_REG_CONFIG, 1)
    _queue = RWBit(_REG_CONFIG, 0)

    _temp_filter_cnf = RWBits(2, _TEMP_FILTER, 1)


    #fan spin-up
    _spin_drive = RWBits(2, _FAN_SPINUP, 3)
    _spin_time = RWBits(3, _FAN_SPINUP, 0)
    _spin_tach_limit = RWBit(3, _FAN_SPINUP, 5)

    # seems like a pain but ¯\_(ツ)_/¯
    _fan_lut_t1 = UnaryStruct(0x50, "<B")
    _fan_lut_s1 = UnaryStruct(0x51, "<B")

    _fan_lut_t2 = UnaryStruct(0x52, "<B")
    _fan_lut_s2 = UnaryStruct(0x53, "<B")

    _fan_lut_t3 = UnaryStruct(0x54, "<B")
    _fan_lut_s3 = UnaryStruct(0x55, "<B")

    _fan_lut_t4 = UnaryStruct(0x56, "<B")
    _fan_lut_s4 = UnaryStruct(0x57, "<B")

    _fan_lut_t5 = UnaryStruct(0x58, "<B")
    _fan_lut_s5 = UnaryStruct(0x59, "<B")

    _fan_lut_t6 = UnaryStruct(0x5A, "<B")
    _fan_lut_s6 = UnaryStruct(0x5B, "<B")

    _fan_lut_t7 = UnaryStruct(0x5C, "<B")
    _fan_lut_s7 = UnaryStruct(0x5D, "<B")

    _fan_lut_t8 = UnaryStruct(0x5E, "<B")
    _fan_lut_s8 = UnaryStruct(0x5F, "<B")

    _lut_temp_hyst = UnaryStruct(_LUT_HYSTERESIS, "<B")

    _lut_speed_setters = [_fan_lut_s1, _fan_lut_s2, _fan_lut_s3, _fan_lut_s4,
        _fan_lut_s5, _fan_lut_s6, _fan_lut_s7, _fan_lut_s8]
    _lut_temp_setters = [_fan_lut_t1, _fan_lut_t2, _fan_lut_t3, _fan_lut_t4,
        _fan_lut_t5, _fan_lut_t6, _fan_lut_t7, _fan_lut_t8]


    def __init__(self, i2c_bus):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, _I2C_ADDR)

        if not self._part_id in [0x16, 0x28] or self._mfg_id is not 0x5D:
            raise AttributeError("Cannot find a EMC2101")
        # self._lut = {}

        self.initialize()
        self._lut = FanSpeedLUT(self)

    def initialize(self):
        """Reset the controller to an initial default configuration"""
        # self._lut_temp_hyst = 0
        self._tach_mode_enable = True
        self.lut_enabled = False
        self._enabled_forced_temp = False
        self._fan_pwm_clock_override = True
        self._queue = True
        self._temp_filter_cnf = 3

    @property
    def internal_temperature(self):
        """The temperature as measured by the EMC2101's internal 8-bit temperature sensor"""
        return self._int_temp  # !!! it's RAAAAAAAAARW)


    @property
    def external_temperature(self):
        """The temperature measured using the external diode"""


        temp_lsb = self._ext_temp_lsb
        temp_msb = self._ext_temp_msb
        full_tmp = (temp_msb << 8) | temp_lsb
        print(_b16(full_tmp))
        full_tmp >>= 5
        full_tmp *= 0.125

        return full_tmp  # !!! it's RAAAAAAAAARW

    @property
    def fan_speed(self):
        """The current speed in Revolutions per Minute (RPM)"""

        val = self._tach_read_lsb
        val |= self._tach_read_msb << 8
        return _FAN_RPM_DIVISOR / val

    @property
    def status(self):
        status_dat = self._status_byte
        fault_stat = (status_dat & 0b000000100)>0
        if fault_stat:
            print("Fault!", fault_stat, "reading ext msb (0x01):")
            ext_high = self._ext_temp_msb
            print("ext_mdb:", _b(ext_high))
            print("reading lsb(0x10)")
            ext_low = self._ext_temp_lsb
            print("ext_lsb:", _b(ext_low))
            print("full ext data:", _b16(((ext_high<<8)|ext_low)))
        # names = ["tach", "tcrit", "fault", "ext_low", "ext_high", "eeprom", "int_high", "busy"]
        # for i in range(8):
        #     if (status_dat & 1<<i) >0:
        #         print(names[i], " hit!")


    @property
    def config(self):

        print("_mask:", self._mask)
        print("_standby:", self._standby)
        print("_fan_standby:", self._fan_standby)
        print("_dac:", self._dac)
        print("_dis_to:", self._dis_to)
        print("_alt_tch:", self._alt_tch)
        print("_tcrit_ovrd:", self._tcrit_ovrd)
        print("_queue:", self._queue)

    @property
    def manual_fan_speed(self):
        """The fan speed used while the LUT is being updated and is unavailable. The speed is given as the fan's PWM duty cycle represented as a float percentage.
        The value roughly approximates the percentage of the fan's maximum speed"""
        raw_setting = self._fan_setting & MAX_LUT_SPEED
        return (raw_setting / MAX_LUT_SPEED) * 100

    @manual_fan_speed.setter
    def manual_fan_speed(self, fan_speed):
        if fan_speed not in range(0, 101):
            raise AttributeError("manual_fan_speed must be from 0-100 ")

        # convert from a percentage to an lsb value
        percentage = fan_speed / 100.0
        fan_speed_lsb = round(percentage * MAX_LUT_SPEED)
        lut_disabled = self._fan_lut_prog
        self._fan_lut_prog = True
        self._fan_setting = fan_speed_lsb
        self._fan_lut_prog = lut_disabled

    @property
    def lut_enabled(self):
        """Enable or disable the internal look up table used to map a given temperature
      to a fan speed. When the LUT is disabled, fan speed can be changed with `manual_fan_speed`"""
        return self._fan_lut_prog == False

    @lut_enabled.setter
    def lut_enabled(self, enable_lut):
        self._fan_lut_prog = not enable_lut

    def get_lut(self, lut_index):
        """The Look Up Table used to determine what the fan speed should be based on the measured
        temperature. `lut` acts similarly to a dictionary but with restrictions:

        * The LUT key is a temperature in celcius
        * The LUT value is the corresponding fan speed in % of maximum RPM
        * The LUT can only contain 8 entries. Attempting to set a ninth will
            result in an `IndexError`

        Example:

        .. code-block:: python3

        # If the measured external temperature goes over 20 degrees C, set the fan speed to 50%
        fan_controller.lut[20] = 50

        # If the temperature is over 30 degrees, set the fan speed to 75%
        fan_controller.lut[30] = 75
        """
        return self._lut.__getitem__(self, lut_index)

    def set_lut(self, lut_temp, lut_speed):
        print("NEW LUT:", lut_temp, "=>", lut_speed)
        self._lut.__setitem__(lut_temp, lut_speed)

    @property
    def lut(self):
        """The dict-like representation of the LUT"""
        return self._lut

    @property
    def tach_limit(self):
        """The maximum /minimum speed expected for the fan"""

        low = self._tach_limit_lsb
        high = self._tach_limit_msb

        return (high<<8)|low

    @tach_limit.setter
    def tach_limit(self, new_limit):
        self._tach_limit_lsb = new_limit &0xFF
        self._tach_limit_msb = ((new_limit>>8) & 0xFF)
