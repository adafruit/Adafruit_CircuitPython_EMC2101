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
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
import adafruit_bus_device.i2c_device as i2cdevice

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EMC2101.git"

#
# EMC2101 Register Addresses
#
_INTERNAL_TEMP = const(0x00)  # Readonly
_EXTERNAL_TEMP_MSB = const(0x01)  # Readonly, Read MSB first
_EXTERNAL_TEMP_LSB = const(0x10)  # Readonly
_REG_STATUS = const(0x02)  # Readonly
_REG_CONFIG = const(0x03)  # Also at 0x09
_CONVERT_RATE = const(0x04)  # Also at 0x0A
_INT_TEMP_HI_LIM = const(0x05)  # Also at 0x0B
_TEMP_FORCE = const(0x0C)
_ONESHOT = const(0x0F)  # Effectively Writeonly
_SCRATCH_1 = const(0x11)
_SCRATCH_2 = const(0x12)
_EXT_TEMP_LO_LIM_LSB = const(0x14)
_EXT_TEMP_LO_LIM_MSB = const(0x08)  # Also at 0x0E
_EXT_TEMP_HI_LIM_LSB = const(0x13)
_EXT_TEMP_HI_LIM_MSB = const(0x07)  # Also at 0x0D
_ALERT_MASK = const(0x16)
_EXT_IDEALITY = const(0x17)
_EXT_BETACOMP = const(0x18)
_TCRIT_TEMP = const(0x19)
_TCRIT_HYST = const(0x21)
_TACH_LSB = const(0x46)  # Readonly, Read MSB first
_TACH_MSB = const(0x47)  # Readonly
_TACH_LIMIT_LSB = const(0x48)
_TACH_LIMIT_MSB = const(0x49)
_FAN_CONFIG = const(0x4A)
_FAN_SPINUP = const(0x4B)
_REG_FAN_SETTING = const(0x4C)
_PWM_FREQ = const(0x4D)
_PWM_FREQ_DIV = const(0x4E)
_FAN_TEMP_HYST = const(0x4F)
_AVG_FILTER = const(0xBF)
_REG_PARTID = const(0xFD)  # Readonly, 0x16 (or 0x28 for -R part)
_REG_MFGID = const(0xFE)  # Readonly, SMSC is 0x5D
_REG_REV = const(0xFF)  # Readonly, e.g. 0x01

MAX_LUT_SPEED = 0x3F  # 6-bit value
MAX_LUT_TEMP = 0x7F  # 7-bit

MFG_ID_SMSC = 0x5D
PART_ID_EMC2101 = 0x16
PART_ID_EMC2101R = 0x28

_I2C_ADDR = const(0x4C)

# See datasheet section 6.14:
_FAN_RPM_DIVISOR = const(5400000)


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        """creates CV entries"""
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value):
        "Returns true if the given value is a member of the CV"
        return value in cls.string


class ConversionRate(CV):
    """Options for ``conversion_rate``"""


ConversionRate.add_values(
    (
        ("RATE_1_16", 0, str(1 / 16.0), None),
        ("RATE_1_8", 1, str(1 / 8.0), None),
        ("RATE_1_4", 2, str(1 / 4.0), None),
        ("RATE_1_2", 3, str(1 / 2.0), None),
        ("RATE_1", 4, str(1.0), None),
        ("RATE_2", 5, str(2.0), None),
        ("RATE_4", 6, str(4.0), None),
        ("RATE_8", 7, str(8.0), None),
        ("RATE_16", 8, str(16.0), None),
        ("RATE_32", 9, str(32.0), None),
    )
)


class SpinupDrive(CV):
    """Options for ``spinup_drive``"""


SpinupDrive.add_values(
    (
        ("BYPASS", 0, "Disabled", None),
        ("DRIVE_50", 1, "50% Duty Cycle", None),
        ("DRIVE_75", 2, "25% Duty Cycle", None),
        ("DRIVE_100", 3, "100% Duty Cycle", None),
    )
)


class SpinupTime(CV):
    """Options for ``spinup_time``"""


