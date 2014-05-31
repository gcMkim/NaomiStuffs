#!/usr/bin/env python2.7

from __future__ import print_function

import wx
import os, os.path
import stat
import copy
import threading


class prefs:
    title = "GCArc NaomiBoot"
    size = (320, 240)




##################################################
# --- begin copy-paste naomi_boot_oo.py here --- #
##################################################

#!/usr/bin/python2.6
# Triforce Netfirm Toolbox, put into the public domain. 
# Please attribute properly, but only if you want.
import struct, sys
import socket
import time
try:
	from Crypto.Cipher import DES
except:
	#raise  # uncomment to make fatal.
	pass

# connect to the Triforce. Port is tcp/10703.
# note that this port is only open on
#	- all Type-3 triforces,
#	- pre-type3 triforces jumpered to satellite mode.
# - it *should* work on naomi and chihiro, but due to lack of hardware, i didn't try.

#triforce_ip = "192.168.0.9"
#s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
##print "connecting..."
#s.connect((triforce_ip, 10703))
#print "ok!"

class TriforceNetfirmToolbox (object):
	# Set default IP here.
	DEFAULT_IP = '192.168.0.9'
	DEFAULT_PORT = 10703

	def __init__(self, triforce_ip=None):
		self.s = None
		if not triforce_ip:
			triforce_ip = TriforceNetfirmToolbox.DEFAULT_IP
		self.triforce_ip = triforce_ip

	def connect(self, triforce_ip=None):
		if not triforce_ip:
			triforce_ip = self.triforce_ip
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.connect((triforce_ip, TriforceNetfirmToolbox.DEFAULT_PORT))
		self.feedback_connected()
		return self.s

	# feedback wrappers.  Override in subclass as needed.

	# when socket is connected
	def feedback_connected(self):
		print("ok!")

	# when progress in a long operation is made - expect number
	def feedback_progress(self, num, denom=None):
		sys.stderr.write("%08x\r" % num)

	# when information output
	def feedback_info(self, msg):
		print(msg)


	# naomi_boot.py port follows.

	# a function to receive a number of bytes with hard blocking
	def readsocket(self, n):
		res = ""
		while len(res) < n:
			res += self.s.recv(n - len(res))
		return res

	# Peeks 16 bytes from Host (gamecube) memory
	def HOST_Read16(self, addr):
		self.s.send(struct.pack("<II", 0xf0000004, addr))
		data = self.readsocket(0x20)
		res = ""
		for d in xrange(0x10):
			res += data[4 + (d ^ 3)]
		return res

	# same, but 4 bytes.
	def HOST_Read4(self, addr, type = 0):
		self.s.send(struct.pack("<III", 0x10000008, addr, type))
		return self.s.recv(0xc)[8:]

	def HOST_Poke4(self, addr, data):
		self.s.send(struct.pack("<IIII", 0x1100000C, addr, 0, data))

	def HOST_Restart(self):
		self.s.send(struct.pack("<I", 0x0A000000))

	# Read a number of bytes (up to 32k) from DIMM memory (i.e. where the game is). Probably doesn't work for NAND-based games.
	def DIMM_Read(self, addr, size):
		self.s.send(struct.pack("<III", 0x05000008, addr, size))
		return self.readsocket(size + 0xE)[0xE:]

	def DIMM_GetInformation(self):
		self.s.send(struct.pack("<I", 0x18000000))
		return self.readsocket(0x10)

	def DIMM_SetInformation(self, crc, length):
		#print "length: %08x" % length
		self.feedback_info("length: %08x" % length)
		self.s.send(struct.pack("<IIII", 0x1900000C, crc & 0xFFFFFFFF, length, 0))

	def DIMM_Upload(self, addr, data, mark):
		self.s.send(struct.pack("<IIIH", 0x04800000 | (len(data) + 0xA) | (mark << 16), 0, addr, 0) + data)

	def NETFIRM_GetInformation(self):
		self.s.send(struct.pack("<I", 0x1e000000))
		return self.s.recv(0x404)

	def CONTROL_Read(self, addr):
		self.s.send(struct.pack("<II", 0xf2000004, addr))
		return self.s.recv(0xC)

	def SECURITY_SetKeycode(self, data):
		assert len(data) == 8
		self.s.send(struct.pack("<I", 0x7F000008) + data)

	def HOST_SetMode(self, v_and, v_or):
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
		self.s.send(struct.pack("<II", 0x17000004, data), 0x8000)

	def DIMM_DumpToFile(self, tofile):
		for x in xrange(0, 0x20000, 1):
			tofile.write(self.DIMM_Read(x * 0x8000, 0x8000))
			#sys.stderr.write("%08x\r" % x)
			self.feedback_progress(x)

	def HOST_DumpToFile(self, tofile, addr, len):
		for x in range(addr, addr + len, 0x10):
	#		if not (x & 0xFFF):
			#sys.stderr.write("%08x\r" % x)
			self.feedback_progress(x)
			tofile.write(self.HOST_Read16(x))

