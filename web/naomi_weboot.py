#!/usr/bin/env python

import os, sys
import os.path
import time

import pynaomi


class NaomiWebToolbox (pynaomi.NaomiToolbox):
    def __init__ (self):
        pynaomi.NaomiToolbox.__init__(self)
        self.total = 0

    def emitstatus (self, msg):
#        print('''<pre>STATUS: %s</pre>''' % msg)
        sys.stdout.flush()
        return

    def emitprogress (self, val):
        if self.total:
            percent = 100. * val / self.total
#            print('''<pre>%d%%</pre>''' % int(percent))
            print('''<script>set_upload_tag("%d%%");</script>''' % percent)
        else:
#            print('''<pre>PROGRESS %08x</pre>''' % val)
            print('''<script>set_upload_tag("%08x");</script>''' % val)
        sys.stdout.flush()
        return

#    def connect (self, *args):
#        self.emitstatus("faking connection")
#    def HOST_SetMode (self, *args):
#        self.emitstatus("faking host mode")
#    def SECURITY_SetKeycode (self, *args):
#        self.emitstatus("faking set keycode")
#    def DIMM_UploadFile(self, romfile):
#        self.emitstatus("faking upload romfile")
#        for i in range(0,16):
#            self.emitprogress(i*252144)
#            time.sleep(.5)
#    def HOST_Restart(self, *args):
#        self.emitstatus("faking restart host")
#        raise Exception("faked")
#    def close (self, *args):
#        self.emitstatus('faking close socket')


class NaomiWeboot (object):
    ROM_DIR = "../NaomiStuffs"

    def __init__ (self):
        self.romfiles = []
        #self.toolbox = pynaomi.NaomiToolbox()
        self.toolbox = NaomiWebToolbox()

#print("<html><body>Works Phase 1</body></html>")

    def get_all_roms (self):
        allfiles = os.listdir("../NaomiStuffs")
        self.romfiles = [ f for f in allfiles if f[-4:] == ".bin" ]
        return self.romfiles


    def list_roms (self):
        print('''Content-type: text/html

<html>
<head>Select ROM</head>
<body>
''')

        romlist = self.get_all_roms()
        romlist.sort()

        print('''<ul>''')
        for f in romlist:
            href = "%s/%s" % (os.getenv("SCRIPT_NAME"), f)
            print('''<li><a href="%s">%s</a></li>''' % (href,f))
        print('''</ul>''')
        print('''
</body>
</html>
''')
        return


    def load_rom (self, rompath):
        print("""Content-type: text/html

""")
#        print("<html><body>Loading ROM '%s'...<br/>" % rompath)
        print("<h3>Loading ROM '%s'...</h3>" % rompath)
        print('''<html>
<head>
<title>Loading Naomi ROM</title>
<style>
.pending {
  background: silver;
}

.inprogress {
  background: yellow;
}

.completed {
  background: green;
}

.failed {
  background: red;
}

tr {
  text-align: center;
}

</style>
</head>
''')
        print('''
<body>
<script>

activeStage = null;

function set_active_progress (tag) {
//  document.writeln("set active progress " + tag + ";");
  eltid = "progress_" + activeStage;
  elt = document.getElementById(eltid);
  elt.innerHTML = tag;
}

function activate_stage (stageid) {
  if (activeStage) {
    // Set previous to 'complete'
    set_active_progress("OK");
    eltid = "row_" + activeStage;
    elt = document.getElementById(eltid)
    if (elt) {
      elt.className = "completed";
    }
  }

//  document.writeln("activating stage");
  activeStage = stageid;
  eltid = "row_" + stageid;
  elt = document.getElementById(eltid);
  if (elt) {
    elt.className = "inprogress";
  }
  set_active_progress("IN PROGRESS")
}

function failed_stage () {
  set_active_progress("FAILED")
  eltid = "row_" + activeStage;
  elt = document.getElementById(eltid);
  elt.className = 'failed';
}

function set_romname (romname) {
  eltid = "stage_romid";
  elt = document.getElementById(eltid);
  elt.innerHTML = "ROM=" + romname;
}

function set_conninfo (addrspec) {
//  document.writeln("set_conninfo " + addrspec);
  eltid = "stage_conn";
  elt = document.getElementById(eltid);
  elt.innerHTML = "Connecting " + addrspec;
}

function set_upload_tag (tag) {
  eltid = "progress_upload";
  elt = document.getElementById(eltid);
  //elt.innerHTML = tag;
  if (tag.indexOf("%") > -1) {
    elt.innerHTML = "<div style='width: 100%; position: relative; display: block;'><span style='width: " + tag + "%; background: green; display: block;'>" + tag + "</span></div>";
  } else {
    elt.innerHTML = tag;
  }
}

</script>

<table border=1 cellspacing=0 width="100%">
<tr><th width="80%">STAGE</th><th>PROGRESS</th></tr>
<tr id="row_romid" class="pending"><td id="stage_romid">ROM=</td><td id="progress_romid">-</td></tr>
<tr id="row_conn" class="pending"><td id="stage_conn">Connecting ...</td><td id="progress_conn">-</td><tr>
<tr id="row_loading" class="pending"><td id="stage_loading">&quot;Now Loading&quot;</td><td id="progress_loading">PENDING</td></tr>
<tr id="row_key" class="pending"><td id="stage_key">Keycode Zeroing</td><td id="progress_key">PENDING</td></tr>
<tr id="row_upload" class="pending"><td id="stage_upload">Uploading</td><td id="progress_upload">PENDING</td></tr>
<tr id="row_restart" class="pending"><td id="stage_restart">Restarting host</td><td id="progress_restart">PENDING</td></tr>
<tr id="row_wrapup" class="pending"><td id="stage_wrapup">Finishing</td><td id="progress_wrapup">PENDING</td></tr>
</table>
</body>
''')
        sys.stdout.flush()
