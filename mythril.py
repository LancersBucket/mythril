"""Mythril"""
from sys import exit as sys_exit
from threading import Thread
from random import randrange
from math import ceil, floor
from time import sleep
import os
import pygame
from pygame import mixer, USEREVENT
import dearpygui.dearpygui as dpg
from mutagen.mp3 import MP3

VERSION = "v0.0.1"
SONGEND = USEREVENT+1
class Status:
    """General Global Vars"""
    # Bank Vault
    folder_groups = []
    bank_groups = []

    # Program Status
    playing = False
    paused = False
    current_bank = ""
    current_song = ""
    current_song_length = -1

    # Rewind and skip forward handling
    seek_fake_position = 0
    seek_offset = 0
    seek_real_position = 0

    # Settings
    loop = False
    fade = False
    shuffle = False
    auto = False

    # Thread Information
    t1 = None
    t1_keepalive = True
    t1_ready_to_swap = False
    t1_seek_pos_update = True

class Color:
    """Color Vars"""
    NEUTRAL = (255,255,255,255)
    WARNING = (232,177,48,255)
    ERROR = (255,0,0,255)

def show_message(msg: str, color: tuple=(255,255,255,255)) -> None:
    """Helper function to show a status message in the status text with optional color value"""
    dpg.set_value("status",msg)
    dpg.configure_item("status",color=color)

def forward_button(autoplay=False):
    """Forward button handler"""
    Status.t1_ready_to_swap = False
    Status.playing = False
    Status.paused = False

    # Checks if it set to loop, and if not, go to the next song
    if not Status.loop:
        current_bank_items = dpg.get_item_user_data(Status.current_bank+"List")
        index = current_bank_items.index(Status.current_song)
        # Either increments the index by one or shuffles it, depending on the setting
        if not Status.shuffle:
            if (index + 1) > len(current_bank_items)-1:
                index = 0
            else:
                index += 1
        else:
            index = randrange(0, len(current_bank_items)-1)
        new_song = current_bank_items[index]
        dpg.set_value(Status.current_bank+"List",new_song)
        Status.current_song = new_song
        dpg.configure_item("mythrilPlay",label="Play")
        if autoplay:
            play_pause_button()

def back_button():
    """Back Button Handler"""
    Status.playing = False
    Status.paused = False
    Status.t1_ready_to_swap = False

    mixer.music.set_endevent()
    mixer.music.stop()
    mixer.music.unload()
    current_bank_items = dpg.get_item_user_data(Status.current_bank+"List")
    index = current_bank_items.index(Status.current_song)

    if (index - 1) < 0:
        index = len(current_bank_items)-1
    else:
        index -= 1

    new_song = current_bank_items[index]
    dpg.set_value(Status.current_bank+"List",new_song)
    Status.current_song = new_song
    dpg.configure_item("mythrilPlay",label="Play")

def __play_song():
    """Plays the song by handling loading it and volume change and such; Returns 1 if success"""
    try:
        Status.current_song = dpg.get_value(Status.current_bank+"List")
        if Status.current_song == "":
            raise OSError(f"No Songs Found In Bank {Status.current_bank}")
        mixer.music.unload()
        # Loads the music and plays it
        mixer.music.load(f"mythril/{Status.current_bank}/{Status.current_song}")
        mixer.music.set_endevent(SONGEND)
        vol_change()
        song = MP3(f"mythril/{Status.current_bank}/{Status.current_song}")
        Status.current_song_length = song.info.length
        mixer.music.play(fade_ms=int(Status.fade)*1000)
    except OSError as e:
        show_message(f"Error: No songs are loaded in bank '{Status.current_bank}'.",Color.ERROR)
        print(e)
        return -1
    except Exception as e:
        if str(e).startswith("ModPlug_Load"):
            show_message(f"Failed to load song: {e}\n(Not an mp3 file?)",Color.ERROR)
            print(e)
            return -1
        show_message(str(e),Color.ERROR)
        print(e)
        return -1
    finally:
        Status.t1_ready_to_swap = True

    return 1

def play_pause_button():
    """Play Pause Button Handler"""
    try:
        if not Status.playing:
            if Status.paused:
                mixer.music.unpause()
                Status.paused = False
            else:
                mixer.music.unload()
                worked = __play_song()
                if worked == -1:
                    return

            show_message(f"Now playing: {Status.current_song}")
            Status.playing = True
            dpg.set_item_label("mythrilPlay","Pause")
        else:
            Status.playing = False
            Status.paused = True
            mixer.music.pause()
            dpg.set_item_label("mythrilPlay","Play")
            show_message("Paused")
    except Exception:
        show_message("Cannot play, no songs are loaded.", Color.ERROR)

