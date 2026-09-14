"""Repair the MSVC pragma spelling in the locked EigenPy 3.12.0 headers.

MSVC __pragma accepts preprocessing tokens, whereas _Pragma accepts a string.
This changes a build header only; it does not modify the binary dependency.
"""
from pathlib import Path
import sys

header = Path(sys.argv[1]) / 'Library/include/eigenpy/fwd.hpp'
text = header.read_text(encoding='utf-8')
old = '#define EIGENPY_PRAGMA(x) __pragma(#x)'
new = '#define EIGENPY_PRAGMA(x) __pragma(x)'
if text.count(old) != 1:
    raise RuntimeError('Locked EigenPy pragma changed; review this patch before building')
header.write_text(text.replace(old, new), encoding='utf-8')
print('Repaired EigenPy MSVC __pragma argument')
