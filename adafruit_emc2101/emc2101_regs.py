# SPDX-FileCopyrightText: Copyright (c) 2022 Ruth Ivimey-Cook for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_emc2101.emc2101_regs`
================================================================================

Brushless fan controller EMC2101 Register addresses.

Register offset definitions for the SMC EMC2101 fan controller.

* Author(s): Bryan Siepert, Ruth Ivimey-Cook

Implementation Notes
--------------------

**Hardware:**

* `Adafruit EMC2101 Breakout
  <https://adafruit.com/product/4808>`_ (Product ID: 4808)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

* Adafruit's Register library:
  https://github.com/adafruit/Adafruit_CircuitPython_Register

"""

from micropython import const

MFG_ID_SMSC = 0x5D
PART_ID_EMC2101 = 0x16
PART_ID_EMC2101R = 0x28

I2C_ADDR = const(0x4C)

MAX_LUT_SPEED = 0x3F  # 6-bit value
MAX_LUT_TEMP = 0x7F  # 7-bit

# Values of external temp register for fault conditions.
TEMP_FAULT_OPENCIRCUIT = 0x3F8
TEMP_FAULT_SHORT = 0x3FF

# See datasheet section 6.14:
FAN_RPM_DIVISOR = const(5400000)

#
# EMC2101 Register Addresses
#
INTERNAL_TEMP = const(0x00)  # Readonly
EXTERNAL_TEMP_MSB = const(0x01)  # Readonly, Read MSB first
EXTERNAL_TEMP_LSB = const(0x10)  # Readonly
REG_STATUS = const(0x02)  # Readonly
REG_CONFIG = const(0x03)  # Also at 0x09
CONVERT_RATE = const(0x04)  # Also at 0x0A
INT_TEMP_HI_LIM = const(0x05)  # Also at 0x0B
TEMP_FORCE = const(0x0C)
ONESHOT = const(0x0F)  # Effectively Writeonly
SCRATCH_1 = const(0x11)
SCRATCH_2 = const(0x12)
EXT_TEMP_LO_LIM_LSB = const(0x14)
EXT_TEMP_LO_LIM_MSB = const(0x08)  # Also at 0x0E
EXT_TEMP_HI_LIM_LSB = const(0x13)
EXT_TEMP_HI_LIM_MSB = const(0x07)  # Also at 0x0D
ALERT_MASK = const(0x16)
EXT_IDEALITY = const(0x17)
EXT_BETACOMP = const(0x18)
TCRIT_TEMP = const(0x19)
TCRIT_HYST = const(0x21)
TACH_LSB = const(0x46)  # Readonly, Read MSB first
TACH_MSB = const(0x47)  # Readonly
TACH_LIMIT_LSB = const(0x48)
TACH_LIMIT_MSB = const(0x49)
FAN_CONFIG = const(0x4A)
FAN_SPINUP = const(0x4B)
REG_FAN_SETTING = const(0x4C)
PWM_FREQ = const(0x4D)
PWM_FREQ_DIV = const(0x4E)
FAN_TEMP_HYST = const(0x4F)
AVG_FILTER = const(0xBF)

REG_PARTID = const(0xFD)  # Readonly, 0x16 (or 0x28 for -R part)
REG_MFGID = const(0xFE)  # Readonly, SMSC is 0x5D
REG_REV = const(0xFF)  # Readonly, e.g. 0x01

LUT_HYSTERESIS = const(0x4F)
LUT_BASE = const(0x50)
