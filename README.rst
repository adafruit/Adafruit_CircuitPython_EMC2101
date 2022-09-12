Introduction
============

.. image:: https://readthedocs.org/projects/adafruit-circuitpython-emc2101/badge/?version=latest
    :target: https://docs.circuitpython.org/projects/emc2101/en/latest/
    :alt: Documentation Status

.. image:: https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/main/badges/adafruit_discord.svg
    :target: https://adafru.it/discord
    :alt: Discord

.. image:: https://github.com/adafruit/Adafruit_CircuitPython_EMC2101/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_EMC2101/actions
    :alt: Build Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

CircuitPython driver for EMC2101 brushless fan controller

Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_
* `Register <https://github.com/adafruit/Adafruit_CircuitPython_Register>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_.

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-emc2101/>`_. To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-emc2101

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-emc2101

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install adafruit-circuitpython-emc2101

Usage Example
=============

.. code-block:: python3

    import time
    import board
    from adafruit_emc2101 import EMC2101

    i2c = board.I2C()  # uses board.SCL and board.SDA

    emc = EMC2101(i2c)
    print("Setting fan speed to 25%")
    emc.manual_fan_speed = 25
    time.sleep(2)  # longer sleep to let it spin down from 100%
    print("Fan speed", emc.fan_speed)

Additional examples, including the use of the temperature look up table
(LUT) can be found in the examples/ folder:

* emc2101_lut_example.py
* emc2101_set_pwm_freq.py
* emc2101_simpletest.py

For access to some additional properties, but without configuring the LUT,
use the intermediate class EMC2101_EXT:

.. code-block:: python3

    import time
    import board
    from adafruit_emc2101 import EMC2101_EXT

    i2c = board.I2C()  # uses board.SCL and board.SDA

    emc = EMC2101_EXT(i2c)
    print("External limit temp is", emc.external_temp_high_limit)
    print("Setting external limit temp to 50C")
    emc.external_temp_high_limit = 50

When the temperature limits are exceeded the device sets the alert bit
in the status register and (if configured to do so) will raise the ALERT
output pin as an interrupt.

EMC2101_EXT defines properties for internal and external temperature
limits, and has register definitions for all registers except the LUT
itself. The EMC2101_LUT class includes this as well.

The EMC2101_Regs class is intended for internal use, and defines register
addresses.

Documentation
=============

API documentation for this library can be found on `Read the Docs <https://docs.circuitpython.org/projects/emc2101/en/latest/>`_.

For information on building library documentation, please check out `this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_EMC2101/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
