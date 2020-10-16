# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import busio
import time
from struct import unpack_from
from timer import Timer
from adafruit_emc2101 import EMC2101
from adafruit_debug_i2c import DebugI2C

i2c = busio.I2C(board.SCL, board.SDA)
# i2c = DebugI2C(i2c)

emc = EMC2101(i2c)
print("Setting fan speed to 25%")
print("Setting tach limit")
emc.tach_limit = 1024

while True:
    # print("Fan speed", emc.fan_speed)
    print("Internal temp:", emc.internal_temperature)
    print("  External temp:", emc.external_temperature)
    emc.status
    print("tach_limit:", emc.tach_limit)
    print("")
    # emc.config
    time.sleep(.3)