SpinupTime.add_values(
    (
        ("BYPASS", 0, "Disabled", None),
        ("SPIN_0_05_SEC", 1, "0.05 seconds", None),
        ("SPIN_0_1_SEC", 2, "0.1 seconds", None),
        ("SPIN_0_2_SEC", 3, "0.2 seconds", None),
        ("SPIN_0_4_SEC", 4, "0.4 seconds", None),
        ("SPIN_0_8_SEC", 5, "0.8 seconds", None),
        ("SPIN_1_6_SEC", 6, "1.6 seconds", None),
        ("SPIN_3_2_SEC", 7, "3.2 seconds", None),
    )
)


class EMC2101:  # pylint: disable=too-many-instance-attributes
    """Basic driver for the EMC2101 Fan Controller.

    :param ~busio.I2C i2c_bus: The I2C bus the EMC is connected to.


    **Quickstart: Importing and using the device**

        Here is an example of using the :class:`EMC2101` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            from adafruit_emc2101.emc2101_lut import EMC2101_LUT as EMC2101

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()  # uses board.SCL and board.SDA
            emc = EMC2101(i2c)

        Now you have access to the :attr:`manual_fan_speed` attribute to setup the
        desired fanspeed

        .. code-block:: python

            emc.manual_fan_speed = 25


    If you need control over PWM frequency and the controller's built in temperature/speed
    look-up table (LUT), you will need :class:`emc2101_lut.EMC2101_LUT` which extends this
    class to add those features, at the cost of increased memory usage.

    Datasheet: https://ww1.microchip.com/downloads/en/DeviceDoc/2101.pdf
    """

    _part_id = ROUnaryStruct(_REG_PARTID, "<B")
    _mfg_id = ROUnaryStruct(_REG_MFGID, "<B")
    _part_rev = ROUnaryStruct(_REG_REV, "<B")
    _int_temp = ROUnaryStruct(_INTERNAL_TEMP, "<b")

    # Some of these registers are defined as two halves because the chip does
    # not support multi-byte reads or writes, and there is currently no way to
    # tell Struct to do a transaction for each byte.

    # IMPORTANT!
    # The sign bit for the external temp is in the msbyte so mark it as signed
    #     and lsb as unsigned.
    # The Lsbyte is shadow-copied when Msbyte is read, so read Msbyte first to
    #     avoid risk of bad reads. See datasheet section 6.1 Data Read Interlock.
    _ext_temp_msb = ROUnaryStruct(_EXTERNAL_TEMP_MSB, "<b")
    # Fractions of degree (b7:0.5, b6:0.25, b5:0.125)
    _ext_temp_lsb = ROUnaryStruct(_EXTERNAL_TEMP_LSB, "<B")

    # IMPORTANT!
    # The Msbyte is shadow-copied when Lsbyte is read, so read Lsbyte first to
    #     avoid risk of bad reads. See datasheet section 6.1 Data Read Interlock.
    _tach_read_lsb = ROUnaryStruct(_TACH_LSB, "<B")
    _tach_read_msb = ROUnaryStruct(_TACH_MSB, "<B")

    _tach_mode_enable = RWBit(_REG_CONFIG, 2)
    _tach_limit_lsb = UnaryStruct(_TACH_LIMIT_LSB, "<B")
    _tach_limit_msb = UnaryStruct(_TACH_LIMIT_MSB, "<B")

    _int_temp_limit = UnaryStruct(_INT_TEMP_HI_LIM, "<B")
    """Device internal temperature limit. If temperature is higher than this
    the ALERT actions are taken."""
    _tcrit_limit = UnaryStruct(_TCRIT_TEMP, "<B")
    """Device internal critical temperature. Device part spec is 0C to 85C."""
    _tcrit_hyst = UnaryStruct(_TCRIT_HYST, "<B")
    """Device internal critical temperature hysteresis, default 1C"""

    # Temperature in degrees:
    _ext_temp_lo_limit_msb = RWBits(6, _EXT_TEMP_LO_LIM_LSB, 0)
    """External temperature low-limit (integer part). If read temperature is
    lower than this, the ALERT actions are taken."""
    _ext_temp_hi_limit_msb = RWBits(6, _EXT_TEMP_HI_LIM_LSB, 0)
    """External temperature low-limit (3-bit fractional part). If read
    temperature is lower than this, the ALERT actions are taken."""

    # Limits, Fractions of degree (b7:0.5, b6:0.25, b5:0.125)
    _ext_temp_lo_limit_lsb = RWBits(3, _EXT_TEMP_LO_LIM_LSB, 5)
    """External temperature high-limit (integer part). If read temperature is
    higher than this, the ALERT actions are taken."""
    _ext_temp_hi_limit_lsb = RWBits(3, _EXT_TEMP_HI_LIM_LSB, 5)
    """External temperature high-limit (3-bit fractional part). If read
    temperature is higher than this, the ALERT actions are taken."""

    # Temperature used to override current external temp measurement.
    # Force Temp is 7-bit + sign (one's complement?)
    forced_ext_temp = UnaryStruct(_TEMP_FORCE, "<b")
    """The value that the external temperature will be forced to read when
    `forced_temp_enabled` is set. This can be used to test the behavior of
    the LUT without real temperature changes."""
    forced_temp_enabled = RWBit(_FAN_CONFIG, 6)
    """When True, the external temperature measurement will always be read
    as the value in `forced_ext_temp`. Not applicable if LUT disabled."""

    _ext_ideality = RWBits(5, _EXT_IDEALITY, 0)
    """Factor setting the ideality factor applied to the external diode,
    based around a standard factor of 1.008. See table in datasheet for
    details"""
    _ext_betacomp = RWBits(5, _EXT_BETACOMP, 0)
    """Beta compensation setting. When using diode-connected transistor,
    disable with value of 0x7. Otherwise, bit 3 enables autodetection."""

    # PWM/Fan control
    _fan_setting = UnaryStruct(_REG_FAN_SETTING, "<B")
    _pwm_freq = RWBits(5, _PWM_FREQ, 0)
    _pwm_freq_div = UnaryStruct(_PWM_FREQ_DIV, "<B")
    _fan_lut_prog = RWBit(_FAN_CONFIG, 5)
    """Programming-enable (write-enable) bit for the LUT registers."""
    _fan_clk_sel = RWBit(_FAN_CONFIG, 3)
    """Select base clock used to determine pwm frequency, default 0 is 360KHz,
    and 1 is 1.4KHz."""
    _fan_clk_ovr = RWBit(_FAN_CONFIG, 2)
    """Enable override of clk_sel to use pwm_freq_div register to determine
    the pwm frequency."""
    invert_fan_output = RWBit(_FAN_CONFIG, 4)
    """When set to True, the magnitude of the fan output signal is inverted,
    making 0 the maximum value and 100 the minimum value."""
    _fan_temp_hyst = RWBits(5, _FAN_TEMP_HYST, 0)
    """The amount of hysteresis applied to temp input to the look up table."""

    _dac_output_enabled = RWBit(_REG_CONFIG, 4)
    _conversion_rate = RWBits(4, _CONVERT_RATE, 0)
    _avg_filter = RWBits(2, _AVG_FILTER, 1)
    _alert_comp = RWBit(_AVG_FILTER, 0)

    # Fan spin-up
    _spin_drive = RWBits(2, _FAN_SPINUP, 3)
    _spin_time = RWBits(3, _FAN_SPINUP, 0)
    _spin_tach_limit = RWBit(_FAN_SPINUP, 5)

    def __init__(self, i2c_bus):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, _I2C_ADDR)

        if (
            not self._part_id in [PART_ID_EMC2101, PART_ID_EMC2101R]
            or self._mfg_id != MFG_ID_SMSC
        ):
            raise AttributeError("Cannot find a EMC2101")

        self._full_speed_lsb = None  # See _calculate_full_speed().
        self.initialize()

    def initialize(self):
        """Reset the controller to an initial default configuration"""
        self._tach_mode_enable = True
        self._enabled_forced_temp = False
        self._spin_tach_limit = False
        self._calculate_full_speed()

    @property
    def part_info(self):
        """The part information: manufacturer, part id and revision. Normally (0x5d, 0x16, 0x1)"""
        return (self._mfg_id, self._part_id, self._part_rev)

    @property
    def internal_temperature(self):
        """The temperature as measured by the EMC2101's internal 8-bit temperature sensor"""
        return self._int_temp

    @property
    def external_temperature(self):
        """The temperature measured using the external diode"""

        temp_lsb = self._ext_temp_lsb
        temp_msb = self._ext_temp_msb
        full_tmp = (temp_msb << 8) | temp_lsb
        full_tmp >>= 5
        full_tmp *= 0.125

        return full_tmp

    @property
    def fan_speed(self):
        """The current speed in Revolutions per Minute (RPM)"""

        val = self._tach_read_lsb
        val |= self._tach_read_msb << 8
        return round(_FAN_RPM_DIVISOR / val, 2)

    def _calculate_full_speed(self, pwm_f=None, dac=None):
        """Determine the LSB value for a 100% fan setting"""
        if dac is None:
            dac = self.dac_output_enabled

        if dac:
            # DAC mode is independent of PWM_F.
            self._full_speed_lsb = float(MAX_LUT_SPEED)
            return

        # PWM mode reaches 100% duty cycle at a 2*PWM_F setting.
        if pwm_f is None:
            pwm_f = self._pwm_freq

        # PWM_F=0 behaves like PWM_F=1.
        self._full_speed_lsb = 2.0 * max(1, pwm_f)

    def _speed_to_lsb(self, percentage):
        """Convert a fan speed percentage to a Fan Setting byte value"""
        return round((percentage / 100.0) * self._full_speed_lsb)

    @property
    def manual_fan_speed(self):
        """The fan speed used while the LUT is being updated and is unavailable. The speed is
        given as the fan's PWM duty cycle represented as a float percentage.
        The value roughly approximates the percentage of the fan's maximum speed"""
        raw_setting = self._fan_setting & MAX_LUT_SPEED
        return (raw_setting / self._full_speed_lsb) * 100

    @manual_fan_speed.setter
    def manual_fan_speed(self, fan_speed):
        if fan_speed not in range(0, 101):
            raise AttributeError("manual_fan_speed must be from 0-100")

        fan_speed_lsb = self._speed_to_lsb(fan_speed)
        lut_disabled = self._fan_lut_prog
        self._fan_lut_prog = True
        self._fan_setting = fan_speed_lsb
        self._fan_lut_prog = lut_disabled

    @property
    def dac_output_enabled(self):
        """When set, the fan control signal is output as a DC voltage instead of a PWM signal"""
        return self._dac_output_enabled

    @dac_output_enabled.setter
    def dac_output_enabled(self, value):
        self._dac_output_enabled = value
        self._calculate_full_speed(dac=value)

    @property
    def lut_enabled(self):
        """Enable or disable the internal look up table used to map a given temperature
        to a fan speed.

        When the LUT is disabled (the default), fan speed can be changed with `manual_fan_speed`.
        To actually set this to True and modify the LUT, you need to use the extended version of
        this driver, :class:`emc2101_lut.EMC2101_LUT`
        """
        return not self._fan_lut_prog

    @property
    def tach_limit(self):
        """The maximum /minimum speed expected for the fan"""

        low = self._tach_limit_lsb
        high = self._tach_limit_msb

        return _FAN_RPM_DIVISOR / ((high << 8) | low)

    @tach_limit.setter
    def tach_limit(self, new_limit):
        num = int(_FAN_RPM_DIVISOR / new_limit)
        self._tach_limit_lsb = num & 0xFF
        self._tach_limit_msb = (num >> 8) & 0xFF

    @property
    def spinup_time(self):
        """The amount of time the fan will spin at the current set drive strength.
        Must be a `SpinupTime`"""
        return self._spin_time

    @spinup_time.setter
    def spinup_time(self, spin_time):
        if not SpinupTime.is_valid(spin_time):
            raise AttributeError("spinup_time must be a SpinupTime")
        self._spin_time = spin_time

    @property
    def spinup_drive(self):
        """The drive strength of the fan on spinup in % max RPM"""
        return self._spin_drive

    @spinup_drive.setter
    def spinup_drive(self, spin_drive):
        if not SpinupDrive.is_valid(spin_drive):
            raise AttributeError("spinup_drive must be a SpinupDrive")
        self._spin_drive = spin_drive

    @property
    def conversion_rate(self):
        """The rate at which temperature measurements are taken. Must be a `ConversionRate`"""
        return self._conversion_rate

    @conversion_rate.setter
    def conversion_rate(self, rate):
        if not ConversionRate.is_valid(rate):
            raise AttributeError("conversion_rate must be a `ConversionRate`")
        self._conversion_rate = rate
