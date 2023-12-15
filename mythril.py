# TODO: Add direct playing from youtube
# https://stackoverflow.com/a/8775928
# https://stackoverflow.com/a/49354406

from math import ceil, floor
from time import sleep
from sys import exit as sysexit
import random, os, threading, pygame
from pygame import mixer, USEREVENT
import dearpygui.dearpygui as dpg
from mutagen.mp3 import MP3

currentPos = 0
tags = []
queue = []
playing = False
paused = False
currentBank = ""
loop = False
fade = False
SONGEND = USEREVENT+1
currentSong = ""
alive = True
shuffle = False
songLength = -1
wantToSwap = False

# Helper function to show a status message in the status bar
def show_message(msg):
    dpg.set_value("status",msg)

# Forward button
def forward_button(autoplay=False):
    global currentBank
    global currentSong
    global wantToSwap
    wantToSwap = False
    global playing
    playing = False
    global paused
    paused = False
    if not loop:
        current_bank_items = dpg.get_item_user_data(currentBank+"List")
        index = current_bank_items.index(currentSong)
        # Either increments the index by one or shuffles it, depending on the setting
        if not shuffle:
            if (index + 1) > len(current_bank_items)-1:
                index = 0
            else:
                index += 1
        else:
            index = random.randrange(0, len(current_bank_items)-1)
        new_song = current_bank_items[index]
        dpg.set_value(currentBank+"List",new_song)
        currentSong = new_song
        dpg.configure_item("mythrilPlay",label="Play")
        if autoplay:
            playPauseButton()

# Back Button, same thing as forward button but in reverse
def back_button():
    global currentBank
    global currentSong
    global wantToSwap
    global playing
    playing = False
    global paused
    paused = False
    wantToSwap = False
    mixer.music.unload()
    mixer.music.stop()
    current_bank_items = dpg.get_item_user_data(currentBank+"List")
    index = current_bank_items.index(currentSong)

    if (index - 1) < 0:
        index = len(current_bank_items)-1
    else:
        index -= 1
    new_song = current_bank_items[index]
    dpg.set_value(currentBank+"List",new_song)
    #playPauseButton()
    currentSong = new_song
    dpg.configure_item("mythrilPlay",label="Play") 

# Plays the song by handling loading it and volume change and such
def playSong():
    global queue
    global currentPos
    global playing
    global currentBank
    global currentSong
    global songLength
    global wantToSwap
    try:
        currentSong = dpg.get_value(currentBank+"List")
        mixer.music.unload()
        # Loads the music and plays it
        mixer.music.load('mythril/'+currentBank+'/'+currentSong)
        mixer.music.set_endevent(SONGEND)
        vol_change()
        song = MP3('mythil/'+currentBank+'/'+currentSong)
        songLength = song.info.length*1000
        mixer.music.play(fade_ms=(int(fade)*1000))
        wantToSwap = True

    except Exception as e:
        show_message("Error: No songs are loaded.")
        print(e)

# Play pause button
def playPauseButton():
    try:
        global playing
        global paused
        global currentPos
        if not playing:
            playing = True
            if paused:
                mixer.music.unpause()
                paused = False
                show_message("Now playing: " + currentSong)
            else:
                mixer.music.unload()
                playSong()
                show_message("Now playing: " + currentSong)
            dpg.set_item_label("mythrilPlay","Pause")
        else:
            playing = False
            paused = True
            mixer.music.pause()
            dpg.set_item_label("mythrilPlay","Play")
            show_message("Paused")
    except Exception:
        show_message("Cannot play, no songs are loaded.")

# Monitors volume change
def vol_change():
    mixer.music.set_volume(dpg.get_value("mythrilVol")/100)

# Handles selecting a song bank to play from
def select_bank(sender=""):
    global paused
    paused = False
    global playing
    playing = False
    global currentBank
    global currentSong
    global wantToSwap
    wantToSwap = False
    if fade:
        show_message("Fading Song...")
        mixer.music.fadeout(1000)
    else:
        mixer.music.stop()
    mixer.music.unload()
    dpg.set_item_label("mythrilPlay","Play")
    if not currentBank == "":
        dpg.configure_item(currentBank+"Text",color=(255,0,0,255))
    item = sender.split("Button")
    currentBank = item[0]
    current_bank_items = dpg.get_item_user_data(currentBank+"List")
    dpg.configure_item(item[0]+"Text",color=(0,255,0,255))
    show_message("Selected bank: " + currentBank)
    currentSong = current_bank_items[0]

