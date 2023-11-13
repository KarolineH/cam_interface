#!/bin/bash

# retrieving information 
gphoto2 --auto-detect # detect available cameras
gphoto2 --summary # camera information
gphoto2 --list-config # list all configuration options

# for recording video (preview frames) in PHOTO mode, use this:
# 1024 × 576 ~25fps max output, can also record to the SD card in 1920x1080 at the same time 
gphoto2 --set-config /main/actions/eosmoviemode=1 # activates "movie mode" but within the PHOTO mode of the camera
gphoto2 --set-config /main/settings/movierecordtarget=0 # set the storage target to card
gphoto2 --capture-movie=10s # record for a number of seconds

# for taking regular captures
gphoto2 --set-config /main/actions/eosremoterelease=2 # this is a full press of the shutter button
gphoto2 --capture-image-and-download # save directly to PC, always triggers AF
gphoto2 --capture-image # just take 1 image and save to camera
gphoto2 --trigger-capture
gphoto2 --set-config eosremoterelease=6 --set-config eosremoterelease=2 --wait-event-and-download=2s # this is a half press (triggering AF), followed by full press and download
# eosremoterelease
    # 3 followed by 8 triggers AF and then releases shutter 
    # 2 / 5 (immediate) both appear to trigger JUST the shutter
    # 3 followed by 6 only triggers AF, no capture

# when in VIDEO mode, toggle recording:
gphoto2 --set-config /main/settings/movierecordtarget=0 # REC
gphoto2 --set-config /main/settings/movierecordtarget=1 # STDBY

# important configurations
gphoto2 --get-config /main/capturesettings/focusmode # switch between one-shot and AI Servo focus
gphoto2 --set-config /main/capturesettings/continuousaf=1 # activate continuous autofocus
gphoto2 --set-config /main/capturesettings/liveviewsize=0 # sets the output of the preview video capture to the largest size (960x640) that is available in photo
gphoto2 --set-config /main/capturesettings/drivemode=1 # This sets the camera to "super high speed continuous shooting". Once active, remote shutter will keep firing! 
gphoto2 --set-config eoszoomposition=1,1 # in photo mode, set the focus pixel location

# download new photos
 gphoto2 --new