#        print("<br/>Finished.<br/>")
        print("</body></html>")

        print('''<script>set_romname("%s"); activate_stage("romid");</script>''' % rompath)
        #localpath = "../NaomiStuffs/%s" % rompath
        localpath = os.path.join(self.ROM_DIR, rompath)
#        os.system("python2 ../naomi_boot.py '%s'" % localpath)
#        naomi_weboot.upload(localpath)
        romsize = os.path.getsize(localpath)
        romfile = open(localpath, "rb")
        self.toolbox.total = romsize

        try:
            # Open connection.
            print('''<script>set_conninfo("%s:%s"); activate_stage("conn");</script>''' % (self.toolbox.addr, self.toolbox.port))
            self.toolbox.connect()

            # display "NOW LOADING"
            print('''<script>activate_stage("loading");</script>''')
            self.toolbox.HOST_SetMode(0,1)

            # disable encryption.
            print('''<script>activate_stage("key");</script>''')
            self.toolbox.SECURITY_SetKeycode(None)

            # upload file.
            print('''<script>activate_stage("upload");</script>''')
            self.toolbox.DIMM_UploadFile(romfile)

            # restart host.
            print('''<script>activate_stage("restart");</script>''')
            self.toolbox.HOST_Restart()

            print('''<script>activate_stage("wrapup");</script>''')
            self.toolbox.close()

            print('''<script>activate_stage(null); document.writeln("<pre>FINISHED</pre>");</script>''')
        except:
            print('''<script>failed_stage();</script>''');
            raise

        return



    def main (self):
        pathinfo = os.getenv("PATH_INFO")
        romlist = self.get_all_roms()
        if pathinfo:
            rompath = pathinfo[1:]
            if rompath in romlist:
                #print("load_rom '%s'" % rompath)
                self.load_rom(rompath)
                return 0
        # pathinfo not recognized, or not given.
        self.list_roms()
        return 0


if __name__ == "__main__":
    cgi = NaomiWeboot()
    cgi.main()

