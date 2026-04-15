import struct


class HidSample:
    def __init__(self, tag, seq, tick_ms, freq_hz, gate_index):
        self.tag = tag
        self.seq = seq
        self.tick_ms = tick_ms
        self.freq_hz = freq_hz
        self.gate_index = gate_index

    @classmethod
    def from_bytes(cls, data: bytes):
        tag, char, seq, tick_ms, freq_hz, gate_index = struct.unpack(
            "<BBHHHH", data[:10]
        )

        return cls(
            tag=chr(char),
            seq=seq,
            tick_ms=tick_ms,
            freq_hz=freq_hz,
            gate_index=gate_index,
        )

    def gate_label(self):
        if self.gate_index == 0:
            return "0.1s"
        if self.gate_index == 1:
            return "1s"
        if self.gate_index == 2:
            return "10s"
        return str(self.gate_index)

    def __str__(self):
        return f"{self.tag} seq={self.seq} tick={self.tick_ms} freq={self.freq_hz} gate={self.gate_label()}"