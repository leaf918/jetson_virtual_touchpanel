import os
import gi
import subprocess
import time
import threading
import re
import sys
import multiprocessing as mp
import zmq
import vtouch as vt

zmq_host = "127.0.0.1"
zmq_port = "5001"

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify
from gi.repository import GObject

INDICATOR_ID = 'vtouchindicator'
SELF_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DEFAULT = os.path.join(SELF_DIR, 'assets/icons/icon_vtouch.svg')

evt_queue = mp.Queue()
last_timestamp = mp.Value('d', time.time())
framerate = mp.Value('i', 0)

def quit(_):
    running.clear()
    proc_subscriber.terminate()
    evt_queue.put(None)
    gtk.main_quit()

def build_menu():
    menu = gtk.Menu()
    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)

    menu.show_all()
    return menu

def trtpose_subscriber(running, last_timestamp, framerate):
    print("--- Subscriber thread ---")

    frame_number = 0 # number of message recived in the last 1 sec interval

    # Creates a socket instance
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # Connects to a bound socket
    socket.connect("tcp://{}:{}".format(zmq_host, zmq_port))

    # Subscribes to all topics
    socket.subscribe("")

    while True:

        # Receives a string format message
        msg_string = socket.recv_string() 
        cur_timestamp = time.time()
        print(msg_string + " (received at " + str(cur_timestamp) + ")")

        if (cur_timestamp % 1.0 < last_timestamp.value % 1.0):
            framerate = frame_number
            print("framerate = " + str(framerate))
            frame_number = 0
        else:
            frame_number += 1

        last_timestamp.value = cur_timestamp

def trtpose_monitor(running, last_timestamp):
    print("--- Monitor process ---")
    trtpose_active = False
    while running.is_set():
        cur_timestamp = time.time()
        #print("cur: " + str(cur_timestamp) + ", last_timestamp: " + str(last_timestamp.value))
        if cur_timestamp - last_timestamp.value > 0.5:
            if trtpose_active == True:
                print("trt_pose stopped")
            trtpose_active = False
        else:
            if trtpose_active == False:
                print("trt_pose started")
            trtpose_active = True
        update_icon(trtpose_active)
        do_notify(trtpose_active)
        time.sleep(0.5)

def check_trtpose_activity():
    threading.Timer(1.0, check_trtpose_activity).start()
    print("Hello, World!" +  str(time.time()))

def update_icon(status):
    if(status):
        indicator.set_icon(os.path.join(SELF_DIR, 'assets/icons/icon_vtouch.svg'))
    else:
        indicator.set_icon(os.path.join(SELF_DIR, 'assets/icons/icon_vtouch_inactive.svg'))

def do_notify(status):
    msg_lines = []
    if(status):
        msg_lines.append(f"Service 'trt_pose' started")
    else:
        msg_lines.append(f"Service 'trt_pose' stopped")
    msg = '\n'.join(msg_lines)
    notification.update(msg)
    notification.show()

model = vt.vtouch()

indicator = appindicator.Indicator.new(INDICATOR_ID, ICON_DEFAULT, appindicator.IndicatorCategory.SYSTEM_SERVICES)
indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
indicator.set_menu(build_menu())

notify.init(INDICATOR_ID)
notification = notify.Notification()

running = threading.Event()
running.set()

proc_subscriber = mp.Process(target=trtpose_subscriber, args=(running, last_timestamp, framerate))
proc_subscriber.start()
thrd_monitor = threading.Thread(target=trtpose_monitor, args=(running, last_timestamp))
thrd_monitor.start()

gtk.main()





