
all: arm bytecode

clean:
	rm -f $(ARMOBJS) $(BYTEOBJS)

ARMOBJS=armv7m/__init__.mpy \
	armv7m/emc2101_enums.mpy \
	armv7m/emc2101_ext.mpy \
	armv7m/emc2101_fanspeed.mpy \
	armv7m/emc2101_lut.mpy \
	armv7m/emc2101_regs.mpy

BYTEOBJS=bytecode/__init__.mpy  \
	bytecode/emc2101_enums.mpy  \
	bytecode/emc2101_ext.mpy  \
	bytecode/emc2101_fanspeed.mpy  \
	bytecode/emc2101_lut.mpy  \
	bytecode/emc2101_regs.mpy

arm: $(ARMOBJS)
	ls -l $(ARMOBJS)
bytecode: $(BYTEOBJS)
	ls -l $(BYTEOBJS)

MPYCROSS=$(HOME)/fanctrl.py/bin/mpy-cross

armv7m/%.mpy: %.py
	@mkdir -p armv7m
	$(MPYCROSS) -O2 -march=armv7m -X emit=native -o $@  $<

bytecode/%.mpy: %.py
	@mkdir -p bytecode
	$(MPYCROSS) -O2 -X emit=bytecode -o $@  $<

