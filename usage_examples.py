
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
current_value, choices, msg = cam1.set_image_format(list_choices=True) # what formats are available?
im_format,__,__ = cam1.set_image_format(0) # select the format
cam1.sync_date_time() # sync PC date and time to the camera
files = cam1.list_files() # see files stored on storage media in the camera
cam1.download_file(files[0], target_file='./test.jpg') # download a file from the camera to the PC

cam1.set_exposure_manual() # set exposure mode to manual, which allows remote manipulation of iso, aperture, and shutterspeed
[current_aperture, current_iso, current_shutterspeed, current_cAF], msgs = cam1.set_capture_parameters(aperture=20, iso=120, shutterspeed='1/65', c_AF=False)

# msg = cam1.manual_focus(value=3) # focus manually
current_value, msg = cam1.set_AF_location(1000,500) # target a specific pixel location for AF
msg = cam1.trigger_AF()

# Capturing images and video
success, msg = cam1.capture_preview(target_file='./preview.jpg')
success, file_path, msg = cam1.capture_immediate(download=True, target_path='.')
success, file_path, msg = cam1.record_preview_video(t=1, target_path='.', resolution_prio=True)
success, files, msg = cam1.capture_burst(t=1)

# And finally, record full-res video in VIDEO mode
success, file_path, msg = cam1.record_video(t=1, download=True, target_path='.')