def vol_change():
    """Volume Changer Helper"""
    mixer.music.set_volume(dpg.get_value("mythrilVol")/100)

def select_bank(sender=""):
    """Handles selecting a song bank to play from"""
    Status.paused = False
    Status.playing = False
    Status.t1_ready_to_swap = False
    Status.seek_offset = 0

    # Clear the endevent so t1 doesn't fire when the song is stopped
    # Prevents skipping forward one song when selecting a new bank
    mixer.music.set_endevent()

    if Status.fade:
        show_message("Fading Song...")
        mixer.music.fadeout(1000)
    else:
        mixer.music.stop()
    mixer.music.unload()
    dpg.set_item_label("mythrilPlay","Play")
    if Status.current_bank != "":
        dpg.configure_item(Status.current_bank+"Text",color=(255,0,0,255))
    item = sender.split("Button")
    Status.current_bank = item[0]
    current_bank_items = dpg.get_item_user_data(Status.current_bank+"List")
    dpg.configure_item(item[0]+"Text",color=(0,255,0,255))
    try:
        Status.current_song = current_bank_items[0]
    except Exception:
        show_message(f"Selected bank: {Status.current_bank}\nWarning: Bank is empty.", Color.WARNING)
        return

    show_message(f"Selected bank: {Status.current_bank}")
    if Status.auto:
        play_pause_button()

def status_thread() -> None:
    """Status thread thread that monitors for the end of a song"""
    while Status.t1_keepalive:
        sleep(0.1)
        try:
            # While the song is playing, update the seekbar to the current time
            if Status.playing and Status.t1_seek_pos_update:
                Status.seek_fake_position = mixer.music.get_pos()/1000
                Status.seek_real_position = Status.seek_fake_position + Status.seek_offset
                dpg.set_value("mythrilSeek",Status.seek_real_position)
                dpg.configure_item("mythrilSeek",max_value=Status.current_song_length)
        except Exception:
            pass

        for event in pygame.event.get():
            # If the songend event has fired, unload the song and go to the next one
            if event.type == SONGEND and Status.t1_ready_to_swap:
                Status.playing = False
                Status.paused = False
                Status.seek_offset = 0
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
    # Stop t1 thread loop and join it to the main process to terminiate it
    Status.t1_keepalive = False
    Status.t1.join()

    mixer.quit()
    pygame.quit()

def check_folder(folder_name: str, create_folder: bool = True) -> list[str] | None:
    """Checks to make sure a folder exists and returns it's contents. If not, optionally create it"""
    if not os.path.isdir(folder_name):
        if not create_folder:
            return None
        try:
            os.mkdir(folder_name)
        except Exception as e:
            print(e)
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
    Status.t1_ready_to_swap = False
    Status.current_song = dpg.get_value(sender)
    select_bank(sender.split("List")[0])

def seek_clicked():
    """Checks if mythrilSeek is clicked"""
    if dpg.is_item_edited("mythrilSeek"):
        # Disable automatic display
        Status.t1_seek_pos_update = False

        # Store the offset of the seek change into Status.offset
        # This is needed because mixer.music.get_pos() only reports the total time a song has been playing excluding set_pos() changes
        # (https://www.pygame.org/docs/ref/music.html#pygame.mixer.music.get_pos)
        Status.seek_offset = dpg.get_value("mythrilSeek") - mixer.music.get_pos()/1000
        mixer.music.set_pos(dpg.get_value("mythrilSeek"))
    else:
        Status.t1_seek_pos_update = True

