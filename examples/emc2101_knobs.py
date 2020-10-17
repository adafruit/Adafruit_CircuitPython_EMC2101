# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint:disable=no-member
import time
import board
import busio
from adafruit_emc2101 import EMC2101, SpinupDrive, SpinupTime, ConversionRate

i2c = busio.I2C(board.SCL, board.SDA)

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
    time.sleep(0.001)
