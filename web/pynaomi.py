#!/usr/bin/python2
# vim: set tabstop=4 noexpandtab :
# Triforce Netfirm Toolbox, put into the public domain. 
# Please attribute properly, but only if you want.

# More modularized.

from __future__ import print_function

import struct, sys
import socket
import types
import time

try:
	import Crypto.Cipher
	from Crypto.Cipher import DES
except ImportError:
	# dummy object.
	class DES(object):
		def encrypt(data):
			return data
		@staticmethod
		def new(*arg):
			return DES()


class NaomiToolbox (object):
	DEFAULT_ADDRESS = "192.168.5.112"
	DEFAULT_PORT = 10703
	EMPTY_KEYCODE = "\x00" * 8

	def __init__(self, address = None, port = None):
		# Connect to this IP address.
		self.addr = address or self.DEFAULT_ADDRESS
		self.port = port or self.DEFAULT_PORT
		# Socket.
		self.s = None
		if address:
			self.connect()
		if not bytes is str:
			# Python3 and beyond
			NaomiToolbox.EMPTY_KEYCODE = bytes(8)

	def emitstatus(self, msg):
		"""
		Print status message.
		Override in subclasses to override print behavior.
		"""
		print("STATUS: %s" % msg)
		sys.stdout.flush()
		return

	def emitprogress(self, val):
		"""
		Print progress message (overwrite current line; suppress newline)
		"""
		print("%08x" % val, end='\r')
		sys.stdout.flush()

	def connect(self, address = None, port = None):
		"""
		Connect to Naomi system.
		If address unspecified, use self.DEFAULT_ADDRESS;
		If port unspecified, use self.DEFAULT_PORT;
		To reconnect, call with no arguments.
		"""
		self.addr = address or self.DEFAULT_ADDRESS
		if port:
			self.port = port
# connect to the Triforce. Port is tcp/10703.
# note that this port is only open on
#	- all Type-3 triforces,
#	- pre-type3 triforces jumpered to satellite mode.
# - it *should* work on naomi and chihiro, but due to lack of hardware, i didn't try.
		if not self.s:
			self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		else:
			return self.s
		self.emitstatus("connecting to %s:%s ..." % (self.addr, self.port))
		try:
			self.s.connect((self.addr, self.port))
		except socket.error:
			self.emitstatus("connection failed")
			raise
		self.emitstatus("connected to %s:%s" % (self.addr, self.port))
		return self.s

	def close(self):
		res = self.s.close()
		self.s = None
		return res

	def readsocket(self, n):
		"""Receive number of bytes, with hard blocking.
		Returns bytes as string.
		"""
		res = bytes()
		while len(res) < n:
			res += self.s.recv(n - len(res))
		return res

	def HOST_Read16(self, addr):
		"""Peek 16 bytes from Host memory.
		Returns bytes as string.
		"""
		self.s.send(struct.pack("<II", 0xf0000004, addr))
		data = self.readsocket(0x20)
		res = bytes()
		for d in xrange(0x10):
			res += data[4 + (d ^ 3)]
		return res

	def HOST_Read4(self, addr, type = 0):
		"""Peek 4 bytes from Host memory.
		Returns bytes as string.
		"""
		self.s.send(struct.pack("<III", 0x10000008, addr, type))
		return self.s.recv(0xc)[8:]

	def HOST_Poke4(self, addr, data):
		"""Poke 4 bytes into Host memory."""
		self.s.send(struct.pack("<IIII", 0x1100000C, addr, 0, data))

	def HOST_Restart(self):
		"""Restart host."""
		self.s.send(struct.pack("<I", 0x0A000000))

