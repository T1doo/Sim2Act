"""Read PE architecture, imports and export names without loading native code."""

import struct


def inspect(data):
    if data[:2] != b"MZ":
        raise ValueError("Not a PE image")
    pe = struct.unpack_from("<I", data, 60)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Missing PE signature")
    machine, count = struct.unpack_from("<HH", data, pe + 4)
    size, flags = struct.unpack_from("<HH", data, pe + 20)
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic not in (0x10B, 0x20B):
        raise ValueError("Unknown optional header")
    directory = optional + (112 if magic == 0x20B else 96)
    sections = []
    for index in range(count):
        offset = optional + size + index * 40
        virtual, address, raw_size, raw = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((address, min(virtual, raw_size), raw))

    def at(address, length=1):
        for start, length_bound, raw in sections:
            if start <= address and address + length <= start + length_bound:
                result = raw + address - start
                if result + length <= len(data):
                    return result
        raise ValueError("PE RVA outside backed section")

    def name(address):
        start = at(address)
        end = data.find(b"\0", start, start + 4096)
        if end < 0:
            raise ValueError("Unbounded PE name")
        return data[start:end].decode("ascii")

    imports, exports = [], []
    address, length = struct.unpack_from("<II", data, directory + 8)
    if address:
        for index in range(min(length // 20, 4096)):
            entry = struct.unpack_from("<IIIII", data, at(address + index * 20, 20))
            if not any(entry):
                break
            imports.append(name(entry[3]))
        else:
            raise ValueError("Unterminated PE import directory")
    address, length = struct.unpack_from("<II", data, directory)
    if address:
        table = at(address, 40)
        total = struct.unpack_from("<I", data, table + 24)[0]
        names = struct.unpack_from("<I", data, table + 32)[0]
        if total > 100000:
            raise ValueError("Excess PE export count")
        for index in range(total):
            exports.append(name(struct.unpack_from("<I", data, at(names + index * 4, 4))[0]))
    return dict(machine=hex(machine), pe32plus=magic == 0x20B, dll=bool(flags & 0x2000),
                imports=sorted(imports), exports=sorted(exports))
