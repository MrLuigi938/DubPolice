"""Report which archives another process currently holds open (exclusive-open test, reads nothing)."""
import ctypes
import os
import sys
from ctypes import wintypes

k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
k.CreateFileW.restype = wintypes.HANDLE
k.CloseHandle.argtypes = [wintypes.HANDLE]
INVALID = wintypes.HANDLE(-1).value

folder = sys.argv[1]
held, free = [], []
for n in sorted(os.listdir(folder)):
    if not n.endswith((".ttarch2", ".lua")):
        continue
    h = k.CreateFileW(os.path.join(folder, n), 0x80000000, 0, None, 3, 0x80, None)
    if h == INVALID:
        held.append(n)
    else:
        k.CloseHandle(h)
        free.append(n)
print("HELD by game:", held)
print("not held:", free)
