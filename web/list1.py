#!/usr/bin/env python

import os, sys
#import naomi_weboot

#print("<html><body>Works Phase 1</body></html>")

def get_all_roms ():
    allfiles = os.listdir("../NaomiStuffs")
    romfiles = [ f for f in allfiles if f[-4:] == ".bin" ]
    return romfiles



def list_roms ():
    print('''
<html>
<head>Select ROM</head>
<body>
''')
#    print('''
#Naomi ROM:
#<select name="rom">
#''')

    romlist = get_all_roms()
    romlist.sort()

#    for f in romlist:
#        print('''<option value="%s">%s</option>''' % (f, f))
#    print('''
#</select>
#''')
#
#    print("<br/><br/>")

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


def load_rom (rompath):
    print("<html><body>Loading ROM '%s'...<br/>" % rompath)
    sys.stdout.flush()

    localpath = "../NaomiStuffs/%s" % rompath
#    naomi_weboot.upload(localpath)
    os.system("python2 ../naomi_boot.py '%s'" % localpath)

    print("<br/>Finished.<br/>")
    print("</body></html>")
    return



def main ():
    pathinfo = os.getenv("PATH_INFO")
    romlist = get_all_roms()
    if pathinfo:
        rompath = pathinfo[1:]
        if rompath in romlist:
            print("load_rom '%s'" % rompath)
            load_rom(rompath)
            return 0
    # pathinfo not recognized, or not given.
    list_roms()
    return 0


if __name__ == "__main__":
    main()

