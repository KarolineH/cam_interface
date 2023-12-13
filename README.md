# cam_interface
This is a python interface for remote controlling one or multiple Canon EOS R5 C cameras via USB.

# Set-up instructions
1. Install the requirements (listed below).
2. Make sure all cameras are equipped with fully charged batteries.
3. Confirm that all cameras are equipped with SD cards.\
If the card is new or was previously formatted (initialized) by another camera or computer, it is advised to format the card using the camera's own menu. 
5. Connect all cameras to the PC via USB.
6. Turn on all cameras by setting the switches to PHOTO or VIDEO mode.
7. To check if everything is ready, open a terminal and run 'gphoto2 --auto-detect'\
If any of the cameras are not detected, please refer to gphoto2 documentation. 

# Requirements:
[gphoto2 >= 2.5.27](http://www.gphoto.org/doc/manual/index.html)\
[python-gphoto2 v2.5.1](https://github.com/jim-easterbrook/python-gphoto2)

Tested with Python 3.10.12
