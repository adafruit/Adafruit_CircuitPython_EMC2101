# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_emc2101.emc2101_lut`
================================================================================

Brushless fan controller: extended functionality


* Author(s): Bryan Siepert, Ryan Pavlik

Implementation Notes
--------------------

**Hardware:**

* `Adafruit EMC2101 Breakout <https://adafruit.com/product/4808>`_ (Product ID: 4808)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

* Adafruit's Register library:
  https://github.com/adafruit/Adafruit_CircuitPython_Register


The class defined here may be used instead of :class:`adafruit_emc2101.EMC2101`,
if your device has enough RAM to support it. This class adds LUT control
and PWM frequency control to the base feature set.
"""

from adafruit_register.i2c_struct_array import StructArray
from adafruit_register.i2c_struct import UnaryStruct
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_emc2101 import emc2101_regs
from adafruit_emc2101 import EMC2101

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EMC2101.git"


class FanSpeedLUT:
    """A class used to provide a dict-like interface to the EMC2101's Temperature
    to Fan speed Look Up Table (LUT).

    Keys are integer temperatures, values are fan duty cycles between 0 and 100.
    A max of 8 values may be stored.

    To remove a single stored point in the LUT, assign it as `None`.
    """

    # 8 (Temperature, Speed) pairs in increasing order
    _fan_lut = StructArray(emc2101_regs.LUT_BASE, "<B", 16)
    _defer_update = 0

    def __init__(self, fan_obj):
        self._defer_update = 0
        self.emc_fan = fan_obj
        self.lut_values = {}
        self.i2c_device = fan_obj.i2c_device

    def __enter__(self):
        """ 'with' wrapper: defer lut update until end of 'with'
        so update_lut work can be done just once at the end of
        setting the LUT.

        Usage:
        ```
            with emc2101.lut as lut:
                lut[20] = 0
                lut[40] = 10
        ```
        """
        # Use increment/decrement so nested with's are dealt with properly.
        self._defer_update += 1
        return self

    # 'with' wrapper
    def __exit__(self, typ, val, tbk):
        """ 'with' wrapper: defer lut update until end of 'with'
        so update_lut work can be done just once at the end of
        setting the LUT.
        """
        self._defer_update -= 1
        if self._defer_update <= 0:
            self._defer_update = 0
            self._update_lut()

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise IndexError
        if not index in self.lut_values:
            raise IndexError
        return self.lut_values[index]

    def __setitem__(self, index, value):
        if not isinstance(index, int):
            raise IndexError
        if value is None:
            # Assign None to remove this entry
            del self.lut_values[index]
        elif value > 100.0 or value < 0:
            # Range check
            raise AttributeError("LUT values must be a fan speed from 0-100%")
        else:
            self.lut_values[index] = value
        if self._defer_update == 0:
            self._update_lut()

    def __repr__(self):
        """return the official string representation of the LUT"""
        # pylint: disable=consider-using-f-string
        return "FanSpeedLUT <%x>" % id(self)

    def __str__(self):
        """return the official string representation of the LUT"""
        value_strs = []
        lut_keys = tuple(sorted(self.lut_values.keys()))
        for temp in lut_keys:
            fan_drive = self.lut_values[temp]
            # pylint: disable=consider-using-f-string
            value_strs.append("%d deg C => %.1f%% duty cycle" % (temp, fan_drive))

        return "\n".join(value_strs)

    @property
    def lookup_table(self):
        """Return a dictionary of LUT values."""
        lut_keys = tuple(sorted(self.lut_values.keys()))
        values = {}
        for temp in lut_keys:
            fan_drive = self.lut_values[temp]
            values[temp] = fan_drive
        return values

    def __len__(self):
        return len(self.lut_values)

    # this function does a whole lot of work to organized the user-supplied lut dict into
    # their correct spot within the lut table as pairs of set registers, sorted with the lowest
    # temperature first

    def _update_lut(self):
        # Make sure we're not going to try to set more entries than we have slots
        if len(self.lut_values) > 8:
            raise AttributeError("LUT can only contain a maximum of 8 items")

        # Backup state
        current_mode = self.emc_fan.lut_enabled

        # Disable the lut to allow it to be updated
        self.emc_fan.lut_enabled = False

        # we want to assign the lowest temperature to the lowest LUT slot, so we sort the keys/temps
        # get and sort the new lut keys so that we can assign them in order
        for idx, current_temp in enumerate(sorted(self.lut_values.keys())):
            # We don't want to make `_speed_to_lsb()` public, it is only needed here.
            # pylint: disable=protected-access
            current_speed = self.emc_fan._speed_to_lsb(self.lut_values[current_temp])
            self._set_lut_entry(idx, current_temp, current_speed)

        # Set the remaining LUT entries to the default (Temp/Speed = max value)
        for idx in range(len(self.lut_values), 8):
            self._set_lut_entry(
                idx, emc2101_regs.MAX_LUT_TEMP, emc2101_regs.MAX_LUT_SPEED
            )
        self.emc_fan.lut_enabled = current_mode

    def _set_lut_entry(self, idx, temp, speed):
        """Internal function: add a value to the local LUT as a byte array,
        suitable for block transfer to the EMC I2C interface.
        """
        self._fan_lut[idx * 2] = bytearray((temp,))
        self._fan_lut[idx * 2 + 1] = bytearray((speed,))


class EMC2101_EXT(EMC2101):  # pylint: disable=too-many-instance-attributes
    """Driver for EMC2101 Fan, adding definitions for all (but LUT) device registers.

    See :class:`adafruit_emc2101.EMC2101` for the base/common functionality.
    See :class:`adafruit_emc2101.EMC2101_LUT` for the temperature look up table functionality.

    :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.
    """

    _int_temp_limit = UnaryStruct(emc2101_regs.INT_TEMP_HI_LIM, "<B")
    """Device internal temperature limit. If temperature is higher than this
    the ALERT actions are taken."""
    _tcrit_limit = UnaryStruct(emc2101_regs.TCRIT_TEMP, "<B")
    """Device internal critical temperature. Device part spec is 0C to 85C."""
    _tcrit_hyst = UnaryStruct(emc2101_regs.TCRIT_HYST, "<B")
    """Device internal critical temperature hysteresis, default 1C"""

    # Limits, Integer Temperature in degrees:
    _ext_temp_lo_limit_msb = RWBits(6, emc2101_regs.EXT_TEMP_LO_LIM_MSB, 0)
    """External temperature low-limit (integer part). If read temperature is
    lower than this, the ALERT actions are taken."""
    _ext_temp_hi_limit_msb = RWBits(6, emc2101_regs.EXT_TEMP_HI_LIM_MSB, 0)
    """External temperature high-limit (integer part). If read temperature is
    higher than this, the ALERT actions are taken."""

    # Limits, Fractions of degree (b7:0.5, b6:0.25, b5:0.125)
    _ext_temp_lo_limit_lsb = RWBits(3, emc2101_regs.EXT_TEMP_LO_LIM_LSB, 5)
    """External temperature low-limit (3-bit fractional part). If read
    temperature is lower than this, the ALERT actions are taken."""
    _ext_temp_hi_limit_lsb = RWBits(3, emc2101_regs.EXT_TEMP_HI_LIM_LSB, 5)
    """External temperature high-limit (3-bit fractional part). If read
    temperature is higher than this, the ALERT actions are taken."""

    _ext_ideality = RWBits(5, emc2101_regs.EXT_IDEALITY, 0)
    """Factor setting the ideality factor applied to the external diode,
    based around a standard factor of 1.008. See table in datasheet for
    details"""
    _ext_betacomp = RWBits(5, emc2101_regs.EXT_BETACOMP, 0)
    """Beta compensation setting. When using diode-connected transistor,
    disable with value of 0x7. Otherwise, bit 3 enables autodetection."""

    _fan_clk_sel = RWBit(emc2101_regs.FAN_CONFIG, 3)
    """Select base clock used to determine pwm frequency, default 0 is 360KHz,
    and 1 is 1.4KHz."""
    _fan_clk_ovr = RWBit(emc2101_regs.FAN_CONFIG, 2)
    """Enable override of clk_sel to use pwm_freq_div register to determine
    the pwm frequency."""

    _avg_filter = RWBits(2, emc2101_regs.AVG_FILTER, 1)
    """Set the filtering options. """
    _alert_comp = RWBit(emc2101_regs.AVG_FILTER, 0)
    """Set alert options. """

    def __init__(self, i2c_bus):
        super().__init__(i2c_bus)
        self.initialize()

    def initialize(self):
        """Reset the controller to an initial default configuration"""
        self.extended_api = True
        super().initialize()

    @property
    def dev_temp_critical_limit(self):
        """The critical temperature limit for the device (measured by internal
        sensor), in degrees."""
        return self._tcrit_limit

    @property
    def dev_temp_critical_hysteresis(self):
        """The critical temperature hysteresis for the device (measured by
        internal sensor), in degrees."""
        return self._tcrit_hyst

    @dev_temp_critical_hysteresis.setter
    def dev_temp_critical_hysteresis(self, hysteresis):
        """The critical temperature hysteresis for the device (measured by
        internal sensor), in degrees (1..10)."""
        if hysteresis not in range(1, 10):
            raise AttributeError("dev_temp_critical_hysteresis must be from 1..10")
        self._tcrit_hyst = hysteresis

    @property
    def dev_temp_high_limit(self):
        """The high limit temperature for the internal sensor, in degrees."""
        return self._int_temp_limit

    @dev_temp_high_limit.setter
    def dev_temp_high_limit(self, temp):
        """The high limit temperature for the internal sensor, in
        degrees (0..85)."""
        # Device specced from 0C to 85C
        if temp not in range(0, 85):
            raise AttributeError("dev_temp_high_limit must be from 0..85")
        self._int_temp_limit = temp

    @property
    def external_temp_low_limit(self):
        """The low limit temperature for the external sensor."""
        # No ordering restrictions here.
        temp_lsb = self._ext_temp_lo_limit_lsb
        temp_msb = self._ext_temp_lo_limit_msb
        temp = (temp_msb << 8) | (temp_lsb & 0xE0)
        temp >>= 5
        temp *= 0.125
        return temp

    @external_temp_low_limit.setter
    def external_temp_low_limit(self, temp: float):
        """Set low limit temperature for the external sensor."""
        if temp not in range(-40, 100):
            raise AttributeError("dev_temp_high_limit must be from -40..100")
        # Multiply by 8 to get 3 bits of fraction within the integer.
        temp *= 8.0
        temp = int(temp)
        # Mask 3 bits & shift to bits 5,6,7 in byte
        temp_lsb = temp & 0x07
        temp_lsb = temp_lsb << 5
        # Now drop 3 fraction bits.
        temp_msb = temp >> 3

        # No ordering restrictions here.
        self._ext_temp_lo_limit_lsb = temp_lsb
        self._ext_temp_lo_limit_msb = temp_msb

    @property
    def external_temp_high_limit(self):
        """The high limit temperature for the external sensor."""
        # No ordering restrictions here.
        temp_lsb = self._ext_temp_hi_limit_lsb
        temp_msb = self._ext_temp_hi_limit_msb
        # Mask bottom bits of lsb, or with shifted msb
        full_tmp = (temp_msb << 8) | (temp_lsb & 0xE0)
        full_tmp >>= 5
        full_tmp *= 0.125
        return full_tmp

    @external_temp_high_limit.setter
    def external_temp_high_limit(self, temp: float):
        """Set high limit temperature for the external sensor."""
        # Multiply by 8 to get 3 bits of fraction.
        temp *= 8.0
        temp = int(temp)
        # Mask 3 bits & shift to bits 5,6,7 in byte
        temp_lsb = temp & 0x07
        temp_lsb = temp_lsb << 5
        # Now drop 3 fraction bits.
        temp_msb = temp >> 3
        # No ordering restrictions here.
        self._ext_temp_hi_limit_lsb = temp_lsb
        self._ext_temp_hi_limit_msb = temp_msb


class EMC2101_LUT(EMC2101_EXT):  # pylint: disable=too-many-instance-attributes
    """Driver for the EMC2101 Fan Controller, with PWM frequency and LUT control.

    See :class:`adafruit_emc2101.EMC2101` for the base/common functionality.
    See :class:`adafruit_emc2101.EMC2101_EXT` for (almost) complete device register set but no LUT.

    :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.
    """

    lut_temperature_hysteresis = UnaryStruct(emc2101_regs.LUT_HYSTERESIS, "<B")
    """The amount of hysteresis in Degrees Celsius of hysteresis applied to temperature readings
    used for the LUT. As the temperature drops, the controller will switch to a lower LUT entry when
    the measured value is below the lower entry's threshold, minus the hysteresis value"""

    def __init__(self, i2c_bus):
        super().__init__(i2c_bus)

        self.initialize()
        self._lut = FanSpeedLUT(self)

    def initialize(self):
        """Reset the controller to an initial default configuration"""
        self.lut_enabled = True
        self._fan_clk_ovr = True
        super().initialize()

    def set_pwm_clock(self, use_preset=False, use_slow=False):
        """
             Select the PWM clock source, choosing between two preset clocks or by configuring the
             clock using `pwm_frequency` and `pwm_frequency_divisor`.

        :param bool use_preset:
         True: Select between two preset clock sources
         False: The PWM clock is set by `pwm_frequency` and `pwm_frequency_divisor`
        :param bool use_slow:
             True: Use the 1.4kHz clock
             False: Use the 360kHz clock.
        :type priority: integer or None
        :return: None
        :raises AttributeError: if use_preset is not a `bool`
        :raises AttributeError: if use_slow is not a `bool`

        """

        if not isinstance(use_preset, bool):
            raise AttributeError("use_preset must be given a bool")
        if not isinstance(use_slow, bool):
            raise AttributeError("use_slow_pwm must be given a bool")

        self._fan_clk_ovr = not use_preset
        self._fan_clk_sel = use_slow

    @property
    def pwm_frequency(self):
        """Selects the base clock frequency used for the fan PWM output"""
        return self._pwm_freq

    @pwm_frequency.setter
    def pwm_frequency(self, value):
        if value < 0 or value > 0x1F:
            raise AttributeError("pwm_frequency must be from 0-31")
        self._pwm_freq = value
        self._calculate_full_speed(pwm_f=value)

    @property
    def pwm_frequency_divisor(self):
        """The Divisor applied to the PWM frequency to set the final frequency"""
        return self._pwm_freq_div

    @pwm_frequency_divisor.setter
    def pwm_frequency_divisor(self, divisor):
        if divisor < 0 or divisor > 255:
            raise AttributeError("pwm_frequency_divisor must be from 0-255")
        self._pwm_freq_div = divisor

    @property
    def lut_enabled(self):
        """Enable or disable the internal look up table used to map a given temperature
        to a fan speed. When the LUT is disabled fan speed can be changed with `manual_fan_speed`"""
        return not self._fan_lut_prog

    @lut_enabled.setter
    def lut_enabled(self, enable_lut):
        self._fan_lut_prog = not enable_lut

    @property
    def lut(self):
        """The dict-like representation of the LUT, actually of type :class:`FanSpeedLUT`"""
        return self._lut
