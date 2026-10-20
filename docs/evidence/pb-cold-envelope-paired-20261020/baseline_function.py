def _cold_graph_bytes(values):
    """Fresh complete local pin bytes; never loaded and never an authority.

    Initial/add validation traverses the same complete raw row storage payload.
    Hoisting the class/imports does not cache bytes, fingerprints or permissions.
    """
    output = _ColdGraphBytesIO()
    _ColdGraphPickler(output, protocol=5).dump(values)
    return b"SIM2ACT_COLD_GRAPH_PICKLE_V2\x00" + output.getvalue()
