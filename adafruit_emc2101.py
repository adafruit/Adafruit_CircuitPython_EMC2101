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
_TACH_LSB = const(0x46)
_TACH_MSB = const(0x47)
_REG_FAN_SETTING =const(0x4C)
foo = """
  # 00h	R	Internal Temperature	"Stores the Internal Temperature"	00h	Page 33																				
  # 02h	R	Status	"Reports internal, external, and TCRIT alarms"	00h	Page 33																				
  # 03h and 09h	R/W	Configuration	"Alert Mask, STANDBY, TCRIT override, Alert Fault
  # Queue"	00h	Page 34																				
  # 04h and 0Ah	R/W	Conversion Rate	Sets conversion rate	"08h (16 / sec)"	Page 35																				


  # 4Ah	R/W	FAN Configuration	"defines polarity of PWM or DAC"	20h	Page 41																				
  # 46h	R	TACH Reading Low Byte	"Stores the lower 6 bits of the TACH count. and theTACH configuration bits"	FFh	Page 40																				
  # 47h	R	TACH Reading High Byte	"Stores the upper 8 bits of
  # the TACH count."	FFh	Page 40																				
  # 48h	R/W	TACH Limit Low Byte	"Stores the lower 6 bits ofthe TACH Limit"	FFh	Page 40																				
  # 49h	R/W	TACH Limit High Byte	"Stores the upper 8 bits ofthe TACH Limit"	FFh	Page 40																				

  # 19h	R/W	TCRIT Temp Limit	"Fan will be set to full speedif external temp above this
  # value"	"55h
  # (85°C)"	Page 36																				
  # 21h	R/W	TCRIT Hysteresis	"Amount of hysteresisapplied to TCRIT Temp
  # (1LSB = 1°C)"	"0Ah
  # (10°C)"	Page 36																				


  # 4Ah	R/W	FAN Configuration	"defines polarity of PWM or
  # DAC"	20h	Page 41																				
  # 4Bh	R/W	Fan Spin-up	Sets Spin Up options	3Fh	Page 42																				
  # 4Ch	R/W	Fan Setting	Sets PWM or DAC value	00h	Page 43																				
  # 4Dh	R/W	PWM Frequency	"Sets the final PWM
  # Frequency"	17h	Page 44																				
  # 4Eh	R/W	PWM Frequency Divide	"Sets the base PWM
  # frequency"	01h	Page 44																				

  # ##### LUT
  # 50h	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 1	"Look Up Table
  # Temperature Setting 1"	7Fh	Page 46																				
  # 51h	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 1	"Associated Fan Setting for
  # Temp Setting 1"	3Fh	Page 46																				
  # 52h	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 2	"Look Up Table
  # Temperature Setting 2"	7Fh	Page 46																				
  # 53h	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 2	"Associated Fan Setting for
  # Temp Setting 2"	3Fh	Page 46																				
  # 54h	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 3	"Look Up Table
  # Temperature Setting 3"	7Fh	Page 46																				
  # 55h	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 3	"Associated Fan Setting for
  # Temp Setting 3"	3Fh	Page 46																				
  # 56h	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 4	"Look Up Table
  # Temperature Setting 4"	7Fh	Page 46																				
  # 57h	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 4	"Associated Fan Setting for
  # Temp Setting 4"	3Fh	Page 46																				
  # 58h	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 5	"Look Up Table
  # Temperature Setting 5"	7Fh	Page 46																				
  # 59h	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 5	"Associated Fan Setting for
  # Temp Setting 5"	3Fh	Page 46																				
  # 5Ah	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 6	"Look Up Table
  # Temperature Setting 6"	7Fh	Page 46																				
  # 5Bh	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 6	"Associated Fan Setting for
  # Temp Setting 6"	3Fh	Page 46																				
  # 5Ch	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 7	"Look Up Table
  # Temperature Setting 7"	7Fh	Page 46																				
  # 5Dh	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 7	"Associated Fan Setting for
  # Temp Setting 7"	3Fh	Page 46																				
  # 5Eh	"R/W (See
  # Note 6.1)"	Lookup Table Temp Setting 8	"Look Up Table
  # Temperature Setting 8"	7Fh	Page 46																				
  # 5Fh	"R/W (See
  # Note 6.1)"	Lookup Table Fan Setting 8	"Associated Fan Setting for
  # Temp Setting 8"	3Fh	Page 46																				
  """
