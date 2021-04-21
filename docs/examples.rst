Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/emc2101_simpletest.py
    :caption: examples/emc2101_simpletest.py
    :linenos:

LUT Usage Example
-----------------

Use the temperature to fan speed Look Up Table to automatically control the fan speed.
This example requires more memory than the first one because it needs to use the extended
:class:`adafruit_emc2101.emc2101_lut.EMC2101_LUT` driver to access LUT functionality.

.. literalinclude:: ../examples/emc2101_lut_example.py
    :caption: examples/emc2101_lut_example.py
    :linenos:


PWM Tuning
-----------------

Adjust the EMC2101s PWM settings to fit your application.
This example requires more memory than the first one because it needs to use the extended
:class:`adafruit_emc2101.emc2101_lut.EMC2101_LUT` driver to access LUT functionality.

.. literalinclude:: ../examples/emc2101_set_pwm_freq.py
    :caption: examples/emc2101_set_pwm_freq.py
    :linenos:
