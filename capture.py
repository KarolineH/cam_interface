import gphoto2 as gp
import subprocess as sp, logging, os
from PIL import Image
from datetime import datetime
import time
from subprocess import Popen, PIPE

class EOS(object):
    """
    Interface a Canon EOS R5 C with gphoto2 via USB.
    """

    def __init__(self, port=None):
        # Kill any existing gphoto processes to free up the USB ports for communication
        # prevents error *Could not claim the USB device*
        command = f'killall gvfsd-gphoto2 gvfs-gphoto2-volume-monitor'
        sp.call([command], shell=True)

        camera_list = list(gp.Camera.autodetect()) # Find all available cameras
        if not camera_list:
            print('No camera detected')
            exit()
        
        self.camera = gp.Camera()
        if port is not None: # If a port is specified, initialise the correct device
            port_info_list = gp.PortInfoList()
            port_info_list.load()
            idx = port_info_list.lookup_path(port)
            self.camera.set_port_info(port_info_list[idx])

            name = camera_list[[entry[1] for entry in camera_list].index(port)][0]
            abilities_list = gp.CameraAbilitiesList()
            abilities_list.load()
            idx = abilities_list.lookup_model(name)
            self.camera.set_abilities(abilities_list[idx])
        self.camera.init()
        self.config = self.camera.get_config()
        self.mode = self.get_camera_mode() # detects the manual switch state: 0 == PHOTO, 1 == VIDEO
        if self.mode == 0:
            self.set_exposure_manual()



    ''' Universal Methods, work in both PHOTO and VIDEO mode '''


    def list_all_config(self):
        '''
        List all available configuration options communicated via USB and supported by gphoto2
        '''
        return [el[0] for el in gp.check_result(gp.gp_camera_list_config(self.camera))]
    
    def get_camera_mode(self):
        '''
        Detect whether the physical switch on the camera is set to photo or video mode
        0 == PHOTO, 1 == VIDEO
        '''
        switch = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmovieswitch'))
        value = gp.check_result(gp.gp_widget_get_value(switch))
        return int(value)
    
    def sync_date_time(self):
        '''
        Sync the camera's date and time with the connected computer's date and time.
        '''
        date_time = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'syncdatetimeutc'))
        date_time.set_value(1)
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        date_time.set_value(0)
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return

    def get_config(self, config_name=''):
        '''
        Get the current value and all choices of a named configuration
        '''
        if config_name in self.list_all_config():
            conf = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config_name))
            value = gp.check_result(gp.gp_widget_get_value(conf))
            try:
                choices = list(conf.get_choices())
            except:
                choices = None
                print(f"Config {config_name} provides no choices")
            return value, choices
        else:
            print(f"Config {config_name} not found")
            return None
    
    def get_file_info(self, file_path):
        '''Retrieve information about a specific file saved on the device.'''
        folder, name = os.path.split(file_path)
        info = self.camera.file_get_info(folder, name)
        #size = info.file.size
        #file_type = info.file.type
        #timestamp = datetime.fromtimestamp(info.file.mtime).isoformat(' ')
        return info

    def list_files(self, path='/store_00020001/DCIM'):
        '''List all media files saved on the device (default) or at a specific location on the device.'''
        folders = [os.path.join(path, folder[0]) for folder in self.camera.folder_list_folders(path)]
        files = [os.path.join(folder,file_name[0]) for folder in folders for file_name in self.camera.folder_list_files(folder)]
        return files
    
    def download_file(self, camera_path, target_file=None):
        '''Download a specific file saved on the device to the target file path on the PC.'''
        folder, name = os.path.split(camera_path)
        cam_file = self.camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
        if target_file is None:
            target_file = os.path.join('./', name)
        cam_file.save(target_file)
        return target_file
    
    def manual_focus(self, value=3):
        '''
        Manually drive the focus nearer or further in three different increment sizes.
        This function will have to be called repeatedly to achieve a specific focus distance.
        To bring the focus point nearer, use [0,1,2] for [small, medium, large] increments.
        To bring the focus point further, use [4,5,6] for [small, medium, large] increments.
        '''
        # 0,1,2 == small, medium, large increment --> nearer
        # 3 == none
        # 4,5,6 == small, medium, large increment --> further 
        value = int(value)
        mf = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'manualfocusdrive'))
        mf.set_value(list(mf.get_choices())[value])
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        mf.set_value(list(mf.get_choices())[3]) # set back to 'None'
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return
    
    def set_aperture(self, value='AUTO', list_choices=False):
        '''
        Change the aperture (f-number), or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Input value should be of type int, float, or string 'AUTO'
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.

        WARNING: !! In VIDEO mode, it is unclear if the AUTO setting works. Might have to set 'Iris Mode' to 'Automatic' in the camera menu if you need auto aperture. !!
        '''

        auto = False
        if self.mode == 0:
            # in PHOTO mode
            choices = [2.8, 3.2, 3.5, 4, 4.5, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 13, 14, 16, 18, 20, 22, 25, 29, 32]
            auto_string = 'Unknown value 00ff'
        else:
            # in VIDEO mode
            choices = [2.8, 3.2, 3.5, 4, 4.5, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 14, 16, 18, 20, 22, 25, 29, 32] # option 13 is missing
            auto_string = 'implicit auto'

        if value == 'AUTO':
            auto = True
            value = auto_string

        msg = ''
        aperture = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'aperture'))
        if list_choices:
            choices.append('AUTO')
            print(choices)
            if aperture.get_value() == auto_string:
                return 'AUTO', choices, msg
            else:
                return aperture.get_value(), choices, msg

        if not auto:
            value = float(value)
            # if the exact value specified is not supported, use the closest option
            if value not in choices:
                closest = min(choices, key=lambda x: abs(x - value))
                msg = f'Aperture of {value} not supported, using closest option of {closest}'
                print(msg)
                value = closest
            # gphoto2 only accepts strings formated as proper floats or integers, no ints with trailing zeros
            if value == int(value):
                value = int(value)

        choices.append('AUTO')
        aperture.set_value(str(value))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return str(value), choices, msg
    
    def set_shutterspeed(self, value='AUTO', list_choices=False):
        '''
        Change the shutter speed, or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Input value should be a string of the form '1/50' or '0.5' or '25', or one of the automatic options.
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.
        '''

        auto = False
        if self.mode == 0:
            # in PHOTO mode
            choices = ['30', '25', '20', '15', '13', '10.3', '8', '6.3', '5', '4', '3.2', '2.5', '2', '1.6', '1.3', '1', '0.8', '0.6', '0.5', '0.4', '0.3', '1/4', '1/5', '1/6', '1/8', '1/10', '1/13', '1/15', '1/20', '1/25', '1/30', '1/40', '1/50', '1/60', '1/80', '1/100', '1/125', '1/160', '1/200', '1/250', '1/320', '1/400', '1/500', '1/640', '1/800', '1/1000', '1/1250', '1/1600', '1/2000', '1/2500', '1/3200', '1/4000', '1/5000', '1/6400', '1/8000']
            num_choices = [eval(choice) for choice in choices]
            auto_string = 'bulb'
        else:
            # in VIDEO mode
            choices = ['1/50', '1/60', '1/75', '1/90', '1/100', '1/120', '1/150', '1/180','1/210', '1/250', '1/300', '1/360',  '1/420',  '1/500',  '1/600',  '1/720',  '1/840',  '1/1000', '1/1200', '1/1400', '1/1700', '1/2000'] # option 13 is missing
            num_choices = [eval(choice) for choice in choices]
            auto_string = 'auto'

        if value == 'AUTO':
            auto = True
            value = auto_string
        
        msg = ''
        shutterspeed = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'shutterspeed'))
        if list_choices:
            choices.append('AUTO')
            print(choices)
            if shutterspeed.get_value() == auto_string:
                return 'AUTO', choices, msg
            else:
                return shutterspeed.get_value(), choices, msg

        if not auto:
            # if the exact value specified is not supported, use the closest option
            if value not in choices:
                num_value = eval(value)
                closest = choices[num_choices.index(min(num_choices, key=lambda x: abs(x - num_value)))]
                msg = f'Shutterspeed of {value} not supported, using closest option of {closest}'
                print(msg)
                value = closest

        choices.append('AUTO')
        shutterspeed.set_value(value)
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return value, choices, msg
    
    def set_continuous_AF(self, value='Off'):
        '''
        Turn continuous auto focus on (1/'On') or off (0/'Off').
        Always treturns the (new) currently active setting.
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.
        '''
        if self.mode == 0:
            config = 'continuousaf'
        else:
            config = 'movieservoaf'

        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        value_dict = {0:'Off',1:'On', '0':'Off', '1':'On', 'False':'Off','True':'On','off':'Off','on':'On', 'Off':'Off', 'On':'On'}
        if value not in value_dict:
            error_msg = f"Value {value} not supported. Please use 'Off' or 'On'."
            print(error_msg)
            return c_AF.get_value(), error_msg

        value = value_dict[value]
        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        c_AF.set_value(value)
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return value, ''
    

    ''' PHOTO mode only methods'''


    def set_exposure_manual(self):
        '''
        Set the camera's auto-exposure mode to manual, so that shutter, aperture, and iso can be set remotely.
        Only supported in PHOTO mode.
        '''
        exp_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autoexposuremodedial'))
        exp_mode.set_value('Fv') # 'Fv' == Canon's 'Flexible-Priority Auto Exposure', useful for manual access
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return

    def set_iso(self, value='AUTO', list_choices=False):
        '''
        Change the ISO setting, or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Accepts input values of type int, either as the index of the choice or the value itself.
        Only supported in PHOTO mode.
        '''
        msg = ''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually set ISO."
            print(msg)
            return None, None, msg
        
        iso = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'iso'))
        choices = list(iso.get_choices())
        num_choices = [eval(choice) for choice in choices if choice.isnumeric()]

        if list_choices:
            num_choices.append('AUTO')
            return iso.get_value(), num_choices, msg
        
        if value == 'AUTO':
            iso.set_value('Auto')
        else:
            value = int(value)
            if value not in num_choices:
                closest = min(num_choices, key=lambda x: abs(x - value))
                msg = f'ISO of {value} not supported, using closest option of {closest}'
                print(msg)
                value = closest
            value = str(value)
            iso.set_value(value)
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        num_choices.append('AUTO')
        return value, num_choices, msg

    def set_image_format(self, value=0, list_choices=False):
        '''
        Change the target image format, or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Only supported in PHOTO mode.
        '''
        msg = ''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to change the target image format"
            print(msg)
            return None, None, msg
        
        im_format = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'imageformat'))
        choices = list(im_format.get_choices())
        if list_choices:
            print(choices)
            msg = "Select format by full string or index"
            return im_format.get_value(), choices, msg
        if str(value) not in choices:
            if str(value).isnumeric() and int(value) < len(choices):
                value = choices[int(value)]
            else:
                msg = f"Format {value} not supported, please input choice either as full string or by index."
                print(msg)  
                return im_format.get_value(), choices, msg
            
        OK = gp.check_result(gp.gp_widget_set_value(im_format, value))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return value, choices, msg
    
    def trigger_AF(self):
        '''
        Trigger auto-focus once. 
        It is currently not possible to check if focus has been achieved.
        This function might need to be called repeatedly to adjust focus.
        (Equivalent to the bash command --set-config autofocusdrive=1)
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually trigger auto focus"
            print(msg)
            return msg
        AF_action = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autofocusdrive'))
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 1))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 0))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return 'AF triggered once'
    
    def set_AF_location(self, x, y):
        '''
        Set the auto focus point to a specific pixel location.
        (Equivalent to the bash command --set-config eoszoomposition=x,y)
        x and y are int, supported range is the image resolution, normally (1,1) to (8192,5464)
        Only supported in PHOTO mode.
        '''
        msg = ''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually set auto focus location"
            print(msg)
            return None, msg
        
        AF_point = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eoszoomposition'))
        if 0 <= x <= 8192 and 0 <= y <= 5464:
            OK = gp.check_result(gp.gp_widget_set_value(AF_point, f"{x},{y}"))
            OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
            return f'{x},{y}', msg
        else:
            msg = f"AF point {x},{y} not supported, please input values between according to your selected image resolution, normally between 0 and 8192 for x and 0 and 5464 for y."
            return AF_point.get_value(), msg
    
    def capture_preview(self, target_file='./preview.jpg'):
        '''
        Capture a preview image (i.e. viewfinder frame, with the mirror up) and save it to the target file.
        Optionally display the image.
        The taken image is NOT saved on the device, only on the computer.
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture a preview"
            print(error_msg)
            return False, error_msg
        
        camera_file = gp.check_result(gp.gp_camera_capture_preview(self.camera))
        camera_file.save(target_file)
        return True, 'saved to computer'

    def capture_immediate(self, download=True, target_path='.'):
        '''
        Taken an immeditate capture, without triggering the auto-focus first.
        Optionally download the image to the target path.
        The file will also be saved to the device and the file name will follow the camera's set naming convention.
        Only supported in PHOTO mode.
        '''

        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture static images"
            print(error_msg)
            return False, error_msg
        
        release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease'))
        release.set_value('Immediate') # 5 == Immediate
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        if download:
            timeout = time.time() + 5
            while True:
                # potential for errors if the new file event is not caught by this wait loop
                # loop times out after 10 seconds
                event_type, event_data = self.camera.wait_for_event(1000)
                if event_type == gp.GP_EVENT_FILE_ADDED:
                    cam_file = self.camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                    cam_file.save(target_path+'/'+event_data.name)
                    release.set_value('None')
                    OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
                    return True, 'downloaded'
                elif time.time() > timeout:
                    error_msg = "Waiting for new file event timed out, capture may have failed."
                    print(error_msg)
                    release.set_value('None')
                    OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
                    return False, error_msg
        release.set_value('None')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return True, 'saved to camera'
    
    def record_preview_video(self, t=1, target_file ='./prev_vid.mp4', resolution_prio=False):
        '''
        Capture a series of previews (i.e. the viewfinder frames, with mirror up)
        for a duration of t seconds, and save them as a video file.
        The file will not be saved to the device.
        Note that this function will overwrite existing files in the specified location!
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture preview videos"
            print(error_msg)
            return False, error_msg
        
        if os.path.exists(target_file): # overwrite existing file to prevent ffmpeg error
            os.remove(target_file)

        # if a higher resolution is the priority, record in 'eosmoviemode' at 1024x576 and ~25 fps
        # if a higher frame rate is the priority, record at 960x640 and close to ~60 fps
        if resolution_prio:
            mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmoviemode'))
            mode.set_value(1)
            try:
                OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
            except:
                OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        else:
            frame_size = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'liveviewsize'))
            frame_size.set_value('Large') # set to max size: 960x640
            OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))

        # Attempting to recreate the bash command "gphoto2 --capture-movie"
        # under the hood, this just takes repeated preview captures
        # see https://github.com/gphoto/gphoto2/blob/f632dcccfc2f27b7e510941335a80dfc986b4bf2/gphoto2/actions.c#L1053
        # sp.call(['gphoto2 --capture-movie=2s'], shell=True) # Can't call the bash command here, because I/O is busy
        #OK, path = gp.gp_camera_capture(self.camera, gp.GP_CAPTURE_MOVIE) # error: function not supported
        ffmpeg_command = [
            'ffmpeg', 
            '-f', 'image2pipe',           # Input format
            '-vcodec', 'mjpeg',
            '-i', '-',                    # Input comes from a pipe
            '-c:v', 'libx264',            # Video codec to use for encoding
            '-pix_fmt', 'yuvj422p',        # Output pixel format
            target_file                   # Output file path
        ]

        ffmpeg = Popen(ffmpeg_command, stdin=PIPE)

        start_time = time.time()  # Start the timer
        while True:
            if time.time() - start_time > t:
                break  # Stop recording after t seconds
            capture = self.camera.capture_preview()
            filedata = capture.get_data_and_size()
            data = memoryview(filedata)
            ffmpeg.stdin.write(data.tobytes())
        ffmpeg.stdin.close()
        ffmpeg.wait()

        if resolution_prio:
            mode.set_value(0)
            try:
                OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
            except:
                OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return True, 'saved to computer'
    
    def capture_burst(self, t=0.5, save_timeout=5):
        '''
        Shoot a quick burst of full-scale images for a duration of t seconds.
        Should achieve about 8-9fps. Returns a list of file locations on the camera.
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture burst"
            print(error_msg)
            return False, None, error_msg

        # Set the drive mode to continuous shooting
        drive_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'drivemode'))
        drive_mode.set_value(list(drive_mode.get_choices())[1])
        release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease'))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))

        # start shooting but activating remote trigger
        release.set_value('Immediate') # 5 == Immediate
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        time.sleep(t) # wait for the desired duration
        # and turn the trigger OFF again
        release.set_value('Release Full')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))

        # after the burst is over, fetch all the files
        # this allows for faster shooting rather than saving files after each capture
        files=[]
        timeout = time.time() + save_timeout # the save timeout stops retrieving of files if no new file has been written for a while
        while True:
            event_type, event_data = self.camera.wait_for_event(100)
            if event_type == gp.GP_EVENT_FILE_ADDED:
                files.append(event_data.folder +'/'+ event_data.name)
                timeout = time.time() + save_timeout
            elif time.time() > timeout:
                break

        # Finally, set the drive mode back to individual captures
        drive_mode.set_value(list(drive_mode.get_choices())[0])
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return True, files, 'saved to camera'

    ''' VIDEO mode only methods'''


    def record_video(self, t=1, download=True, target_path='.', save_timeout=5):
        '''
        Record a video for a duration of t seconds.
        Resolution and file formats are set in the camera's menu. Storage medium must be inserted.
        Only supported in VIDEO mode.
        '''
        if self.mode == 0:
            error_msg = "Camera must be in VIDEO mode to record full-res videos"
            print(error_msg)
            return False, error_msg
        
        # recording
        rec_button = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'movierecordtarget'))
        rec_button.set_value('Card')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        time.sleep(t)
        rec_button.set_value('None')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))

        # fetching the file
        timeout = time.time() + save_timeout
        if download:
            while True:
                # potential for errors if the new file event is not caught by this wait loop
                event_type, event_data = self.camera.wait_for_event(1000)
                if event_type == gp.GP_EVENT_FILE_ADDED:
                    cam_file = self.camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                    cam_file.save(target_path+'/'+event_data.name)
                    return True, 'File downloaded to PC'
                elif time.time() > timeout:
                    error_msg = "Warning: Waiting for new file event timed out, capture may have failed."
                    print(error_msg)
                    return True, error_msg
        return True, 'saved to camera'

if __name__ == '__main__':

    cam1 = EOS(port='usb:002,016')
    cam1.set_continuous_AF(value='On')
    #cam1.set_iso(value=120,list_choices=True)
    #cam1.capture_image(download=False, target_path='./', AF=True)

    print("Camera initalised")