# upload a file into DIMM memory, and optionally encrypt for the given key.
# note that the re-encryption is obsoleted by just setting a zero-key, which
# is a magic to disable the decryption.
	def DIMM_UploadFile(self, name, key = None):
		import zlib
		crc = 0
		a = open(name, "rb")
		addr = 0
		if key:
			d = DES.new(key[::-1], DES.MODE_ECB)
		while True:
			#sys.stderr.write("%08x\r" % addr)
			self.feedback_progress(addr)
			data = a.read(0x8000)
			if not len(data):
				break
			if key:
				data = d.encrypt(data[::-1])[::-1]
			self.DIMM_Upload(addr, data, 0)
			crc = zlib.crc32(data, crc)
			addr += len(data)
		crc = ~crc
		self.DIMM_Upload(addr, "12345678", 1)
		self.DIMM_SetInformation(crc, addr)

	# obsolete
	def PATCH_MakeProgressCode(self, x):
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

	#obsolete
	def PATCH_MakeContentError(self, x):
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

	# this essentially removes a region check, and is triforce-specific; It's also segaboot-version specific.
	# - look for string: "CLogo::CheckBootId: skipped."
	# - binary-search for lower 16bit of address
	def PATCH_CheckBootID_301(self):
		# 3.01
		addr = 0x8000dc5c
		self.HOST_Poke4(addr + 0, 0x4800001C)

	def PATCH_CheckBootID_203(self):
		self.addr = 0x8000CC6C # 2.03, 2.15
		self.HOST_Poke4(addr + 0, 0x4e800020)
		self.HOST_Poke4(addr + 4, 0x38600000)
		self.HOST_Poke4(addr + 8, 0x4e800020)
		self.HOST_Poke4(addr + 0, 0x60000000)

	def PATCH_CheckBootID_215(self):
		return self.PATCH_CheckBootID_203()

	def PATCH_CheckBootID_107(self):
		self.addr = 0x8000d8a0 # 1.07
		self.HOST_Poke4(addr + 0, 0x4e800020)
		self.HOST_Poke4(addr + 4, 0x38600000)
		self.HOST_Poke4(addr + 8, 0x4e800020)
		self.HOST_Poke4(addr + 0, 0x60000000)

	PATCH_CheckBootID = PATCH_CheckBootID_301  # default to 3.01

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

	def HOST_DumpToFileSimple(self, tofile):
		for x in xrange(0, 0x10000, 1):
			tofile.write(self.HOST_Read16(0x80000000 + x * 0x10))
			#sys.stderr.write("%08x\r" % x)
			self.feedback_progress(x, 0x10000)

# this is not required anymore:
#	PATCH_MakeContentError(2)
#	PATCH_MakeProgressCode(5)


# Class-based wrapper.
class TriforceNetfirmUploader (TriforceNetfirmToolbox):
	def __init__ (self, triforce_ip=None, filepath=None, timeloop=1):
		TriforceNetfirmToolbox.__init__(self)
		self.triforce_ip = triforce_ip
		# disable encryption by setting magic zero-key
		self.keycode = "\x00" * 8
		# for time limit hack loop
		self.timelimit = 10*60*1000
		# seconds between steps of time limit hack loop
		self.loopinterval = 5
		# use time limit hack loop
		self.timeloop = timeloop
		# file to upload
		self.filepath = None
		if filepath:
			self.upload(filepath)

	# Override in subclass as needed.
	def feedback_connected (self):
		print("connecting %s ok!" % self.triforce_ip)

	# Override in subclass as needed.
	def feedback_progress (self, num):
		sys.stderr.write("%08x\r" % num)

	# Override in subclass as needed.
	def feedback_start (self):
		"Called when uploading begins"
		print("Now loading '%s'..." % self.filepath)

	# Override in subclass as needed.
	def feedback_looping (self):
		"Called when begining time limit hack loop"
		print("time limit hack looping...")

	# Override in subclass as needed.
	def feedback_loopstep (self):
		"Called each iteration of time limit hack loop.  Display a progress bar or something."
		pass

    # Override in subclass as needed.
	def feedback_finished (self):
		"Called when upload/timeloop finished."
		pass

	def upload (self, filepath, timeloop=None):
		if not self.s:
			self.connect(self.triforce_ip)
		if not self.s:    # still failed
			return -1
		self.filepath = filepath
		if not (timeloop is None):
			self.timeloop = timeloop

		self.feedback_start()    # display "now loading..."
		self.HOST_SetMode(0, 1)
		# set keycode; default is magic zero-key
		self.SECURITY_SetKeycode(self.keycode)
		
		# uploads file. Also sets "dimm information" (file length and crc32)
		self.DIMM_UploadFile(self.filepath)
		# restart host, this wil boot into game
		#print "restarting in 10 seconds..."
		#time.sleep(10)
		self.HOST_Restart()

		self.feedback_looping()  # display "time limit hack looping..."
		while self.timeloop:
			# set time limit to 10h. According to some reports, this does not work.
			self.TIME_SetLimit(self.timelimit)
			self.feedback_loopstep()  # display progress indicator
			time.sleep(self.loopinterval)
		self.feedback_finished()

	def __call__ (self, *args, **kwargs):
		self.upload(self.filepath)

