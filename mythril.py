"""Mythril"""
from sys import exit as sysexit
from threading import Thread
from random import randrange
from math import ceil, floor
from time import sleep
import os, pygame
from pygame import mixer, USEREVENT
import dearpygui.dearpygui as dpg
from mutagen.mp3 import MP3

SONGEND = USEREVENT+1
class Status:
    """General Global Vars"""
    # Bank Vault
    tags = []
    groups = []

    # Program Status
    playing = False
    paused = False
    currentBank = ""
    currentSong = ""
    wantToSwap = False
    tracking = True
    songLength = -1
    fakePos = 0
    offset = 0
    realPos = 0

    # Settings
    loop = False
    fade = False
    shuffle = False
    auto = False

    # Thread Information
    t1 = None
    t1alive = True

def show_message(msg):
    """Helper function to show a status message in the status bar"""
    dpg.set_value("status",msg)

def forward_button(autoplay=False):
    """Forward button handler"""
    Status.wantToSwap = False
    Status.playing = False
    Status.paused = False
    if not Status.loop:
        current_bank_items = dpg.get_item_user_data(Status.currentBank+"List")
        index = current_bank_items.index(Status.currentSong)
        # Either increments the index by one or shuffles it, depending on the setting
        if not Status.shuffle:
            if (index + 1) > len(current_bank_items)-1:
                index = 0
            else:
                index += 1
        else:
            index = randrange(0, len(current_bank_items)-1)
        new_song = current_bank_items[index]
        dpg.set_value(Status.currentBank+"List",new_song)
        Status.currentSong = new_song
        dpg.configure_item("mythrilPlay",label="Play")
        if autoplay:
            play_pause_button()

def back_button():
    """Back Button Handler"""
    Status.playing = False
    Status.paused = False
    Status.wantToSwap = False
    mixer.music.unload()
    mixer.music.stop()
    current_bank_items = dpg.get_item_user_data(Status.currentBank+"List")
    index = current_bank_items.index(Status.currentSong)

    if (index - 1) < 0:
        index = len(current_bank_items)-1
    else:
        index -= 1
    new_song = current_bank_items[index]
    dpg.set_value(Status.currentBank+"List",new_song)
    #play_pause_button()
    Status.currentSong = new_song
    dpg.configure_item("mythrilPlay",label="Play")

def play_song():
    """Plays the song by handling loading it and volume change and such"""
    try:
        Status.currentSong = dpg.get_value(Status.currentBank+"List")
        mixer.music.unload()
        # Loads the music and plays it
        mixer.music.load('mythril/'+Status.currentBank+'/'+Status.currentSong)
        mixer.music.set_endevent(SONGEND)
        vol_change()
        song = MP3('mythril/'+Status.currentBank+'/'+Status.currentSong)
        Status.songLength = song.info.length
        mixer.music.play(fade_ms=int(Status.fade)*1000)
        Status.wantToSwap = True
    except Exception as e:
        show_message("Error: No songs are loaded.")
        print(e)

def play_pause_button():
    """Play Pause Button Handler"""
    try:
        if not Status.playing:
            Status.playing = True
            if Status.paused:
                mixer.music.unpause()
                Status.paused = False
                show_message("Now playing: " + Status.currentSong)
            else:
                mixer.music.unload()
                play_song()
                show_message("Now playing: " + Status.currentSong)
            dpg.set_item_label("mythrilPlay","Pause")
        else:
            Status.playing = False
            Status.paused = True
            mixer.music.pause()
            dpg.set_item_label("mythrilPlay","Play")
            show_message("Paused")
    except Exception:
        show_message("Cannot play, no songs are loaded.")

def vol_change():
    """Volume Changer Helper"""
    mixer.music.set_volume(dpg.get_value("mythrilVol")/100)

def select_bank(sender=""):
    """Handles selecting a song bank to play from"""
    Status.paused = False
    Status.playing = False
    Status.wantToSwap = False
    Status.offset = 0
    if Status.fade:
        show_message("Fading Song...")
        mixer.music.fadeout(1000)
    else:
        mixer.music.stop()
    mixer.music.unload()
    dpg.set_item_label("mythrilPlay","Play")
    if Status.currentBank != "":
        dpg.configure_item(Status.currentBank+"Text",color=(255,0,0,255))
    item = sender.split("Button")
    Status.currentBank = item[0]
    current_bank_items = dpg.get_item_user_data(Status.currentBank+"List")
    dpg.configure_item(item[0]+"Text",color=(0,255,0,255))
    show_message("Selected bank: " + Status.currentBank)
    Status.currentSong = current_bank_items[0]
    if Status.auto:
        play_song()

def status_thread():
    """status_thread thread that monitors for the end of a song"""
    while Status.t1alive:
        sleep(0.1)
        try:
            if Status.playing and Status.tracking:
                Status.fakePos = mixer.music.get_pos()/1000
                Status.realPos = Status.fakePos + Status.offset
                dpg.set_value("mythrilSeek",Status.realPos)
                dpg.configure_item("mythrilSeek",max_value=Status.songLength)
            else:
                dpg.set_value("mythrilSeek",0)
        except Exception:
            pass

        for event in pygame.event.get():
            if event.type == SONGEND and Status.wantToSwap:
                Status.playing = False
                Status.paused = False
                Status.offset = 0
                try:
                    mixer.music.unload()
                except Exception:
                    pass
                if not Status.loop:
                    forward_button(autoplay=True)
                else:
                    play_pause_button()