# Read a number of bytes (up to 32k) from DIMM memory (i.e. where the game is). Probably doesn't work for NAND-based games.
	def DIMM_Read(self, addr, size):
		"""Read number of bytes (up to 32k) from DIMM memory (i.e. where the game is).
		Probably doesn't work for NAND-based games.
		Returns bytes as string.
		"""
		self.s.send(struct.pack("<III", 0x05000008, addr, size))
		return self.readsocket(size + 0xE)[0xE:]

	def DIMM_GetInformation(self):
		"""???
		Returns bytes as string (16 byte structure).
		"""
		self.s.send(struct.pack("<I", 0x18000000))
		return self.readsocket(0x10)

	def DIMM_SetInformation(self, crc, length):
		"""???
		"""
		#print("length: %08x" % length)
		self.s.send(struct.pack("<IIII", 0x1900000C, crc & 0xFFFFFFFF, length, 0))

	def DIMM_Upload(self, addr, data, mark):
		"""Upload bytes to memory address.
		"""
		self.s.send(struct.pack("<IIIH", 0x04800000 | (len(data) + 0xA) | (mark << 16), 0, addr, 0) + data)

	def NETFIRM_GetInformation(self):
		"""???
		Returns 1028-byte string.
		"""
		self.s.send(struct.pack("<I", 0x1e000000))
		return self.s.recv(0x404)

	def CONTROL_Read(self, addr):
		"""???
		Returns 12-byte string.
		"""
		self.s.send(struct.pack("<II", 0xf2000004, addr))
		return self.s.recv(0xC)

	def SECURITY_SetKeycode(self, data = None):
		"""???
		"""
		# TODO: raise IndexError exception. Or KeyError (lol).
		if data is None:
			data = self.EMPTY_KEYCODE
		assert len(data) == 8
		self.s.send(struct.pack("<I", 0x7F000008) + data)

	def HOST_SetMode(self, v_and, v_or):
		"""???
		Returns 8-byte string.
		"""
		self.s.send(struct.pack("<II", 0x07000004, (v_and << 8) | v_or))
		return self.readsocket(0x8)

	def DIMM_SetMode(self, v_and, v_or):
		self.s.send(struct.pack("<II", 0x08000004, (v_and << 8) | v_or))
		return self.readsocket(0x8)

	def DIMM22(self, data):
		assert len(data) >= 8
		self.s.send(struct.pack("<I", 0x22000000 | len(data)) + data)

	def MEDIA_SetInformation(self, data):
		assert len(data) >= 8
		self.s.send(struct.pack("<I",	0x25000000 | len(data)) + data)

	def MEDIA_Format(self, data):
		self.s.send(struct.pack("<II", 0x21000004, data))

	def TIME_SetLimit(self, data):
		self.s.send(struct.pack("<II", 0x17000004, data))

	def DIMM_DumpToFile(self, file):
		for x in xrange(0, 0x20000, 1):
			file.write(self.DIMM_Read(x * 0x8000, 0x8000))
			#sys.stderr.write("%08x\r" % x)
			self.emitprogress(x)

	def HOST_DumpToFile(self, file, addr, len):
		for x in range(addr, addr + len, 0x10):
#				if not (x & 0xFFF):
			#sys.stderr.write("%08x\r" % x)
			self.emitprogress(x)
			file.write(self.HOST_Read16(x))

	def HOST_DumpToFile2(self, file):
		for x in xrange(0, 0x10000, 1):
			file.write(self.HOST_Read16(0x80000000 + x * 0x10))
			#sys.stderr.write("%08x\r" % x)
			self.emitprogress(x)


	def DIMM_UploadFile(self, fileobj, key = None):
		"""
upload a file into DIMM memory, and optionally encrypt for the given key.
note that the re-encryption is obsoleted by just setting a zero-key, which
is a magic to disable the decryption.
		"""
		import zlib
		crc = 0
		addr = 0
		if key:
			d = DES.new(key[::-1], DES.MODE_ECB)
		while True:
			#sys.stderr.write("%08x\r" % addr)
			self.emitprogress(addr)
			data = fileobj.read(0x8000)
			if not len(data):
				break
			if key:
				data = d.encrypt(data[::-1])[::-1]
			self.DIMM_Upload(addr, data, 0)
			crc = zlib.crc32(data, crc)
			addr += len(data)
		crc = ~crc
		if bytes is str:
			self.DIMM_Upload(addr, "12345678", 1)
		else:
			self.DIMM_Upload(addr, bytes("12345678", 'latin-1'), 1)
		self.DIMM_SetInformation(crc, addr)

	def DIMM_UploadNamedFile(self, name, key = None):
		return self.DIMM_UploadFile(open(name, "rb"), key)

	def PATCH_MakeProgressCode(self, x):
		"""Obsolete.  Kept for historical reference."""
		#addr = 0x80066ed8 # 2.03
		#addr = 0x8005a9c0 # 1.07
		#addr = 0x80068304 # 2.15
		addr = 0x80068e0c # 3.01
		self.HOST_Poke4(addr + 0, 0x4e800020)
		self.HOST_Poke4(addr + 4, 0x38a00000 | x)
		self.HOST_Poke4(addr + 8, 0x90a30000)
		self.HOST_Poke4(addr + 12, 0x38a00000)
		self.HOST_Poke4(addr + 16, 0x60000000)
		self.HOST_Poke4(addr + 20, 0x4e800020)
		self.HOST_Poke4(addr + 0, 0x60000000)

	def PATCH_MakeContentError(self, x):
		"""Obsolete.  Preserved for historical reference."""
		#addr = 0x80066b30 # 2.03
		#addr = 0x8005a72c # 1.07
		#addr = 0x80067f5c # 2.15
		addr = 0x8005a72c # 3.01
		self.HOST_Poke4(addr + 0, 0x4e800020)
		self.HOST_Poke4(addr + 4, 0x38a00000 | x)
		self.HOST_Poke4(addr + 8, 0x90a30000)
		self.HOST_Poke4(addr + 12, 0x38a00000)
		self.HOST_Poke4(addr + 16, 0x60000000)
		self.HOST_Poke4(addr + 20, 0x4e800020)
		self.HOST_Poke4(addr + 0, 0x60000000)

	def PATCH_CheckBootID(self):
		"""
this essentially removes a region check, and is triforce-specific; It's also segaboot-version specific.
- look for string: "CLogo::CheckBootId: skipped."
- binary-search for lower 16bit of address
"""

		# 3.01
		addr = 0x8000dc5c
		self.HOST_Poke4(addr + 0, 0x4800001C)
		return

		addr = 0x8000CC6C # 2.03, 2.15
		#addr = 0x8000d8a0 # 1.07
		self.HOST_Poke4(addr + 0, 0x4e800020)
		self.HOST_Poke4(addr + 4, 0x38600000)
		self.HOST_Poke4(addr + 8, 0x4e800020)
		self.HOST_Poke4(addr + 0, 0x60000000)

