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
from adafruit_register.i2c_struct import ROUnaryStruct
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits, ROBits
import adafruit_bus_device.i2c_device as i2cdevice

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EMC2101.git"
_INRNL_TEMP = const(0x00)
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

_EMC2101_REG_PARTID = const(0xFD) # 0x16
_EMC2101_REG_MFGID = const(0xFE) # 0xFF16
# FDh	R	Product ID	ID	16h or 28h	Page 48																				
# FEh	R	Manufacturer ID	SMSC	5Dh	Page 48																				
_EMC2101_I2C_ADDR = const(0x4C)
class EMC2101:  # pylint: disable=too-many-instance-attributes
    """Driver for the EMC2101 Fan Controller.
        :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.
    """

    _part_id = ROUnaryStruct(_EMC2101_REG_PARTID, "<B")
    _mfg_id = ROUnaryStruct(_EMC2101_REG_MFGID, "<B")

    def __init__(self, i2c_bus):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, _EMC2101_I2C_ADDR)

        if not self._part_id in [0x16, 0x28] or self._mfg_id is not 0x5D:
          raise AttributeError("Cannot find a EMC2101")

    def initialize(self):
      """Reset the controller to an initial default configuration"""
      print("initializing!")


if __name__=='__main__':
  import board
  import time
  i2c = board.I2C()
  emc = EMC2101(i2c)
  print("Done with init!")