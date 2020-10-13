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
emc.set_lut(25, 25)
emc.set_lut(30, 50)
emc.set_lut(45, 75)

for i in range(8):
    print("LUT[%d] =>"%emc._lut_temp_setters[i].__get__(emc),
    "->", _lsb_to_speed(emc._lut_speed_setters[i].__get__(emc)))
emc.lut_enabled = True
emc._enabled_forced_temp = True

emc._forced_ext_temp = 26 # over 25, should be 25%
time.sleep(3)
percent_max = (FAN_MAX_RPM*0.25)
print("25%% max fan speed is %f RPM:"%percent_max, "FAN SPEED:", emc.fan_speed)


emc._forced_ext_temp = 31 # over 30, should be 50%
time.sleep(3)
percent_max = (FAN_MAX_RPM*0.50)
print("50%% max fan speed is %f RPM:"%percent_max, "FAN SPEED:", emc.fan_speed)

emc._forced_ext_temp = 46 # over 30, should be 50%
time.sleep(3)
percent_max = (FAN_MAX_RPM*0.75)
print("75%% max fan speed is %f RPM:"%percent_max, "FAN SPEED:", emc.fan_speed)
