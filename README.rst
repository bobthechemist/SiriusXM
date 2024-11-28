SiriusXM
--------

This script creates a server that serves HLS streams for SiriusXM channels. To use it, pass your SiriusXM username and password and a port to run the server on. For example, you start the server by running:
`python3 sxm.py -p 8888`

You can see a list of the channels by setting the -l or --list flag:
`python3 sxm.py -l`

Then in a player that supports HLS (QuickTime, VLC, ffmpeg, etc) you can access a channel at http://127.0.0.1:8888/channel.m3u8 where "channel" is the channel ID (the 4-digit code in the first column of the channel list output).

Modifications
-------------

The original source has been marked as read only, so this is my place to keep updates and modifications.  Here is my intended use:

* Single user streaming from a Raspberry Pi Zero W equipped with an `Adafruit speaker bonnet <https://www.adafruit.com/product/3346>`_.
* Interface with an `Adafruit 3x4 membrane matrix pad <https://www.adafruit.com/product/419>`_
* Publishes track information to an Adafruit.io feed, which is then fetched and displayed on an `Adafruit Matrixportal <https://www.adafruit.com/product/4745>`_

To help me from sharing my credentials with the world, I have modified the original code to include a `my_secrets` dictionary.  A template is included, and .gitignore will prevent you from sharing the non-templated version, hopefully.

The Raspberry Pi uses `cvlc` to play music, so that should be installed `sudo apt isntall vlc` (TBH I do not know if the current version of vlc contains the command line tool; previously, vlc-nox was required).

The matrixpad script is simply an adaptation of Adafruit's tutorial.  It shows how the buttons can be programmed to different channels or even other streaming services and locally mounted sources.  Naturally, these will need to be changed to suit your preferences.  Note: I have my matrix pad mounted upside down on my wall; hence the odd numbering.

Two services are included to allow the RPi to run headless.  Each service calls a bash script which executes the python scripts, which allows for future developments such as checking for mounted directories and internet access w/o cluttering up the python scripts.

The RPi I'm using is running deprecated Stretch because I cannot get the speaker bonnet to work on current RPi OS versions. It uses Python 3.5 which therefore requires Adafruit_IO version 1.0.0 to be installed. Upon install, it raises an error about a README file not being found; however, I have not found this error to be problematic and the script can send data to the feed.

Credits
-------

Original work is from andrew0 <andrew0@github.com> who reverse engineered the
original SXM APIs.
