
from capture import EOS
import gphoto_util

### USAGE EXAMPLES ###

# Initialise camera
port = gphoto_util.choose_camera()
cam1 = EOS(port=port)

# Get information about available cmaera configs
config_names = cam1.list_all_config() # list all
value, choices = cam1.get_config('autofocusdrive') # get details about a specific config


# Set a few parameters
im_format = cam1.set_image_format(list_choices=True) # what formats are available?
im_format = cam1.set_image_format(0) # select the format
cam1.sync_date_time() # sync PC date and time to the camera
files = cam1.list_files() # see files stored on storage media in the camera
cam1.download_file(files[0], target_path='.') # download a file from the camera to the PC

cam1.set_exposure_manual() # set exposure mode to manual, which allows remote manipulation of iso, aperture, and shutterspeed
cam1.set_shutterspeed('1/65')
cam1.set_aperture(20)
values = cam1.set_iso(list_choices=True) # what iso values are available?
cam1.set_iso(120) # use 0 for auto

# cam1.manual_focus(value=3) # focus manually
cam1.set_continuous_AF('Off')
cam1.set_AF_location(1000,500) # target a specific pixel location for AF
cam1.trigger_AF()

#file_location = cam1.capture_preview(target_file='./preview.jpg', show=False) # Capture a preview frame
cam1.capture_image(download=True, target_path='.', AF=True) # Capture full-size image with or without AF 
#cam1.record_preview_video(t=1, target_file ='./prev_vid.mp4', resolution_prio=False) # Record a preview video (series of viewfinder frames), either with resolution priority (True) or frame rate priority (False) 
#burst_files = cam1.capture_burst(t=0.5) # Capture a burst of full-size images of length t seconds. Returns location of files on camera storage media.


# And finally, record video in VIDEO mode
cam1.record_video(t=1, download=True, target_path='.') # record a video of length t seconds