_REG_PARTID = const(0xFD)  # 0x16
_REG_MFGID = const(0xFE)  # 0xFF16
# _REG_CONFIG = const(0x09)
_REG_CONFIG = const(0x03)
# FDh	R	Product ID	ID	16h or 28h	Page 48
# FEh	R	Manufacturer ID	SMSC	5Dh	Page 48
_I2C_ADDR = const(0x4C)
_TEMP_LSB = 0.125
_FAN_RPM_DIVISOR = const(5400000)
_REG_FAN_CONFIG=const(0x4A)
_TEMP_FORCE = const(0x0C)

def _h(val):
    return "0x{:02X}".format(val)


class EMC2101:  # pylint: disable=too-many-instance-attributes
    """Driver for the EMC2101 Fan Controller.
        :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.
    """

    _part_id = ROUnaryStruct(_REG_PARTID, "<B")
    _mfg_id = ROUnaryStruct(_REG_MFGID, "<B")
    _int_temp = ROUnaryStruct(_INTERNAL_TEMP, "<b")
    _ext_temp_msb = ROUnaryStruct(_INTERNAL_TEMP, "<b")
    _ext_temp_lsb = ROUnaryStruct(_INTERNAL_TEMP, "<b")
    #_tach_read = ROUnaryStruct(_TACH_LSB, "<H")
    _tach_read_lsb = ROUnaryStruct(_TACH_LSB, "<B")
    _tach_read_msb = ROUnaryStruct(_TACH_MSB, "<B")
    _tach_mode_enable = RWBit(_REG_CONFIG, 2)

    # temp used to override current external temp measurement
    _ext_tmp_force = UnaryStruct(_TEMP_FORCE, "<b")
    _fan_ext_force_lut_en = RWBit(_REG_FAN_CONFIG, 5)

    # speed to use when LUT is disabled in programming mode, default speed
    # uses 6 lsbits
    _fan_setting = UnaryStruct(_REG_FAN_SETTING, "<B")
    _fan_lut_prog = RWBit(_REG_FAN_CONFIG, 5)
    _fan_polarity = RWBit(_REG_FAN_CONFIG, 4)
    _fan_pwm_clock_slow = RWBit(_REG_FAN_CONFIG, 3)
    _fan_pwm_clock_override = RWBit(_REG_FAN_CONFIG, 2)
    _fan_tach_mode = RWBits(2, _REG_FAN_CONFIG, 0)

    _fan_lut_t1 = UnaryStruct(0x50, "<B")
    _fan_lut_s1 = UnaryStruct(0x51, "<B")

    _fan_lut_t2 = UnaryStruct(0x52, "<B")
    _fan_lut_s2 = UnaryStruct(0x53, "<B")
    def __init__(self, i2c_bus):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, _I2C_ADDR)

        if not self._part_id in [0x16, 0x28] or self._mfg_id is not 0x5D:
            raise AttributeError("Cannot find a EMC2101")
        self.initialize()

    def initialize(self):
        """Reset the controller to an initial default configuration"""
        print("initializing!")
        self._tach_mode_enable = True
        # set lowest temp to temp on boot
        self._fan_lut_prog = True
        self._fan_lut_t1 = 30
        self._fan_lut_s1 = 5

        self._fan_lut_t2 = 40
        self._fan_lut_s2 = 50
        self._fan_lut_prog = False
        

    @property
    def internal_temperature(self):
        """The temperature as measured by the EMC2101's internal temperature sensor"""
        return self._int_temp  # !!! it's RAAAAAAAAARW)

    @property
    def external_temperature(self):
        """The temperature measured using the external diode"""
        temp_msb = self._ext_temp_msb
        temp_lsb = self._ext_temp_lsb
        full_tmp = (temp_msb << 8) | temp_lsb
        full_tmp >>= 5
        full_tmp *= 0.125

        return full_tmp  # !!! it's RAAAAAAAAARW
    @property
    def fan_speed(self):
      """The current speed in Revolutions per Minute (RPM)"""


      val = self._tach_read_lsb
      val |= (self._tach_read_msb<<8)
      return _FAN_RPM_DIVISOR / val
    @property
    def fan_fallback_speed(self):
      """The fan speed used while the LUT is being updated and is unavailable"""
      return self._fan_setting

    @fan_fallback_speed.setter
    def fan_fallback_speed(self, fan_speed):
      self._fan_setting = (fan_speed & 0b111111)


if __name__ == "__main__":
    import board
    import time
    from adafruit_debug_i2c import DebugI2C

    i2c = board.I2C()
    #i2c = DebugI2C(i2c)
    emc = EMC2101(i2c)
    emc.fan_fallback_speed = 10
    while True:
        print("Internal temp:", emc.internal_temperature)
        print("External temp", emc.external_temperature)
        print("Fan speed", emc.fan_speed)
        print("Fan fallback speed:", emc.fan_fallback_speed)

        print("")
        time.sleep(0.5)
