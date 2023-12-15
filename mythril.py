# TODO: Add direct playing from youtube
# https://stackoverflow.com/a/8775928
# https://stackoverflow.com/a/49354406

import sys, random, os, threading, pygame
from math import ceil, floor
from time import sleep
from pygame import mixer, USEREVENT
sys.path.append('../Carbon')
import dearpygui.dearpygui as dpg
from mutagen.mp3 import MP3

loop = False
fade = False
SONGEND = USEREVENT+1
currentSong = ""
alive = True
shuffle = False
songLength = -1
wantToSwap = False

# Helper function to show a status message in the status bar
def showMessage(msg):
    dpg.set_value("status",msg)

# Forward button
def forwardButton(autoplay=False):
    global currentBank
    global currentSong
    global wantToSwap
    wantToSwap = False
    global playing
    playing = False
    global paused
    paused = False
    if (not loop):
        currentBankItems = dpg.get_item_user_data(currentBank+"List")
        index = currentBankItems.index(currentSong)
        # Either increments the index by one or shuffles it, depending on the setting
        if (not shuffle):
            if ((index + 1) > len(currentBankItems)-1):
                index = 0
            else:
                index += 1
        else:
            index = random.randrange(0, len(currentBankItems)-1)
        newSong = currentBankItems[index]
        dpg.set_value(currentBank+"List",newSong)
        currentSong = newSong
        dpg.configure_item("mythrilPlay",label="Play")
        if (autoplay):
            playPauseButton()

# Back Button, same thing as forward button but in reverse
def backButton():
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
    currentBankItems = dpg.get_item_user_data(currentBank+"List")
    index = currentBankItems.index(currentSong)

    if ((index - 1) < 0):
        index = len(currentBankItems)-1
    else:
        index -= 1
    newSong = currentBankItems[index]
    dpg.set_value(currentBank+"List",newSong)
    #playPauseButton()
    currentSong = newSong
    dpg.configure_item("mythrilPlay",label="Play") 

# Plays the song by handling loading it and volume change and such
def playSong():
    global queue
    global currentPos
    global playing
    global config
    global currentBank
    global currentSong
    global songLength
    global wantToSwap
    try:
        currentSong = dpg.get_value(currentBank+"List")
        mixer.music.unload()
        # Loads the music and plays it
        mixer.music.load(config["musicFolder"]+ '/'+currentBank+'/'+currentSong)
        mixer.music.set_endevent(SONGEND)
        volChange()
        song = MP3(config["musicFolder"]+ '/'+currentBank+'/'+currentSong)
        songLength = song.info.length*1000
        mixer.music.play(fade_ms=(int(fade)*config["fadeTimeMS"]))
        wantToSwap = True

    except Exception as e:
        showMessage("Error: No songs are loaded.")
        print(e)

# Play pause button
def playPauseButton():
    try:
        global playing
        global paused
        global currentPos
        if not playing:
            playing = True
            if (paused):
                mixer.music.unpause()
                paused = False
                showMessage("Now playing: " + currentSong)
            else:
                mixer.music.unload()
                playSong()
                showMessage("Now playing: " + currentSong)
            dpg.set_item_label("mythrilPlay","Pause")
        else:
            playing = False
            paused = True
            mixer.music.pause()
            dpg.set_item_label("mythrilPlay","Play")
            showMessage("Paused")
    except:
        showMessage("Cannot play, no songs are loaded.")

# Monitors volume change
def volChange():
    mixer.music.set_volume(dpg.get_value("mythrilVol")/100)

# Handles selecting a song bank to play from
def selectBank(sender=""):
    global paused
    paused = False
    global playing
    playing = False
    global currentBank
    global currentSong
    global wantToSwap
    wantToSwap = False
    if (fade):
        showMessage("Fading Song...")
        mixer.music.fadeout(config["fadeTimeMS"])
    else:
        mixer.music.stop()
    mixer.music.unload()
    dpg.set_item_label("mythrilPlay","Play")
    if (not currentBank == ""):
        dpg.configure_item(currentBank+"Text",color=(255,0,0,255))
    item = sender.split("Button")
    currentBank = item[0]
    currentBankItems = dpg.get_item_user_data(currentBank+"List")
    dpg.configure_item(item[0]+"Text",color=(0,255,0,255))
    showMessage("Selected bank: " + currentBank)
    currentSong = currentBankItems[0]

