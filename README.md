# cam_interface
This is a python interface for remote controlling one or multiple Canon EOS R5 C cameras via USB.

# Set-up instructions
1. Install the requirements (listed below).
2. Make sure all cameras are equipped with fully charged batteries.
3. Confirm that all cameras are equipped with SD cards.\
If the card is new or was previously formatted (initialized) by another camera or computer, it is advised to format the card using the camera's own menu. 
5. Connect all cameras to the PC via USB.
6. Turn on all cameras by setting the switches to PHOTO (recommended) or VIDEO mode.
7. To check if everything is ready, open a terminal and run 'gphoto2 --auto-detect'\
If any of the cameras are not detected, please refer to gphoto2 documentation. 

We also advise to turn the 'Auto rotate' feature OFF in the camera menu (on the camera itself) and we mostly use the 'Scene Intelligent Auto' or 'Flexible-priority AE' shooting modes. Please refer to the camera manual for details.

# Quick start
After following the set-up instructions, take a look at uage_examples.py, especially the top-level API calls: get_capture_parameters(), capture_image(), capture_video(), and show_live_preview().

# Mode selection
- Use PHOTO mode for capturing stills and also for maximum control over capture parameters, including ISO and autofocus 
    - capture photos at full resolution
    - capture photo bursts at ~ 9 fps
    - a live preview video stream can be displayed with 960x640 resolution at around 15fps
    - recording videos to file is possible at 1024x576 and ~25 fps OR at 960x640 and ~60 fps
- Use VIDEO mode for full-resolution video capture
    - With suitable storage media, the camera supports formats up to 8192x4320 and 60fps, please refer to the camera user guide for more details
    - Note that this mode is not supported by older versions of gphoto2

# Requirements:
[gphoto2 >= 2.5.27, libphoto2 >= 2.5.31](http://www.gphoto.org/doc/manual/index.html) (We recommend using this [gphoto2-updater tool](https://github.com/gonzalo/gphoto2-updater) for installation)\
[python-gphoto2 v2.5.1](https://github.com/jim-easterbrook/python-gphoto2)

Tested with Python 3.10.12