#if __name__ == "__main__":
#	#triforce_ip = '192.168.0.9'
#	triforce_ip = '127.0.0.1'
#	toolbox = TriforceNetfirmUploader(triforce_ip, sys.argv[1], timeloop=0)




############################
# --- end naomi_boot_oo.py #
############################

























# Structure:
# App
#  Frame
#   Tab - per naomi machine
#    address, IP address of machine : textbox
#    enable time-hack loop - checkbox
#    path to game image - 
#    drag-n-drop area
#   "


def crumb (msg):
    #print(msg)
    pass


# Checkpointable state.
#state = {
#  # targets - array of dict
#  "targets": [
#    { "name": "Machine1", "addr": "192.168.1.12", "timeloop": True, "image": "./pacman.rom" }
#    ]
#  }



# Custom events.
import wx.lib.newevent
NetfirmOpenEvent, EVT_NETFIRM_OPEN = wx.lib.newevent.NewEvent()
NetfirmProgressEvent, EVT_NETFIRM_PROGRESS = wx.lib.newevent.NewEvent()
NetfirmCompleteEvent, EVT_NETFIRM_COMPLETE = wx.lib.newevent.NewEvent()
NetfirmCloseEvent, EVT_NETFIRM_CLOSE = wx.lib.newevent.NewEvent()
NetfirmFailEvent, EVT_NETFIRM_FAIL = wx.lib.newevent.NewEvent()


class NaomiBooterStateful (object):
    def GetState (self):
        bid = self
        parent = bid.GetParent()
        while parent and bid != parent:
            bid = parent
            parent = bid.GetParent()
        if not bid:
            # Assume 'self' to be toplevel.
            return self.state
        else:
            # 'parent' points to toplevel.
            return bid.state