# ok, now you're on your own, the tools are there.
# We see the DIMM space as it's seen by the dimm-board (i.e. as on the disc).
# It will be transparently decrypted when accessed from Host, unless a
# zero-key has been set. We do this before uploading something, so we don't
# have to bother with the inserted key chip. Still, some key chip must be
# present.
# You need to configure the triforce to boot in "satellite mode", 
# which can be done using the dipswitches on the board (type-3) or jumpers 
# (VxWorks-style). 
# The dipswitch for type-3 must be in the following position:
#	- SW1: ON ON *
#	- It shouldn't wait for a GDROM anymore, but display error 31. 
# For the VxWorks-Style:
#	- Locate JP1..JP3 on the upper board in the DIMM board. They are near 
#		the GDROM-connector. 
#		The jumpers must be in this position for satellite mode:
#		1		3
#		[. .].	JP1
#		[. .].	JP2
#		 .[. .] JP3
#	- when you switch on the triforce, it should say "waiting for network..."
#
# Good Luck. Warez are evil.

	@staticmethod
	def main(argv):
		addr = None
		filepath = None
		if len(argv) > 2:
			filepath = argv[2]
			addr = argv[1]
		elif len(argv) > 1:
			filepath = argv[1]

		toolbox = NaomiToolbox(addr)
		toolbox.connect()

		# display "now loading..."
		toolbox.emitstatus("display now loading")
		toolbox.HOST_SetMode(0, 1)
		# disable encryption by setting magic zero-key
		toolbox.emitstatus("disabling encryption")
		#toolbox.SECURITY_SetKeycode("\x00" * 8)
		toolbox.SECURITY_SetKeycode(toolbox.EMPTY_KEYCODE)

		# uploads file. Also sets "dimm information" (file length and crc32)
		toolbox.emitstatus("uploading file")
		toolbox.DIMM_UploadNamedFile(filepath)
		# restart host, this wil boot into game
		#toolbox.emitstatus("restaring in 10 seconds...")
		#time.sleep(10)
		toolbox.emitstatus("restarting host")
		toolbox.HOST_Restart()

		if 0:
			# this is triforce-specific, and will remove the "region check"
			toolbox.PATCH_CheckBootID()

		if 1:
			toolbox.emitstatus("time limit hack looping...")
			while 1:
			# set time limit to 10h. According to some reports, this does not work.
				toolbox.TIME_SetLimit(600000)
				time.sleep(5)

# this is not required anymore:
#	PATCH_MakeContentError(2)
#	PATCH_MakeProgressCode(5)

if __name__ == "__main__":
	NaomiToolbox.main(sys.argv)

