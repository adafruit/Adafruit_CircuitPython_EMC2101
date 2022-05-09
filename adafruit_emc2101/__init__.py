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
from adafruit_emc2101 import emc2101_regs

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EMC2101.git"


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        """Creates CV entries"""
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

    See :class:`adafruit_emc2101.EMC2101_EXT` for (almost) complete device register set.
    See :class:`adafruit_emc2101.EMC2101_LUT` for the temperature look up table functionality.

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

    _sensorfault_exceptions = True
    """If True, sensor faults for the external sensor are reported as an
    exception."""

    _part_id = ROUnaryStruct(emc2101_regs.REG_PARTID, "<B")
    """Device Part ID field value, see also _part_rev and _part_id."""
    _mfg_id = ROUnaryStruct(emc2101_regs.REG_MFGID, "<B")
    """Device Manufacturer ID field value, see also _part_rev and _part_id."""
    _part_rev = ROUnaryStruct(emc2101_regs.REG_REV, "<B")
    """Device Part revision field value, see also _mfg_id and _part_id."""
    _int_temp = ROUnaryStruct(emc2101_regs.INTERNAL_TEMP, "<b")

    # Some of these registers are defined as two halves because the chip does
    # not support multi-byte reads or writes, and there is currently no way to
    # tell Struct to do a transaction for each byte.

    # IMPORTANT!
    # The sign bit for the external temp is in the msbyte so mark it as signed
    #     and lsb as unsigned.
    # The Lsbyte is shadow-copied when Msbyte is read, so read Msbyte first to
    #     avoid risk of bad reads. See datasheet section 6.1 Data Read Interlock.
    _ext_temp_msb = ROUnaryStruct(emc2101_regs.EXTERNAL_TEMP_MSB, "<b")
    # Fractions of degree (b7:0.5, b6:0.25, b5:0.125)
    _ext_temp_lsb = ROUnaryStruct(emc2101_regs.EXTERNAL_TEMP_LSB, "<B")

    # IMPORTANT!
    # The Msbyte is shadow-copied when Lsbyte is read, so read Lsbyte first to
    #     avoid risk of bad reads. See datasheet section 6.1 Data Read Interlock.
    _tach_read_lsb = ROUnaryStruct(emc2101_regs.TACH_LSB, "<B")
    """LS byte of the tachometer result reading. """
    _tach_read_msb = ROUnaryStruct(emc2101_regs.TACH_MSB, "<B")
    """MS byte of the tachometer result reading. """

    _tach_mode_enable = RWBit(emc2101_regs.REG_CONFIG, 2)
    """The 2 bits of the tach mode config register. """
    _tach_limit_lsb = UnaryStruct(emc2101_regs.TACH_LIMIT_LSB, "<B")
    _tach_limit_msb = UnaryStruct(emc2101_regs.TACH_LIMIT_MSB, "<B")

    # Temperature used to override current external temp measurement.
    # Value is 7-bit + sign (one's complement?)
    forced_ext_temp = UnaryStruct(emc2101_regs.TEMP_FORCE, "<b")
    """The value that the external temperature will be forced to read when
    `forced_temp_enabled` is set. This can be used to test the behavior of the
    LUT without real temperature changes. Force Temp is 7-bit + sign (one's
    complement?)."""
    forced_temp_enabled = RWBit(emc2101_regs.FAN_CONFIG, 6)
    """When True, the external temperature measurement will always be read as
    the value in `forced_ext_temp`. Not applicable if LUT disabled."""

    # PWM/Fan control
    _fan_setting = UnaryStruct(emc2101_regs.REG_FAN_SETTING, "<B")
    """Control register for the fan."""
    _pwm_freq = RWBits(5, emc2101_regs.PWM_FREQ, 0)
    """Fan/PWM frequency setting register. Source frequency is derived via
    the fan pwm divisor."""
    _pwm_freq_div = UnaryStruct(emc2101_regs.PWM_FREQ_DIV, "<B")
    """Fan/PWM frequency divisor register. Controls source frequency for the
    pwm_freq register."""
    _fan_lut_prog = RWBit(emc2101_regs.FAN_CONFIG, 5)
    """Programming-enable (write-enable) bit for the LUT registers."""

    _fan_temp_hyst = RWBits(5, emc2101_regs.FAN_TEMP_HYST, 0)
    """The amount of hysteresis ("wiggle-room") applied to temp input to the
    look up table."""

    _dac_output_enabled = RWBit(emc2101_regs.REG_CONFIG, 4)
    """Bit controlling whether DAC output (pure analog, not PWM) control of
    fan speed is enabled. This should not be enabled unless the hardware is
    also set up for it as, typically, a power transistor is needed on the
    output line. See datasheet section 5.6 for more detail.
    """

    _conversion_rate = RWBits(4, emc2101_regs.CONVERT_RATE, 0)
    """The number of times/second the temperature is sampled, varying from
    1 every 16 seconds to 32 times per second.
    """

    # Fan spin-up
    _spin_drive = RWBits(2, emc2101_regs.FAN_SPINUP, 3)
    """Set the drive circuit power during spin up, from bypass, 50%, 75% and 100%."""
    _spin_time = RWBits(3, emc2101_regs.FAN_SPINUP, 0)
    """Set the time the fan drive stays in spin_up, from 0 to 3.2 sec."""
    _spin_tach_limit = RWBit(emc2101_regs.FAN_SPINUP, 5)
    """Set whether spin-up is aborted if measured speed is lower than the limit.
    Ignored unless REG_CONFIG bit 3 (alt_tach) is 1.
    """

    def __init__(self, i2c_bus):
        # These devices don't ship with any other address.
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, emc2101_regs.I2C_ADDR)

        if (
            not self._part_id
            in [emc2101_regs.PART_ID_EMC2101, emc2101_regs.PART_ID_EMC2101R]
            or self._mfg_id != emc2101_regs.MFG_ID_SMSC
        ):
            raise AttributeError("Cannot find a EMC2101")

        self._sensorfault_exceptions = True
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
        if full_tmp in (
            emc2101_regs.TEMP_FAULT_OPENCIRCUIT,
            emc2101_regs.TEMP_FAULT_SHORT,
        ):
            if self._sensorfault_exceptions:
                raise ValueError("External Sensor fault")
            return int(full_tmp)

        full_tmp *= 0.125
        return float(full_tmp)

    @property
    def fan_speed(self):
        """The current speed in Revolutions per Minute (RPM)"""
        val = self._tach_read_lsb
        val |= self._tach_read_msb << 8
        if val < 1:
            return 0
        return round(emc2101_regs.FAN_RPM_DIVISOR / val, 2)

    def _calculate_full_speed(self, pwm_f=None, dac=None):
        """Determine the LSB value for a 100% fan setting"""
        if dac is None:
            dac = self.dac_output_enabled

        if dac:
            # DAC mode is independent of PWM_F.
            self._full_speed_lsb = float(emc2101_regs.MAX_LUT_SPEED)
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
        raw_setting = self._fan_setting & emc2101_regs.MAX_LUT_SPEED
        fan_speed = self._full_speed_lsb
        if fan_speed < 1:
            return 0
        return (raw_setting / fan_speed) * 100

    @manual_fan_speed.setter
    def manual_fan_speed(self, fan_speed):
        if fan_speed not in range(0, 101):
            raise AttributeError("manual_fan_speed must be from 0-100")

        fan_speed_lsb = self._speed_to_lsb(fan_speed)
        lut_disabled = self._fan_lut_prog
        # Enable programming
        self._fan_lut_prog = True
        # Set
        self._fan_setting = fan_speed_lsb
        # Restore.
        self._fan_lut_prog = lut_disabled

    @property
    def dac_output_enabled(self):
        """When set, the fan control signal is output as a DC voltage instead of a PWM signal"""
        return self._dac_output_enabled

    @dac_output_enabled.setter
    def dac_output_enabled(self, value):
        """When set, the fan control signal is output as a DC voltage instead of a PWM signal.
        Be aware that the DAC output very likely requires different hardware to the PWM output.
        See datasheet and examples for info.
        """
        self._dac_output_enabled = value
        self._calculate_full_speed(dac=value)

    @property
    def lut_enabled(self):
        """Enable or disable the internal look up table used to map a given
        temperature to a fan speed.

        When the LUT is disabled (the default), fan speed can be changed with
        `manual_fan_speed`.  To actually set this to True and modify the LUT,
        you need to use the extended version of this driver, :class:`emc2101_lut.EMC2101_LUT`
        """
        return not self._fan_lut_prog

    @property
    def tach_limit(self):
        """The maximum /minimum speed expected for the fan"""

        low = self._tach_limit_lsb
        high = self._tach_limit_msb
        limit = high << 8 | low
        if limit < 1:
            return 0
        return emc2101_regs.FAN_RPM_DIVISOR / limit

    @tach_limit.setter
    def tach_limit(self, new_limit):
        """Set the speed limiter on the fan PWM signal. The value of 15000 is
        arbitrary, but very few fans run faster than this.
        """
        if not 1 <= new_limit <= 14000:
            raise AttributeError("tach_limit must be from 1-14000")
        num = int(emc2101_regs.FAN_RPM_DIVISOR / new_limit)
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