class NaomiBooterState (wx.FileConfig, dict):
    """App state persistence.

['targets'] : list of targets (Naomi boards).
['openpage'] : currently open tab

"""
    _instance = None

    def __init__ (self):
        dict.__init__(self)
        cwd = os.getcwd()
        cfgpath = os.path.join(cwd, "naomibooter.cfg")
        wx.FileConfig.__init__(self, "NaomiBooter", "GCArcade", cfgpath)
        self.undostack = ()
        self.redostack = ()
        self['targets'] = []
        self['openpage'] = 0
        self['size'] = (320, 240)
        self.observers = []

    def AddObserver (self, observer):
        """Callback function when state changes."""
        self.observers.append(observer)

    def RemoveObserver (self, observer):
        self.observers.remove(observer)

    def NotifyObservers (self):
        for observer in self.observers:
            observer(self)

    def CountUndo (self):
        return len(self.undostack)

    def CountRedo (self):
        return len(self.redostack)

    def MakeSnapshot (self):
        """Save snapshot for undo/redo"""
        snapshot = copy.deepcopy(dict(self))
        return snapshot
        #self.undostack = (snapshot,) + self.undostack

    def Rebase (self):
        """Eliminate all undo and redo stack."""
        self.redostack = ()
        self.undostack = (self.undostack[0],)
        self.Save()
        self.NotifyObservers()

    def Checkpoint (self):
        """'Forward change': Add to undo stack, obliterate redo stack."""
        crumb("+++ Checkpointing undo stack.")
        snapshot = self.MakeSnapshot()
        self.undostack = (snapshot,) + self.undostack
        self.redostack = ()
        self.NotifyObservers()

    def Rollback (self):
        # Rollback undo stack.
        if len(self.undostack) < 2:  # if available.
            return
        crumb("+++ Rollback undo")
        # Move most-recent to redostack.
        self.redostack = (self.undostack[0],) + self.redostack
        # Take next snapshot.
        snapshot = self.undostack[1]
        self.undostack = self.undostack[1:]
        # Restore.
        for key in snapshot.iterkeys():
            self[key] = snapshot[key]
        self.NotifyObservers()
        crumb("+++ UNDO/REDO = %d/%d" % (len(self.undostack), len(self.redostack)))

    def Rollforward (self):
        # Apply redo stack.
        if not self.redostack:  # if available.
            return
        crumb("+++ Replay redo")
        # Take top of redo.
        snapshot = self.redostack[0]
        self.redostack = self.redostack[1:]
        # Push immediate to top of undo.
        self.undostack = (snapshot,) + self.undostack
        # Restore.
        for key in snapshot.iterkeys():
            self[key] = snapshot[key]
        self.NotifyObservers()
        crumb("+++ UNDO/REDO = %d/%d" % (len(self.undostack), len(self.redostack)))

    def MakeDefaultTarget (self):
        return {
            "name": "New Machine",
            "addr": "192.168.0.6",
            "timehack": True,
            "image": "chess.rom"
            }

    def Load (self):
        # Enumerated targets.
        # Keep trying index until not-found.
        targetidx = 0
        prefix = "targets/%d" % targetidx
        while self.Exists(prefix):
            targetstate = {}
            targetstate['name'] = self.Read(prefix + "/name", '')
            targetstate['addr'] = self.Read(prefix + "/addr", '')
            targetstate['timehack'] = self.ReadBool(prefix + "/timehack", False)
            targetstate['image'] = self.Read(prefix + "/image", '')
            self['targets'].append(targetstate)
            targetidx += 1
            prefix = "targets/%d" % targetidx
        if not self['targets']:
            # Default list.
            self['targets'] = [
              self.MakeDefaultTarget()
            ]

    def Save (self):
        self.DeleteGroup('targets')
        targets = self.get('targets', [])
        targetidx = 0
        for targetstate in targets:
            prefix = "targets/%d" % targetidx
            self.Write(prefix + "/name", targetstate.get('name', ''))
            self.Write(prefix + "/addr", targetstate.get('addr', ''))
            self.WriteBool(prefix + "/timehack", targetstate.get('timehack', True))
            self.Write(prefix + "/image", targetstate.get('image', ''))
            targetidx += 1

    def __bool__ (self):
        return dict.__bool__(self)


#state1 = NaomiBooterState()
#state1.Load()
#if not state1:
#  state['targets'] = [
#    { 'name': "Machine1", 'addr': "192.168.12", 'timehack': True, 'image': "./pacman.rom" },
#  ]


