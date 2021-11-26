import os
import subprocess
import time
import digitalio
import board
import adafruit_matrixkeypad

cols = [digitalio.DigitalInOut(x) for x in (board.D5, board.D6, board.D12)]
rows = [digitalio.DigitalInOut(x) for x in (board.D27, board.D22, board.D23, board.D24)]
keys = ((1,2,3),(4,5,6),(7,8,9),('vup',0,'vdown'))

keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, keys)

check_keypad = True

def SiriusActiveQ():
  '''
  Checks systemd to see if siriusxm is active.  
  systemctl returns 0 if active, or 3 if inactive (presumably other exit codes as well)
  '''
  r = subprocess.call(['systemctl','is-active','siriusxm'])
  return (r == 0)

def killVLC():
  '''
  Ensures that vlc is not running
  '''
  os.system('killall vlc')

def SiriusPlay(channel):
  ''' 
  Plays a channel, does not check if channel is valid
  '''
  killVLC()
  subprocess.Popen(['cvlc','http://127.0.0.1:8888/{}.m3u8'.format(channel)])

def playClassical():
  '''
  Plays theclassicalstation.org
  '''
  killVLC()
  subprocess.Popen(['cvlc', 'http://audio-ogg.ibiblio.org:8000/wcpe.ogg.m3u'])

def playLocal():
  '''
  Plays random songs in the Music directory
  '''
  killVLC()
  subprocess.Popen(['cvlc', '-Z', '/mnt/bespin/Shared Music/Rozenn'])

def playHalloween():
  '''
  Plays random songs in the Halloween directory
  '''
  killVLC()
  subprocess.Popen(['cvlc', '-Z', '/mnt/bespin/Shared Music/Halloween'])

def speak(statement):
  os.system('espeak -w /tmp/out.wav -ven+f3 -k5 -s150 -a125 "{}" 2>/dev/null'.format(statement))
  os.system('aplay /temp/out.wav')
  #subprocess.call(['espeak','-s','125','-a','150',str(statement)])

def constrain(val, min_val, max_val):
  return min(max_val, max(min_val, val))
def setvolume(volume):
  vol = constrain(volume,0,100) # Just making sure
  subprocess.run(['amixer', 'sset','PCM','{}%'.format(vol)])

def process_keypress(key):
  global volume
  if (key=='vup'):
    volume = constrain(volume + 5,0,100)
    setvolume(volume)
  elif (key=='vdown'):
    volume = constrain(volume - 5, 0, 100)
    setvolume(volume)
  elif (key==0):
    killVLC()
    setvolume(75)
  elif (key==1):
    playLocal()
  elif (key==2):
    SiriusPlay('9443')
  elif (key==3):
    SiriusPlay('9432')
  elif (key==4):
    SiriusPlay('9344')
  elif (key==5):
    SiriusPlay('9489')
  elif (key==6):
    SiriusPlay('9484')
  elif (key==7):
    playClassical()
  elif (key==8):
    SiriusPlay('symphonyhall')
  elif (key==9):
    SiriusPlay('purejazz')
  else:
    speak('I do not understand.')

print("Setting default volume to 75%")
volume = 75
setvolume(volume)

print("Do something")
while True:
  try:
    if check_keypad:
      keys = keypad.pressed_keys
      if keys:
        check_keypad = False
        process_keypress(keys[0])
        check_keypad = True
      time.sleep(0.1)
  except (KeyboardInterrupt, EOFError, SystemExit):
    break

