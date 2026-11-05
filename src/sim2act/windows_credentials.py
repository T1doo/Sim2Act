"""Read an explicitly selected current-user Windows DPAPI SecureString file."""
import ctypes
from ctypes import wintypes
import os

from .desktop_protocol import ProtocolError, ordinary


def read_dpapi(path):
    if os.name != 'nt':
        raise ProtocolError('WINDOWS_CREDENTIALS_REQUIRED')
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    output=Blob()
    buffer=None
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    try:
        text=ordinary(path).read_text(encoding='ascii').strip()
        if not 2 <= len(text) <= 131072:raise ValueError
        encrypted=bytes.fromhex(text)
        buffer=(ctypes.c_ubyte*len(encrypted)).from_buffer_copy(encrypted)
        source=Blob(len(encrypted),buffer)
        decrypt=ctypes.WinDLL('crypt32',use_last_error=True).CryptUnprotectData
        decrypt.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        decrypt.restype=wintypes.BOOL
        if not decrypt(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output)):
            raise ValueError
        return ctypes.string_at(output.data,output.size).decode('utf-16-le')
    except Exception:
        raise ProtocolError('LOCAL_CREDENTIAL_UNAVAILABLE') from None
    finally:
        if output.data:
            ctypes.memset(output.data,0,output.size)
            kernel.LocalFree(output.data)
        if buffer is not None:ctypes.memset(buffer,0,len(buffer))