# One tab's page.
class NaomiBooterPanel (wx.Panel, NaomiBooterStateful):
    LAUNCH_NULL = 0
    LAUNCH_LOADING = 1
    LAUNCH_ACTIVE = 2
    LAUNCH_ENDING = 3
    LAUNCH_FAILED = 4

    def __init__ (self, parent, statekey):
        wx.Panel.__init__(self, parent=parent)
        self.statekey = statekey
        self.dirty = False
        self.netfirm = None  # TriforceNetfirmUploader
        self.task = None
        self.launching = self.LAUNCH_NULL

        #self.sizer = wx.BoxSizer(wx.VERTICAL)
        p = wx.BoxSizer(wx.VERTICAL)
        #self.SetSizer(self.sizer)

        #line = wx.BoxSizer(wx.HORIZONTAL)
        #self.lbl_name = wx.StaticText(self, label="Name:")
        #self.ask_name = wx.TextCtrl(self)
        #line.Add(self.lbl_name, flag=wx.ALIGN_CENTER_VERTICAL)
        #line.Add(self.ask_name, flag=wx.ALIGN_CENTER_VERTICAL)
        #p.Add(line, flag=wx.EXPAND)

        line = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_addr = wx.StaticText(self, label="IP &Address:")
        self.ask_addr = wx.TextCtrl(self)
        line.Add(self.lbl_addr, 0, flag=wx.ALIGN_CENTER_VERTICAL)
        line.Add(self.ask_addr, 9, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        p.Add(line, flag=wx.EXPAND)

        line = wx.BoxSizer(wx.HORIZONTAL)
        self.ask_timehack = wx.CheckBox(self, label="Enable: &Time Hack Loop")
        line.Add(self.ask_timehack)
        p.Add(line, flag=wx.EXPAND)

        line = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_image = wx.StaticText(self, label="Game &Image:")
        #self.ask_image = wx.TextCtrl(self)
        self.ask_image = wx.FilePickerCtrl(self, style=wx.FLP_USE_TEXTCTRL|wx.FLP_OPEN)
        line.Add(self.lbl_image, 0, flag=wx.ALIGN_CENTER_VERTICAL)
        line.Add(self.ask_image, 9, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        p.Add(line, flag=wx.EXPAND)

        p.AddStretchSpacer(1)

        line = wx.BoxSizer(wx.HORIZONTAL)
        #self.btn_launch = wx.Button(self, label="&Launch")
        self.btn_launch = wx.ToggleButton(self, label="&Launch")
#        self.ask_drop = wx.StaticBox(self, label="Drag and Drop")
#        self.lbl_drop = wx.StaticText(self.ask_drop, label="Drag and drop image file here")
        line.Add(self.btn_launch, 0, flag=wx.ALIGN_TOP)
        #line.AddStretchSpacer(4)
        self.gau_upload = wx.Gauge(self)
        line.Add(self.gau_upload, 1)
        self.btn_reboot = wx.Button(self, label="&Reboot")
        line.Add(self.btn_reboot)
        #line.AddStretchSpacer(1)
#        line.Add(self.ask_drop, 4, flag=wx.EXPAND|wx.ALIGN_CENTER)
        p.Add(line, 1, flag=wx.EXPAND|wx.ALIGN_CENTER)

#        p.AddStretchSpacer()
#
#        line = wx.BoxSizer(wx.HORIZONTAL)
#        self.btn_reboot = wx.Button(self, label="Reboot")
#        line.Add(self.btn_reboot, 0, flag=wx.ALIGN_CENTER)
#        p.Add(line, 1, flag=wx.EXPAND|wx.ALIGN_CENTER)

        self.SetSizer(p)

        #self.Bind(wx.EVT_BUTTON, self.OnLaunch, self.btn_launch)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnLaunch, self.btn_launch)
        self.Bind(wx.EVT_BUTTON, self.OnReboot, self.btn_reboot)
        self.Bind(wx.EVT_TEXT, self.OnChangeAddr, self.ask_addr)
        self.Bind(wx.EVT_CHECKBOX, self.OnChangeTimehack, self.ask_timehack)
        self.Bind(wx.EVT_FILEPICKER_CHANGED, self.OnChangeImage, self.ask_image)

        EVT_NETFIRM_PROGRESS(self, self.OnNetfirmProgress)
        EVT_NETFIRM_COMPLETE(self, self.OnNetfirmComplete)
        EVT_NETFIRM_CLOSE(self, self.OnNetfirmClose)
        EVT_NETFIRM_FAIL(self, self.OnNetfirmFail)

        wx.EVT_KILL_FOCUS(self.ask_addr, self.OnCheckpointingEvent)
        wx.EVT_KILL_FOCUS(self.ask_timehack, self.OnCheckpointingEvent)
        wx.EVT_KILL_FOCUS(self.ask_image, self.OnCheckpointingEvent)


    def SetState (self, targetstate):
        """Restore page state about target machine."""
#        if targetstate['name'] != self.GetName():
#           return
        crumb("+++ Setting state: %r" % targetstate)
        #name = targetstate.get('name', '')
        addr = targetstate.get('addr', '')
        timehack = targetstate.get('timehack', True)
        imgfile = targetstate.get('image', '')

        #self.ask_name.SetValue(str(name))
        self.ask_addr.ChangeValue(str(addr))
        crumb("+++ timehack = %s" % timehack)
        self.ask_timehack.SetValue(bool(timehack))
        self.ask_image.SetPath(str(imgfile))

    def CmdStop (self):
        if self.task:
            self.netfirm.timeloop = 0
            # Then rely on self.netfirm.feedback_finished for thread end.
            self.SyncUi(self.LAUNCH_ENDING)

    def CmdLaunch (self, destip, imgpath, timehack):
        if not imgpath:
            crumb("*** Image not specified")
            self.SyncUi(self.LAUNCH_NULL)
            return
        crumb("*** LAUNCHING '%s'" % imgpath)
        # Get size of imgpath
        st = os.stat(imgpath)
        sz = st[stat.ST_SIZE]
        #self.max_upload = sz
        self.gau_upload.SetRange(sz)
        self.netfirm = TriforceNetfirmUploader(destip)
        self.netfirm.filepath = imgpath
        self.netfirm.timeloop = timehack
        #self.netfirm.feedback_progress = self.UpdateProgress
        #self.netfirm.feedback_looping = self.OnUploadComplete
        #self.netfirm.feedback_finished = self.OnTaskEnd
        self.netfirm.feedback_connected = lambda: True
        self.netfirm.feedback_start = lambda: wx.PostEvent(self, NetfirmOpenEvent())
        self.netfirm.feedback_progress = lambda val: wx.PostEvent(self, NetfirmProgressEvent(value=val))
        self.netfirm.feedback_looping = lambda: wx.PostEvent(self, NetfirmCompleteEvent())
        self.netfirm.feedback_finished = lambda: wx.PostEvent(self, NetfirmCloseEvent())
        crumb("*** thread prepared")
        def uploadertask ():
            try:
                self.netfirm.__call__()
            except Exception, exc:
                #self.OnTaskFail()
                wx.PostEvent(self, NetfirmFailEvent(reason=exc))
        #self.task = threading.Thread(target=self.netfirm)
        self.task = threading.Thread(target=uploadertask)
        #taskset.append(task)
        self.task.start()
        crumb("*** thread started")
        self.SyncUi(self.LAUNCH_LOADING)

    def SyncUi (self, newstate=None):
        # Synchronize UI elements acccording to task states.`
        if newstate is not None:
            self.launching = newstate

        if self.launching == self.LAUNCH_NULL:
            self.btn_launch.Enable()
            self.btn_launch.SetValue(False)
            self.btn_launch.SetLabel("&Launch")
            self.gau_upload.SetValue(0)
        elif self.launching == self.LAUNCH_LOADING:
            self.btn_launch.SetValue(True)
            self.btn_launch.SetLabel("&Launch")
            self.btn_launch.Disable()
        elif self.launching == self.LAUNCH_ACTIVE:
            self.btn_launch.Enable()
            self.btn_launch.SetValue(True)
            self.btn_launch.SetLabel("&Disconnect")
        elif self.launching == self.LAUNCH_ENDING:
            self.btn_launch.SetValue(False)
            self.btn_launch.SetLabel("&Disconnect")
            self.btn_launch.Disable()

    def OnLaunch (self, *args):
        if self.btn_launch.GetValue():
            crumb("*** LAUNCHING")
            destip = self.ask_addr.GetValue()
            timehack = self.ask_timehack.GetValue()
            imgpath = self.ask_image.GetPath()
            self.CmdLaunch(destip, imgpath, timehack)
        else:
            crumb("*** TERMINATING")
            self.CmdStop()
        self.GetState().Rebase()  # destroy undo/redo.

    def OnNetifmrOpen (self):
        self.SyncUi(self.LAUNCH_LOADING)

    def OnNetfirmComplete (self, evt):  
        self.SyncUi(self.LAUNCH_ACTIVE)

    def OnNetfirmClose (self, evt):
        if self.task:
            crumb("*** task terminated")
            #crumb("Attemping to join thread %r" % self.task)
            self.task.join(10.0)
            self.task = None
            self.netfirm = None
        try:
            evt.chain()
        except AttributeError:
            self.SyncUi(self.LAUNCH_NULL)

    def OnNetfirmFail (self, evt):
        self.task = None
        dlg = wx.MessageDialog(parent=self, message=str(evt.reason), caption="Launch failed", style=wx.OK)
        dlg.ShowModal()
        self.SyncUi(self.LAUNCH_NULL)

    def OnNetfirmProgress (self, evt):
        self.gau_upload.SetValue(evt.value)

    def ContinueReboot (self, interrupting=True):
        destip = self.ask_addr.GetValue()
        if interrupting:
            self.task = None
        try:
            crumb("*** ISSUE REBOOT")
            self.netfirm = TriforceNetfirmUploader(destip)
            self.netfirm.connect()
            self.netfirm.HOST_Restart()
            self.netfirm = None
        except:
            pass
        self.SyncUi(self.LAUNCH_NULL)

    def OnReboot (self, *args):
        crumb("*** SEND REBOOT")
        destip = self.ask_addr.GetValue()
        if self.task:
            #self.netfirm.feedback_finished = self.ContinueReboot
            self.netfirm.feedback_finished = lambda: wx.PostEvent(self, NetfirmCloseEvent(chain=self.ContinueReboot))
            self.CmdStop()
        else:
            self.ContinueReboot(False)

    def GetTargetState (self, finalkey=None):
        d = self.GetState()
        for lvl in self.statekey:
            d = d[lvl]
        if finalkey:
            return d[finalkey]
        else:
            return d

    def UpdateState (self, finalkey, val):
        d = self.GetTargetState()
#        d = self.GetState()
#        for lvl in multikey:
#            d = d[lvl]
        d[finalkey] = val
        self.dirty = True
        return val

    def OnCheckpointingEvent (self, *args):
        crumb("+++ Checkpointing")
        if self.dirty:
            self.GetState().Checkpoint()
            self.dirty = False

    def OnChangeAddr (self, *args):
        crumb("+++ Change addr")
        # TODO: generic split into multi-depth.
        #state[self.statekey[0]][self.statekey[1]]['addr'] = self.ask_addr.GetValue()
        self.UpdateState('addr', self.ask_addr.GetValue())

    def OnChangeTimehack (self, *args):
        crumb("+++ Change timehack")
        self.UpdateState('timehack', self.ask_timehack.GetValue())

    def OnChangeImage (self, *args):
        crumb("+++ Change image: %r" % (self.statekey,))
        self.UpdateState('image', self.ask_image.GetPath())
        self.OnCheckpointingEvent(*args)



class NaomiBooterToolbar (wx.ToolBar, NaomiBooterStateful):
    def __init__ (self, parent):
        wx.ToolBar.__init__(self, parent=parent)
        artsrc = wx.ArtProvider()

        bitmap = artsrc.GetBitmap(wx.ART_NEW)
        self.toolAdd = self.AddLabelTool(wx.ID_ADD, label="Add Target", bitmap=bitmap, shortHelp="Add new Naomi board")

        bitmap = artsrc.GetBitmap("gtk-edit")
        self.toolRename = self.AddLabelTool(wx.ID_EDIT, label="Rename Target", bitmap=bitmap, shortHelp="Change nickname of Naomi board")

        bitmap = artsrc.GetBitmap(wx.ART_DELETE)
        self.toolDelete = self.AddLabelTool(wx.ID_DELETE, label="Delete Target", bitmap=bitmap, shortHelp="Delete entry for this Naomi board")

        self.AddSeparator()

        bitmap = artsrc.GetBitmap(wx.ART_UNDO)
        self.toolUndo = self.AddLabelTool(wx.ID_UNDO, label="Undo", bitmap=bitmap, shortHelp="Undo last modification")

        bitmap = artsrc.GetBitmap(wx.ART_REDO)
        self.toolRedo = self.AddLabelTool(wx.ID_REDO, label="Redo", bitmap=bitmap, shortHelp="Redo last undo")

        self.AddSeparator()

        bitmap = artsrc.GetBitmap(wx.ART_QUIT)
        self.toolQuit = self.AddLabelTool(wx.ID_EXIT, label="Quit", bitmap=bitmap, shortHelp="Quit app")

        self.GetState().AddObserver(self.CheckToolbarUndo)  # update undo/redo with state.
        self.CheckToolbarUndo(self.GetState())  # set dis/enabled state now.

    def CheckToolbarUndo (self, state):
        crumb("+++ Checking UNDO buttons.")
        self.EnableTool(wx.ID_UNDO, state.CountUndo() > 1)
        self.EnableTool(wx.ID_REDO, state.CountRedo() > 0)



class NaomiBooterWindow (wx.Frame, NaomiBooterStateful):
    def __init__ (self, parent):
        wx.Frame.__init__(self, parent=parent, title=prefs.title, size=prefs.size)
        self.state = NaomiBooterState()
        self.state.Load()

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        if True:
            self.toolbar = self.BuildToolbar()
            self.sizer.Add(self.toolbar, flag=wx.EXPAND)

        self.notebook = wx.Notebook(parent=self)
        self.sizer.Add(self.notebook, proportion=10, flag=wx.EXPAND)
        for targetstate in self.state['targets']:
            targetpage = self.AddTargetPage(targetstate)
        self.GetState().AddObserver(self.CheckNotebook)  # update tabs with state.

        self.Bind(wx.EVT_TOOL, self.OnAddTarget, self.toolbar.toolAdd)
        self.Bind(wx.EVT_TOOL, self.OnRenameTarget, self.toolbar.toolRename)
        self.Bind(wx.EVT_TOOL, self.OnDelTarget, self.toolbar.toolDelete)
        self.Bind(wx.EVT_TOOL, self.OnUndo, self.toolbar.toolUndo)
        self.Bind(wx.EVT_TOOL, self.OnRedo, self.toolbar.toolRedo)
        self.Bind(wx.EVT_TOOL, self.OnQuit, self.toolbar.toolQuit)
        self.Bind(wx.EVT_CLOSE, self.OnClose, self)

        crumb("+++ Notebook %r parent = %r" % (self.notebook, self.notebook.GetParent()))
        self.state.Checkpoint()
        self.Show(True)

    def OnAddTarget (self, *args):
        crumb("*** Add new target")
        target = self.GetState().MakeDefaultTarget()
        self.GetState()['targets'].append(target)
        crumb("state=%r" % dict(self.GetState()))
        targetpage = self.AddTargetPage(target)
        self.GetState().Checkpoint()

    def OnRenameTarget (self, *args):
        crumb("*** Rename current target")
        currtab = self.notebook.GetCurrentPage()
        currname = currtab.GetTargetState("name")
        idx = currtab.statekey[-1]
        dialog = wx.TextEntryDialog(self, message="Rename target machine %d" % idx, caption="Rename target", defaultValue=currname)
        commit = dialog.ShowModal()
        val = dialog.GetValue()
        if commit == wx.ID_OK:
            crumb("+++ Renaming %s" % (currtab.statekey,))
            idx = currtab.statekey[-1]  # final element, is numeric.
            self.notebook.SetPageText(idx, val)
            currtab.UpdateState('name', val)
        self.GetState().Checkpoint()

    def OnDelTarget (self, *args):
        crumb("*** Del current target")
        idx = self.notebook.GetSelection()
        del self.GetState()['targets'][idx]
        self.notebook.DeletePage(idx)
        # Resync and renumber tabs.
        for targetidx in xrange(0, len(self.state['targets'])):
            targetstate = self.state['targets'][targetidx]
            #self.tabs[targetidx].SetState(targetstate)
            self.notebook.SetPageText(targetidx, targetstate['name'])
            page = self.notebook.GetPage(targetidx)
            page.statekey = ('targets', targetidx)
            page.SetState(targetstate)
        self.GetState().Checkpoint()

    def OnUndo (self, *args):
        crumb("*** Undo")
        self.state.Rollback()
        for targetidx in xrange(0, len(self.state['targets'])):
            targetstate = self.state['targets'][targetidx]
            #self.tabs[targetidx].SetState(targetstate)
            self.notebook.GetPage(targetidx).SetState(targetstate)

    def OnRedo (self, *args):
        crumb("*** Redo")
        self.state.Rollforward()
        for targetidx in xrange(0, len(self.state['targets'])):
            targetstate = self.state['targets'][targetidx]
            #self.tabs[targetidx].SetState(targetstate)
            self.notebook.GetPage(targetidx).SetState(targetstate)

    def OnQuit (self, *args):
        crumb("*** QUITTING")
        self.Close(True)

    def OnClose(self, *args):
        self.GetState().Save()
        if threading.active_count() > 1:
            dlg = wx.MessageDialog(self, message="Active launch threads detected!  Force quit?", caption="Active threads", style=wx.YES_NO)
            response = dlg.ShowModal()
            if response != wx.ID_YES:
                return
            self.Destroy()
            raise Exception("Forceful Quit")
        self.Destroy()


    def UpdateTargetPage (self, idx):
        page = self.notebook.GetPage(idx)
        target = self.GetState()['targets'][idx]
        name = target['name']
        self.notebook.SetPageText(idx, name)
        page.SetState(target)
        return page

    def AddTargetPage (self, target_state):
        name = target_state['name']
        #idx = len(self.tabs)
        idx = self.notebook.GetPageCount()

        page = NaomiBooterPanel(parent=self.notebook, statekey=("targets", idx))
        self.notebook.AddPage(page, name)
        page.SetState(target_state)
        # Extend tabs collection
        #self.tabs = self.tabs + (page,)
        return page

    def CheckNotebook (self, state):
        crumb("+++ CheckNotebook")
        tabcount = self.notebook.GetPageCount()
        addcount = (len(self.GetState()['targets']) - tabcount)
        if addcount == 0:
            return
        elif addcount < 0:
            # Delete tabs.
            # drop 1 => -2; drop 2 => -3; drop 3 => -4
            if self.notebook.GetSelection() >= (tabcount + addcount):
                refocus = tabcount + addcount - 1
                if refocus < 0:
                    refocus = 0
                self.notebook.SetSelection(refocus)
            while addcount < 0:
                self.notebook.RemovePage(self.notebook.GetPageCount()-1)
                addcount += 1
        elif addcount > 0:
            # Add tabs.
            while addcount > 0:
                idx = self.notebook.GetPageCount()
                target = self.GetState()['targets'][idx]
                self.AddTargetPage(target)
                addcount -= 1
        # Resync tabs.
        for targetidx in xrange(0, len(self.state['targets'])):
            targetstate = self.state['targets'][targetidx]
            #self.tabs[targetidx].SetState(targetstate)
            self.notebook.SetPageText(targetidx, targetstate['name'])
            self.notebook.GetPage(targetidx).SetState(targetstate)

    def BuildToolbar (self):
        toolbar = NaomiBooterToolbar(self)
        return toolbar



if __name__ == "__main__":
    app = wx.App(False)
    frame = NaomiBooterWindow(None)
    app.MainLoop()