def display_banks():
    """Gets folder, folder list and adds them to the folder_group list"""
    root_folder = check_folder("mythril")
    for folder_group in root_folder:
        if folder_group.find(".") == 0 or folder_group.find("_") == 0:
            continue
        else:
            Status.folder_groups.append(folder_group)

    # Check if folder_groups is empty, and if it is, break out early
    if len(Status.folder_groups) == 0:
        show_message("No Valid Banks Found. Verify folder structure and try again (Use ctrl+r to reload banks).", Color.ERROR)
        return

    width = 2
    total_length = len(Status.folder_groups)
    # Calculaltes how many rows are needed with given length
    rows = ceil(total_length / width)

    # Creates groups to put buttons
    for i in range(rows):
        parent_groups = dpg.add_group(horizontal=True,parent="BankGroup")
        Status.bank_groups.append(parent_groups)

    # Adds listboxes to each row, overflows to next row if space is needed
    for i in range(total_length):
        bank_folder_group = Status.folder_groups[i]
        current_row = floor(i/(width))
        parent_group = Status.bank_groups[current_row]
        dpg.add_group(tag=bank_folder_group,parent=parent_group,horizontal=False)
        dpg.add_text(bank_folder_group,parent=bank_folder_group,color=(255,0,0,255),tag=bank_folder_group+"Text")
        folder_group_songs = []
        for song in os.listdir(f"mythril/{bank_folder_group}"):
            # Only display files in which mythril can actually play (currently only .mp3)
            if song.lower().endswith(".mp3"):
                folder_group_songs.append(song)

        # TODO: Horribly hardcoded to split the listbox directly down the middle, will need to fix
        dpg.add_listbox(folder_group_songs,parent=bank_folder_group,
                        tag=(bank_folder_group+"List"),user_data=folder_group_songs,width=676//2,num_items=9)
        dpg.add_button(label="Select",parent=bank_folder_group,tag=(bank_folder_group+"Button"),
                        callback=select_bank)

    # Load the first bank in the list
    select_bank(Status.folder_groups[0])

def destroy_banks():
    """Destroys Banks. Used for regenerating them."""
    for i in Status.bank_groups:
        dpg.delete_item(i)

    Status.bank_groups = []
    Status.folder_groups = []

def on_key_ctrl():
    """Keyboard hotkey handler (for pressing ctrl)"""
    # Rebuild Banks (ctrl+r)
    if dpg.is_key_down(dpg.mvKey_R):
        destroy_banks()
        display_banks()
        show_message("Regenerated banks.")
    # Skip Forward (ctrl+right / ctrl+down)
    if dpg.is_key_down(dpg.mvKey_Right) or dpg.is_key_down(dpg.mvKey_Down):
        forward_button()
    # Skip Backward (ctrl+left / ctrl+up)
    if dpg.is_key_down(dpg.mvKey_Left) or dpg.is_key_down(dpg.mvKey_Up):
        back_button()

def show_window():
    """Main"""
    # Creates the monitor thread and starts it
    Status.t1 = Thread(target=status_thread,args=(),daemon=True)
    Status.t1.start()

    with dpg.handler_registry():
        # Creates a handler for the seek bar
        # drag_callback and drop_callback seems to be broken for sliders
        dpg.add_mouse_click_handler(callback=seek_clicked)
        dpg.add_mouse_move_handler(callback=seek_clicked)
        dpg.add_mouse_release_handler(callback=seek_clicked)

        # Hotkey handler
        dpg.add_key_press_handler(dpg.mvKey_Control, callback=on_key_ctrl)
        dpg.add_key_press_handler(dpg.mvKey_Spacebar, callback=play_pause_button)

    with dpg.window(label="Mythril",tag="mythril",autosize=True,on_close=destroy):
        # Main song controls
        with dpg.group(horizontal=True):
            dpg.add_button(label="Back",callback=back_button)
            dpg.add_button(label="Play",tag="mythrilPlay",callback=play_pause_button)
            dpg.add_button(label="Forward",callback=forward_button)

        # Volume and Song Seek bars
        dpg.add_slider_int(tag="mythrilVol",clamped=False,default_value=50,callback=vol_change)
        dpg.add_slider_float(tag="mythrilSeek",clamped=True,no_input=True)

        # Song Playing Configuration
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
            dpg.add_checkbox(label="Auto Start",callback=flip_auto,tag="Ta")
            with dpg.tooltip("Ta"):
                dpg.add_text("Automatically plays the song in the bank when switching to it")

        # Bank Group
        with dpg.group(tag="BankGroup"):
            pass

        # Status Text
        # TODO: More hardcoding nands
        dpg.add_text("Loading",tag="status",parent="mythril",wrap=700-100)

    display_banks()

# Main Process
# Required for the event system from pygame
pygame.init()
mixer.init()
dpg.create_context()
dpg.create_viewport(title=f"Mythril {VERSION}", width=700, height=600)
show_window()
dpg.set_primary_window("mythril",True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()

# Cleanup and Exit
dpg.destroy_context()
destroy()
sys_exit()