# checkStatus thread that monitors for the end of a song
def checkStatus():
    global playing
    global paused
    global alive
    pygame.init()
    while alive:
        sleep(0.1)
        try:
            if (playing):
                dpg.set_value("mythrilSeek",pygame.mixer.music.get_pos())
                dpg.configure_item("mythrilSeek",max_value=songLength)
            else:
                dpg.set_value("mythrilSeek",-1)
        except:
            pass

        for event in pygame.event.get():
            if event.type == SONGEND and wantToSwap:
                playing = False
                paused = False
                try:
                    mixer.music.unload()
                except:
                    pass
                if (not loop):
                    forwardButton(autoplay=True)
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

def focusWindow():
    dpg.focus_item("myhtril")

def init():
    global currentPos
    currentPos = 0
    global tags
    tags = []
    global queue
    queue = []
    global playing
    playing = False
    global paused
    paused = False
    global currentBank
    currentBank = ""

def checkFolder(folderName: str, createFolder: bool = True, listFolder: bool = True) -> list[str]:
    if (not os.path.isdir(folderName)):
        if (not createFolder):
            return None
        else:
            try:
                os.mkdir(folderName)
            except Exception as e:
                return None
            return os.listdir(folderName)
    else:
        if (listFolder):
            return os.listdir(folderName)

# Helper variable functions
def flipFade():
    global fade 
    fade = not fade
def flipLoop():
    global loop
    loop = not loop
def flipShuffle():
    global shuffle
    shuffle = not shuffle

# Automatically swaps the bank if an item is selected in the listbox
def swapSong(sender):
    global wantToSwap
    global currentSong
    wantToSwap = False
    currentSong = dpg.get_value(sender)
    selectBank(sender.split("List")[0])

# Main function
def showWindow(show=False):
    global tags
    global currentBank
    global fade
    global groups

    mixer.init()
    # Creates the monitor thread and starts it
    global t1
    t1 = threading.Thread(target=checkStatus,args=(),daemon=True)
    t1.start()
    
    # Loads categories
    folders = checkFolder("mythril")
    for tag in folders:
        if (tag.find(".") == -1):
            tags.append(tag)

    with dpg.window(label="Mythril",tag="mythril",show=show,autosize=True,on_close=destroy):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Back",callback=backButton)
            dpg.add_button(label="Play",tag="mythrilPlay",callback=playPauseButton)
            dpg.add_button(label="Forward",callback=forwardButton)
        dpg.add_slider_int(tag="mythrilVol",clamped=True,default_value=50,callback=volChange)
        dpg.add_slider_float(tag="mythrilSeek",clamped=True,no_input=True)
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Fade Between Songs",callback=flipFade)
            dpg.add_checkbox(label="Loop Current Song",callback=flipLoop)
            dpg.add_checkbox(label="Shuffle",callback=flipShuffle)

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
            dpg.add_text(notLabel,parent=notLabel,color=(255,0,0,255),tag=(notLabel+"Text"))
            tagSongs = []
            for song in os.listdir("mythril/"+notLabel):
                tagSongs.append(song)
            dpg.add_listbox(tagSongs,parent=notLabel,tag=(notLabel+"List"),user_data=tagSongs)#,callback=swapSong)
            dpg.add_button(label="Select",parent=notLabel,tag=(notLabel+"Button"),callback=selectBank)
        
        dpg.add_text("HELP",tag="status")
        # Tries to load first bank
        try:
            selectBank(tags[0])
        except:
            showMessage("No Banks Found. Verify folder structure and try again.")
    dpg.set_item_pos("mythril",[0,19])

dpg.create_context()
dpg.create_viewport(title='Mythril', width=700, height=600)

init()
showWindow(True)

dpg.set_primary_window("mythril",True)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
exit()