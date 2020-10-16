# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import busio
import time
from adafruit_emc2101 import EMC2101, _lsb_to_speed

i2c = busio.I2C(board.SCL, board.SDA)

FAN_MAX_RPM = 1700
emc = EMC2101(i2c)
emc.manual_fan_speed = 50
time.sleep(1)
emc.lut[27] = 25
emc.lut[34] = 50
emc.lut[42] = 75
emc.lut_enabled = True
emc._enabled_forced_temp = True
print("Lut:", emc.lut)
emc._forced_ext_temp = 28 # over 25, should be 25%
time.sleep(3)
print("25%% duty cycle is %f RPM:"%emc.fan_speed)


emc._forced_ext_temp = 35 # over 30, should be 50%
time.sleep(3)
print("50%% duty cycle is %f RPM:"%emc.fan_speed)

emc._forced_ext_temp = 43 # over 30, should be 50%
time.sleep(3)
print("75%% duty cycle is %f RPM:"%emc.fan_speed)
