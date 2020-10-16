# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import busio
import time
from struct import unpack_from
from timer import Timer
from adafruit_emc2101 import EMC2101, SpinupDrive, SpinupTime, ConversionRate
from adafruit_debug_i2c import DebugI2C

i2c = busio.I2C(board.SCL, board.SDA)
# i2c = DebugI2C(i2c)

emc = EMC2101(i2c)
# print("Setting fan speed to 75%")
# print("Setting tach limit")
emc.tach_limit = 300
emc.manual_fan_speed = 0
# print("**** Spinup time ****")
emc.spinup_time = SpinupTime.SPIN_3_2_SEC
# print("**** Spinup DRIVE ****")
emc.spinup_drive = SpinupDrive.DRIVE_100
emc.manual_fan_speed = 100
emc.lut_enabled = True
emc.lut[10] = 25
emc.lut[35] = 100
emc.conversion_rate = ConversionRate.RATE_1_16
while True:
    print((emc.external_temperature, emc.internal_temperature))
    # print("Internal temp:", emc.internal_temperature, end="")
    # print("  External temp:", emc.external_temperature, "Fan RPM:", emc.fan_speed, "Tach limit:", emc.tach_limit, "RPM")
    time.sleep(.001)