def destroy():
    """Gracefully kills Mythril"""
    Status.t1alive = False
    Status.t1.join()
    mixer.quit()
    pygame.quit()

def check_folder(folder_name: str, create_folder: bool = True) -> list[str] | None:
    """Checks to make sure a folder exists"""
    if not os.path.isdir(folder_name):
        if not create_folder:
            return None
        try:
            os.mkdir(folder_name)
        except Exception:
            return None
    return os.listdir(folder_name)

def flip_fade():
    """Toggles Fade"""
    Status.fade = not Status.fade
def flip_loop():
    """Toggles Loop"""
    Status.loop = not Status.loop
def flip_shuffle():
    """Toggles Shuffle"""
    Status.shuffle = not Status.shuffle
def flip_auto():
    """Toggles Auto"""
    Status.auto = not Status.auto

def swap_song(sender):
    """Automatically swaps the bank if an item is selected in the listbox"""
    Status.wantToSwap = False
    Status.currentSong = dpg.get_value(sender)
    select_bank(sender.split("List")[0])

def seek_clicked():
    """Checks if mythrilSeek is clicked"""
    if dpg.is_item_edited("mythrilSeek"):
        # Disable automatic display
        Status.tracking = False

        # Store the offset of the seek change into Status.offset
        # This is needed because mixer.music.get_pos() only reports the total time a song has been playing excluding set_pos() changes
        # (https://www.pygame.org/docs/ref/music.html#pygame.mixer.music.get_pos)
        Status.offset = dpg.get_value("mythrilSeek") - mixer.music.get_pos()/1000
        mixer.music.set_pos(dpg.get_value("mythrilSeek"))
    else:
        Status.tracking = True

def show_window():
    """Main"""

    # Creates the monitor thread and starts it
    Status.t1 = Thread(target=status_thread,args=(),daemon=True)
    Status.t1.start()

    # Loads categories
    folders = check_folder("mythril")
    for tag in folders:
        if tag.find(".") == 0 or tag.find("_") == 0:
            continue
        else: 
            Status.tags.append(tag)

    # Creates a handler for the seek bar
    # drag_callback and drop_callback seems to be broken for sliders
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(callback=seek_clicked)
        dpg.add_mouse_move_handler(callback=seek_clicked)
        dpg.add_mouse_release_handler(callback=seek_clicked)

    with dpg.window(label="Mythril",tag="mythril",autosize=True,on_close=destroy):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Back",callback=back_button)
            dpg.add_button(label="Play",tag="mythrilPlay",callback=play_pause_button)
            dpg.add_button(label="Forward",callback=forward_button)
        dpg.add_slider_int(tag="mythrilVol",clamped=True,default_value=50,callback=vol_change)
        dpg.add_slider_float(tag="mythrilSeek",clamped=True,no_input=True)
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Fade Between Songs",callback=flip_fade,tag="Tfbs")
            with dpg.tooltip("Tfbs"):
                dpg.add_text("Fade between songs when a song ends and a bank is switched")
            dpg.add_checkbox(label="Loop Current Song",callback=flip_loop,tag="Tlcs")
            with dpg.tooltip("Tlcs"):
                dpg.add_text("Loops the currently selected song")
            dpg.add_checkbox(label="Shuffle",callback=flip_shuffle,tag="Ts")
            with dpg.tooltip("Ts"):
                dpg.add_text("Shuffles the bank")
            dpg.add_checkbox(label="Auto",callback=flip_auto,tag="Ta")
            with dpg.tooltip("Ta"):
                dpg.add_text("Automatically plays the song in the bank when switching to it")

        width = 2
        total_length = len(Status.tags)
        # Calculaltes how many rows are needed with given length
        rows = ceil(total_length / width)

        # Creates groups to put buttons
        for i in range(rows):
            parent_groups = dpg.add_group(horizontal=True)
            Status.groups.append(parent_groups)

        # Adds listboxes to each row, overflows to next row if space is needed
        for i in range(total_length):
            not_label = Status.tags[i]
            current_row = floor(i/(width))
            parent_group = Status.groups[current_row]
            dpg.add_group(tag=not_label,parent=parent_group,horizontal=False)
            dpg.add_text(not_label,parent=not_label,color=(255,0,0,255),tag=not_label+"Text")
            tag_songs = []
            for song in os.listdir("mythril/"+not_label):
                tag_songs.append(song)
            dpg.add_listbox(tag_songs,parent=not_label,tag=(not_label+"List"),user_data=tag_songs)
            dpg.add_button(label="Select",parent=not_label,tag=(not_label+"Button"),
                           callback=select_bank)

        dpg.add_text("Loading",tag="status")

        # Tries to load the first bank
        try:
            select_bank(Status.tags[0])
        except Exception:
            show_message("No Banks Found. Verify folder structure and try again.")

# Required for the event system from pygame
pygame.init()
mixer.init()
dpg.create_context()
dpg.create_viewport(title='Mythril', width=700, height=600)
show_window()
dpg.set_primary_window("mythril",True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
destroy()
sysexit()