# check_status thread that monitors for the end of a song
def check_status():
    global playing
    global paused
    global alive
    pygame.init()
    while alive:
        sleep(0.1)
        try:
            if playing:
                dpg.set_value("mythrilSeek",pygame.mixer.music.get_pos())
                dpg.configure_item("mythrilSeek",max_value=songLength)
            else:
                dpg.set_value("mythrilSeek",-1)
        except Exception:
            pass

        for event in pygame.event.get():
            if event.type == SONGEND and wantToSwap:
                playing = False
                paused = False
                try:
                    mixer.music.unload()
                except Exception:
                    pass
                if not loop:
                    forward_button(autoplay=True)
                else:
                    playPauseButton()

# Destroy function, common to all modules
def destroy():
    global t1
    global alive
    global groups
    global tags
    mixer.quit()
    for group in groups:
        dpg.delete_item(group)
    groups = []
    tags = []
    dpg.delete_item("mythril")
    alive = False
    t1.join()
    print(t1.is_alive())

def check_folder(folder_name: str, create_folder: bool = True, list_folder: bool = True) -> list[str] | None:
    if not os.path.isdir(folder_name):
        if not create_folder:
            return None
        else:
            try:
                os.mkdir(folder_name)
            except Exception:
                return None
            return os.listdir(folder_name)
    else:
        if (list_folder):
            return os.listdir(folder_name)

# Helper variable functions
def flip_fade():
    global fade 
    fade = not fade
def flip_loop():
    global loop
    loop = not loop
def flip_shuffle():
    global shuffle
    shuffle = not shuffle

# Automatically swaps the bank if an item is selected in the listbox
def swap_song(sender):
    global wantToSwap
    global currentSong
    wantToSwap = False
    currentSong = dpg.get_value(sender)
    select_bank(sender.split("List")[0])

# Main function
def show_window(show=False):
    global tags
    global currentBank
    global fade
    global groups

    mixer.init()
    # Creates the monitor thread and starts it
    global t1
    t1 = threading.Thread(target=check_status,args=(),daemon=True)
    t1.start()

    # Loads categories
    folders = check_folder("mythril")
    for tag in folders:
        if tag.find(".") == -1:
            tags.append(tag)

    with dpg.window(label="Mythril",tag="mythril",show=show,autosize=True,on_close=destroy):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Back",callback=back_button)
            dpg.add_button(label="Play",tag="mythrilPlay",callback=playPauseButton)
            dpg.add_button(label="Forward",callback=forward_button)
        dpg.add_slider_int(tag="mythrilVol",clamped=True,default_value=50,callback=vol_change)
        dpg.add_slider_float(tag="mythrilSeek",clamped=True,no_input=True)
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Fade Between Songs",callback=flip_fade)
            dpg.add_checkbox(label="Loop Current Song",callback=flip_loop)
            dpg.add_checkbox(label="Shuffle",callback=flip_shuffle)

        width = 2
        total_length = len(tags)
        # Calculaltes how many rows are needed with given length
        rows = ceil(total_length / width)

        # Creates groups to put buttons
        groups = []
        for i in range(rows):
            parentGroups = dpg.add_group(horizontal=True)
            groups.append(parentGroups)

        # Adds listboxes to each row, overflows to next row if space is needed
        for i in range(total_length):
            notLabel = tags[i]
            currentRow = floor(i/(width))
            parentGroup = groups[currentRow]
            dpg.add_group(tag=notLabel,parent=parentGroup,horizontal=False)
            dpg.add_text(notLabel,parent=notLabel,color=(255,0,0,255),tag=notLabel+"Text")
            tag_songs = []
            for song in os.listdir("mythril/"+notLabel):
                tag_songs.append(song)
            dpg.add_listbox(tag_songs,parent=notLabel,tag=(notLabel+"List"),user_data=tag_songs)
            dpg.add_button(label="Select",parent=notLabel,tag=(notLabel+"Button"),callback=select_bank)

        dpg.add_text("HELP",tag="status")
        # Tries to load first bank
        try:
            select_bank(tags[0])
        except Exception:
            show_message("No Banks Found. Verify folder structure and try again.")

dpg.create_context()
dpg.create_viewport(title='Mythril', width=700, height=600)
show_window(True)
dpg.set_primary_window("mythril",True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
destroy()
sysexit()
