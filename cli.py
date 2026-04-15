import hid
from hid_sample import HidSample

h = hid.Device(0xc0de, 0xcafe)

while True:
    data = h.read(10)

    sample = HidSample.from_bytes(bytes(data))

    print(sample)                 # pretty output
    print(sample.freq_hz)         # direct access
    print(sample.gate_label)      # mapped value