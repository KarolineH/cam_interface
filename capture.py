import gphoto2 as gp
import subprocess as sp, logging, os
import time
from subprocess import Popen, PIPE

class EOS(object):
    """
    Interface a Canon EOS R5 C using gphoto2 via USB port.
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
        if port is not None: # If a port is specified, initialise the correct device, otherwise just use the first detected compatible device
            port_info_list = gp.PortInfoList()
            port_info_list.load()
            idx = port_info_list.lookup_path(port)
            self.camera.set_port_info(port_info_list[idx])

            name = camera_list[[entry[1] for entry in camera_list].index(port)][0]
            abilities_list = gp.CameraAbilitiesList()
            abilities_list.load()
            idx = abilities_list.lookup_model(name)
            self.camera.set_abilities(abilities_list[idx])

        # Initialise camera
        self.camera.init()
        self.config = self.camera.get_config()
        self.mode = self.get_camera_mode() # detects the manual switch state: 0 == PHOTO, 1 == VIDEO
        if self.mode == 0:
            self.set_exposure_manual() # set the camera's auto-exposure mode to manual, so that shutter, aperture, and iso can be set remotely

        # set the main capture configuration options for both PHOTO and VIDEO mode
        if self.mode == 0:
            self.aperture_choices = [2.8, 3.2, 3.5, 4, 4.5, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 13, 14, 16, 18, 20, 22, 25, 29, 32]
            self.shutter_choices = ['30', '25', '20', '15', '13', '10.3', '8', '6.3', '5', '4', '3.2', '2.5', '2', '1.6', '1.3', '1', '0.8', '0.6', '0.5', '0.4', '0.3', '1/4', '1/5', '1/6', '1/8', '1/10', '1/13', '1/15', '1/20', '1/25', '1/30', '1/40', '1/50', '1/60', '1/80', '1/100', '1/125', '1/160', '1/200', '1/250', '1/320', '1/400', '1/500', '1/640', '1/800', '1/1000', '1/1250', '1/1600', '1/2000', '1/2500', '1/3200', '1/4000', '1/5000', '1/6400', '1/8000']
            self.iso_choices = [100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000, 12800, 16000, 20000, 25600, 32000, 40000, 51200]
        else:
            self.aperture_choices = [2.8, 3.2, 3.5, 4, 4.5, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 14, 16, 18, 20, 22, 25, 29, 32] # option 13 is missing
            self.shutter_choices = ['1/50', '1/60', '1/75', '1/90', '1/100', '1/120', '1/150', '1/180','1/210', '1/250', '1/300', '1/360',  '1/420',  '1/500',  '1/600',  '1/720',  '1/840',  '1/1000', '1/1200', '1/1400', '1/1700', '1/2000'] # option 13 is missing


    ''' Universal Methods, work in both PHOTO and VIDEO mode '''

    def set_config_helper(self):
        '''
        Helper function to 'push' a new configuration to the camera.
        This function catches a common "I/O Busy" error and makes sure the configuration is set, even if the port is busy for a moment.
        '''
        success = False
        while not success:
            try:
                OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
                success = True
            except:
                pass
        return success

    def list_all_config(self):
        '''
        List all available configuration options communicated via USB and supported by gphoto2, including those not (yet) implemented in this class.
        Output: List of strings
        '''
        return [el[0] for el in gp.check_result(gp.gp_camera_list_config(self.camera))]
    
    def get_camera_mode(self):
        '''
        Detect whether the physical switch on the camera is set to photo or video mode
        Output: int 0 == PHOTO, 1 == VIDEO
        '''
        self.config = self.camera.get_config()
        switch = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmovieswitch'))
        value = gp.check_result(gp.gp_widget_get_value(switch))
        return int(value)
    
    def sync_date_time(self):
        '''
        Sync the camera's date and time with the connected computer's date and time.
        '''
        date_time = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'syncdatetimeutc'))
        date_time.set_value(1)
        OK = self.set_config_helper()
        date_time.set_value(0)
        OK = self.set_config_helper()
        return

    def get_config(self, config_name=None):
        '''
        Get the current value and all choices of a named configuration
        Output: tuple (string: current value, list of strings: choices)
        '''
        self.config = self.camera.get_config()
        if type(config_name)==str:
            config_name = config_name.lower()
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
                return None, None
        else:
            print(f"Config name must be a string")
            return None, None
        
    def get_file_info(self, file_path):
        '''
        Retrieve information about a specific file saved on the camera storage medium.
        Output: info object with variables info.file.size, info.file.type, info.file.mtime and more
        '''
        if type(file_path)==str:
            if len(file_path) > 0 and file_path[0] == '/' and file_path[-1] != '/':
                folder, name = os.path.split(file_path)
                try:
                    info = self.camera.file_get_info(folder, name)
                        # usage examples:
                        #size = info.file.size
                        #file_type = info.file.type
                        #timestamp = datetime.fromtimestamp(info.file.mtime).isoformat(' ')
                    return info
                
                except Exception as err:
                    if '-108' in str(err):
                        print(f"File {file_path} not found")
                    else:
                        print('Unhandled gphoto2 error: ' + err)
                    return None

            else:
                print(f"Please provide the absolute file path. Path {file_path} must be a string starting with '/' and ending with the file name")
                return None

    def list_files(self, path='/store_00020001/DCIM'):
        '''
        List all media files saved in the main media directory of the camera storage medium (default) or at another specified directory.
        Output: List of file paths (strings) in the given directory's immediate subdirectories. 
        '''
        if type(path)==str:
            if len(path) > 0 and path[0] == '/':
                dirs = [os.path.join(path, folder[0]) for folder in self.camera.folder_list_folders(path)]
                files = [os.path.join(folder,file_name[0]) for folder in dirs for file_name in self.camera.folder_list_files(folder)]
            else:
                print(f"Please provide the absolute path. Path {path} must be a string starting with '/'")
                return None
        else:
            print(f"Path must be a string")
            return None
        return files
    
    def download_file(self, camera_path, target_file=None):
        '''Download a specific file from the camera storage medium to the target file path on the PC.'''

        if type(camera_path)==str:
            if len(camera_path) > 0 and camera_path[0] == '/' and camera_path[-1] != '/':
                folder, name = os.path.split(camera_path)
                try:
                    cam_file = self.camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
                except Exception as err:
                    if '-108' in str(err):
                        print(f"File {camera_path} not found")
                    else:
                        print('Unhandled gphoto2 error: ' + err)
                    return None
                if target_file is None:
                    target_file = os.path.join('./', name)
                cam_file.save(target_file)
                return target_file
            else:
                print(f"Please provide the absolute file path. Path {camera_path} must be a string starting with '/' and ending with the file name")
                return None
        else:
            print(f"Camera path must be a string")
            return None
    
    def manual_focus(self, value=3):
        '''
        Manually drive the lens focus nearer or further in increments of three different sizes.
        This function will have to be called repeatedly to achieve a specific focus distance.
        To bring the focus point nearer, use [0,1,2] for [small, medium, large] increments.
        To bring the focus point further, use [4,5,6] for [small, medium, large] increments.
        Input: int 0-6
        Output: string describing the action taken
        '''
        # 0,1,2 == small, medium, large increment --> nearer
        # 3 == none
        # 4,5,6 == small, medium, large increment --> further 
        value = int(value)
        if 0 <= value <= 2:
            msg = 'Manually focussing nearer'
        elif 4 <= value <= 6:
            msg = 'Manually focussing farther'
        elif value == 3:
            msg = 'Manual focus drive set to neutral'
        else:
            msg = f'Manual focus drive failed, value {value} out of range'
            return msg
    
        mf = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'manualfocusdrive'))
        mf.set_value(list(mf.get_choices())[value])
        OK = self.set_config_helper()
        mf.set_value(list(mf.get_choices())[3]) # set back to 'None'
        OK = self.set_config_helper()
        return msg
    
    def get_capture_parameters(self):
        '''Get the current values for aperture, iso, shutter speed, and continuous auto focus.'''
        aperture = self.get_aperture()
        shutterspeed = self.get_shutterspeed()
        c_AF = self.get_continuous_AF()
        iso = self.get_iso()
        return aperture, iso, shutterspeed, c_AF
    
    def get_aperture(self):
        '''Get the current aperture (f-number) setting.'''
        self.config = self.camera.get_config()
        aperture = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'aperture'))
        current = 'AUTO' if aperture.get_value() == 'Unknown value 00ff' or aperture.get_value() == 'implicit auto' else aperture.get_value()
        return current
    
    def get_shutterspeed(self):
        '''Get the current shutter speed setting.'''
        self.config = self.camera.get_config()
        shutterspeed = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'shutterspeed'))
        current = 'AUTO' if shutterspeed.get_value() == 'bulb' or shutterspeed.get_value() == 'auto' else shutterspeed.get_value()
        return current
    
    def get_continuous_AF(self):
        '''Get the current continuous auto focus setting.'''
        self.config = self.camera.get_config()
        if self.mode == 0:
            config = 'continuousaf'
        else:
            config = 'movieservoaf'
        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        return c_AF.get_value()
    
    def get_iso(self):
        '''Get the current ISO setting.'''
        self.config = self.camera.get_config()
        if self.mode == 1:
            #TODO: Double check if there is no way to get this value in VIDEO mode
            return None
        iso = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'iso'))
        current = 'AUTO' if iso.get_value() == 'Auto' else iso.get_value()
        return current
    
    def set_capture_parameters(self, aperture=None, iso=None, shutterspeed=None, c_AF=None):
        '''Set the aperture, iso, shutter speed, and continuous auto focus.'''
        msgs = ''
        if aperture is not None:
            current_aperture, msg = self.set_aperture(aperture)
            msgs += msg
        if shutterspeed is not None:
            current_shutterspeed, msg = self.set_shutterspeed(shutterspeed)
            msgs += msg
        if c_AF is not None:
            current_cAF, msg = self.set_continuous_AF(c_AF)
            msgs += msg
        if iso is not None and self.mode == 0:
            current_iso, msg = self.set_iso(iso)
            msgs += msg
        else:
            current_iso = self.get_iso()

        current_aperture, current_iso, current_shutterspeed, current_cAF = self.get_capture_parameters()
        msgs += '... Capture parameters set. '
        return [current_aperture, current_iso, current_shutterspeed, current_cAF], msgs
    
    def set_aperture(self, value='AUTO'):
        '''
        Change the aperture (f-number). Always returns the (new) currently active setting.
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.
        Input: int, float, numeric string, or the string 'AUTO'
        Output: the current setting (string), a potential error message (string)

        WARNING: !! In VIDEO mode, AUTO setting is still untested. Might have to set 'Iris Mode' to 'Automatic' in the camera menu if you need auto aperture. !!
        '''
        self.config = self.camera.get_config()
        aperture = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'aperture'))
        msg = ''
        if value == 'AUTO':
            if self.mode == 0:
                value = 'Unknown value 00ff' # in PHOTO mode
            else:
                value = 'implicit auto' # in VIDEO mode
        else:
            try:
                value = float(value)
            except ValueError:
                msg = f"Value {value} not supported. Please use string 'AUTO' or a number (int/float/numeric string)."
                print(msg)
                print('Supported numeric values: ', self.aperture_choices)
                current = 'AUTO' if aperture.get_value() == 'Unknown value 00ff' else aperture.get_value()
                return current, msg

            # if the exact value specified is not supported, use the closest option
            if value not in self.aperture_choices:
                closest = min(self.aperture_choices, key=lambda x: abs(x - value))
                msg = f'Aperture of {value} not supported, using closest option (or reformatting) to {closest}'
                print(msg)
                value = closest
            # gphoto2 only accepts strings formated as proper decimal numbers or integers without trailing zeros
            if value == int(value):
                value = int(value)

        aperture.set_value(str(value))
        OK = self.set_config_helper()

        # check that the change has been applied
        self.config = self.camera.get_config()
        aperture = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'aperture'))
        current = 'AUTO' if aperture.get_value() == 'Unknown value 00ff' else aperture.get_value()
        return current, msg
    
    def set_shutterspeed(self, value='AUTO'):
        '''
        Change the shutter speed. Always treturns the (new) currently active setting.
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.
        Input: Numeric string of the form '1/50' or '0.5' or '25', or int/float, or the string 'AUTO'.
        Ooutput: the current setting (string), a potential error message (string)
        '''
        self.config = self.camera.get_config()
        shutterspeed = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'shutterspeed'))
        msg = ''
        if value == 'AUTO':
            if self.mode == 0:
                value = 'bulb'
            else:
                value = 'auto'
        else:
            if value not in self.shutter_choices:
                num_choices = [eval(choice) for choice in self.shutter_choices] # convert all string options to numeric values                
                if type(value) == int or type(value) == float:
                    num_value = value
                else:
                    try:
                        num_value = eval(value)
                    except NameError:
                        msg = f"Value {value} not supported. Please use string 'AUTO' or a number (int/float/numeric string)."
                        print(msg)
                        print('Supported numeric values: ', self.shutter_choices)
                        current = 'AUTO' if shutterspeed.get_value() == 'bulb' else shutterspeed.get_value()
                        return current, msg

                closest = self.shutter_choices[num_choices.index(min(num_choices, key=lambda x: abs(x - num_value)))]
                msg = f'Shutterspeed of {value} not supported, using closest option of {closest}'
                print(msg)
                value = closest
        
        shutterspeed.set_value(value)
        OK = self.set_config_helper()

        # Check that the change has been applied
        self.config = self.camera.get_config()
        shutterspeed = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'shutterspeed'))
        current = 'AUTO' if shutterspeed.get_value() == 'bulb' else shutterspeed.get_value()
        return current, msg
    
    def set_continuous_AF(self, value='Off'):
        '''
        Turn continuous auto focus on (1/'On') or off (0/'Off').
        Always treturns the (new) currently active setting.
        Works slightly differently in PHOTO and VIDEO mode, so both are unified in this method.
        Input: string 'On' or 'Off', or int 1 or 0, or bool True or False
        Output: the current setting (string 'On' or 'Off'), a potential error message
        '''
        if self.mode == 0:
            config = 'continuousaf'
        else:
            config = 'movieservoaf' # because the config is named differently in VIDEO mode

        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        value_dict = {0:'Off',1:'On', '0':'Off', '1':'On', 'False':'Off','True':'On','off':'Off','on':'On', 'Off':'Off', 'On':'On'} # gphoto2 only accepts the strings 'Off' and 'On' but this seems too restrictive
        if value not in value_dict:
            error_msg = f"Value {value} not supported. Please use 'Off' or 'On'."
            print(error_msg)
            return c_AF.get_value(), error_msg

        value = value_dict[value]
        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        c_AF.set_value(value)
        OK = self.set_config_helper()

        # Check that the change has been applied
        self.config = self.camera.get_config()
        c_AF = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config))
        current = c_AF.get_value()
        return current, ''

    def reset_after_abort(self):
        if self.mode == 0: # this refers to the mode at initialisation of this camera, not the current mode
            # The current mode might have been changed by the user, but we want to reset to the initial mode
            mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmoviemode'))
            mode.set_value(0)

            release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease')) 
            release.set_value('None')

            drive_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'drivemode'))
            drive_mode.set_value(list(drive_mode.get_choices())[0])
            OK = self.set_config_helper()
        else:

            rec_button = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'movierecordtarget'))
            rec_button.set_value('None')
            OK = self.set_config_helper()

        return 'Reset completed'
        
    def capture_image(self, aperture=None, iso=None, shutterspeed=None, c_AF=None, download=True, target_path='.'):
        '''
        Top-level API call to capture a single image.
        Optionally change the capture parameters before starting the capture.
        Selects the correct capture function based on camera mode.
        Input: aperture, iso, shutterspeed, c_AF: see set_capture_parameters()
                download: bool, whether to download the image to the target path
                target_path: string, path to the directory where the image will be saved
        Output: file_path: string, msg: string
        '''

        # Check if the camera is in the correct mode
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture static images"
            print(error_msg)
            return None, error_msg
        
        msgs = ''
        # Change capture parameters if requested
        input_params = [aperture, iso, shutterspeed, c_AF]
        if any(param is not None for param in input_params):
            current_params = self.get_capture_parameters()
            current_params = list(current_params)
            new_params = [current_params[i] if item is None else item for i, item in enumerate(input_params)]
            set_params, msg = self.set_capture_parameters(*new_params)
            msgs += msg

        # Trigger the capture
        success, file_path, msg = self.capture_immediate(download=download, target_path=target_path)
        msgs += msg

        return file_path, msgs
    
    def capture_video(self, aperture=None, iso=None, shutterspeed=None, c_AF=None, duration=1, target_path='.'):
        '''
        Top-level API call to capture a video.
        Selects the correct recording function based on camera mode.
        Optionally change the capture parameters before starting the recording.
        Input: aperture, iso, shutterspeed, c_AF: see set_capture_parameters()
                duration: float, duration of the recording in seconds
                target_path: string, path to the directory where the video will be saved
        Output: success: bool, file_path: string, msg: string
        '''

        msgs = ''
        # Change capture parameters if requested
        input_params = [aperture, iso, shutterspeed, c_AF]
        if any(param is not None for param in input_params):
            [current_params] = self.get_capture_parameters()
            new_params = [current_params[i] if item is None else item for i, item in enumerate(input_params)]
            __ , msg = self.set_capture_parameters(*new_params)
            msgs += msg

        if self.mode == 0:
            success, file_path, msg = self.record_preview_video(t=duration, target_path=target_path, resolution_prio=True)
        else:
            success, file_path, msg = self.record_video(t=duration, download=True, target_path=target_path)
        msgs += msg
        return success, file_path, msgs


    ''' PHOTO mode only methods'''

    def set_exposure_manual(self):
        '''
        Set the camera's auto-exposure mode to manual, so that shutter, aperture, and iso can be set remotely.
        Only supported in PHOTO mode.
        '''
        try:
            exp_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autoexposuremodedial'))
        except Exception as err:
            print(err)
            return
        exp_mode.set_value('Fv') # 'Fv' == Canon's 'Flexible-Priority Auto Exposure', useful for manual access
        OK = self.set_config_helper()

        # Check that the change has been applied
        self.config = self.camera.get_config()
        exp_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autoexposuremodedial'))
        success = exp_mode.get_value() == 'Fv'
        return success

    def set_iso(self, value='AUTO'):
        '''
        Change the ISO setting. Always returns the (new) currently active setting.
        Only supported in PHOTO mode.
        Input: int, numeric string, or string 'AUTO'
        Output: current value, potential error message
        '''
        self.config = self.camera.get_config()
        msg = ''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually set ISO."
            print(msg)
            return None, msg
        
        iso = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'iso'))

        if value == 'AUTO':
            iso.set_value('Auto')
        else:
            if type(value) == int or type(value) == float:
                value = round(value)
            elif type(value) == str:
                try:
                    value = round(eval(value))
                except NameError:
                    msg = f"Value {value} not supported. Please use string 'AUTO' or a number (int/float/numeric string)."
                    print(msg)
                    print('Supported numeric values: ', self.iso_choices)
                    return iso.get_value(), msg

            if value not in self.iso_choices:
                closest = min(self.iso_choices, key=lambda x: abs(x - value))
                msg = f'ISO of {value} not supported, using closest option of {closest}'
                print(msg)
                value = closest
            value = str(value)
            iso.set_value(value)
        OK = self.set_config_helper()

        # Check that the change has been applied
        self.config = self.camera.get_config()
        iso = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'iso'))
        current = 'AUTO' if iso.get_value() == 'Auto' else iso.get_value()
        return current, msg

    def set_image_format(self, value=0, list_choices=False):
        '''
        Change the target image format, or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Only supported in PHOTO mode.
        Input: value as int (choice index) or string (choice name)
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
        OK = self.set_config_helper()

        # Check that the change has been applied
        self.config = self.camera.get_config()
        im_format = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'imageformat'))
        current = im_format.get_value()
        return current, choices, msg
    
    def trigger_AF(self):
        '''
        Trigger auto-focus once. 
        It is currently not possible to check if focus has been achieved.
        This function might need to be called repeatedly to adjust focus.
        (Equivalent to the bash command --set-config autofocusdrive=1)
        Only supported in PHOTO mode.
        Output: string describing the action taken
        '''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually trigger auto focus"
            print(msg)
            return msg
        
        AF_action = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autofocusdrive'))
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 1))
        OK = self.set_config_helper()
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 0))
        OK = self.set_config_helper()
        return 'AF triggered once'
    
    def set_AF_location(self, x, y):
        '''
        Set the auto focus point to a specific pixel location.
        (Equivalent to the bash command --set-config eoszoomposition=x,y)
        Only supported in PHOTO mode.
        Input: x and y are int, supported range is the image resolution, normally (1,1) to (8192,5464)
        '''
        msg = ''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to manually set auto focus location"
            print(msg)
            return None, msg
        if type(x) != int or type(y) != int:
            msg = f"AF point {x},{y} not supported, please input values as integers."
            return None, msg
        
        AF_point = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eoszoomposition'))
        if 0 <= x <= 8192 and 0 <= y <= 5464:
            OK = gp.check_result(gp.gp_widget_set_value(AF_point, f"{x},{y}"))
            OK = self.set_config_helper()
            return f'{x},{y}', msg
        else:
            msg = f"AF point {x},{y} not supported, please input values between according to your selected image resolution, normally between 0 and 8192 for x and 0 and 5464 for y."
            return AF_point.get_value(), msg
    
    def live_preview(self, file_path='./live_preview.jpg'):
        '''
        Display preview frames on the PC until the user interrupts the preview with 'q'.
        Usually 960x640 at around 15 fps.
        The images are NOT saved on the device or pc.
        Note that the live preview is not available during capture. This function temporarily blocks the USB I/O. Stop the live preview before changing configurations or starting a capture.
        Only supported in PHOTO mode.'''
        if self.mode == 1:
            msg = "Camera must be in PHOTO mode to display live preview"
            print(msg)
            return msg
        
        from PIL import Image
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation 
        
        self.capture_preview(target_file=file_path)
        im = Image.open(file_path)
        ax1 = plt.subplot(111)
        im1 = ax1.imshow(im)

        def update_live_view(i):
            self.capture_preview(target_file=file_path)
            im = Image.open(file_path)
            im1.set_data(im)

        ani = FuncAnimation(plt.gcf(), update_live_view, interval=50)

        def close(event):
            if event.key == 'q':
                plt.close(event.canvas.figure)

        cid = plt.gcf().canvas.mpl_connect("key_press_event", close)
        print('Press q to quit')
        plt.show()
        return

    def capture_preview(self, target_file='./preview.jpg'):
        '''
        Capture a preview image (i.e. viewfinder frame, with the mirror up) and save it to the target file.
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
        Taken an immeditate capture, triggering the shutter but without triggering the auto-focus first.
        Optionally download the image to the target path.
        The file will also be saved to the device and the file name will follow the camera's set naming convention.
        Returns a boolean indicating success, the file path if saved to PC, and a message.
        Only supported in PHOTO mode.
        '''

        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture static images"
            print(error_msg)
            return False, None, error_msg
        
        release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease'))
        release.set_value('Immediate') # 5 == Immediate
        OK = self.set_config_helper()
        if download:
            timeout = time.time() + 5
            while True:
                # potentially need to catch exceptions here in case the new file event is not caught by this wait loop
                # loop times out after 10 seconds
                event_type, event_data = self.camera.wait_for_event(1000)
                if event_type == gp.GP_EVENT_FILE_ADDED:
                    cam_file = self.camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                    cam_file.save(target_path+'/'+event_data.name)
                    release.set_value('Release Full')
                    OK = self.set_config_helper()
                    return True, target_path+'/'+event_data.name, 'downloaded'
                elif time.time() > timeout:
                    error_msg = "Waiting for new file event timed out, capture may have failed."
                    print(error_msg)
                    release.set_value('Release Full')
                    OK = self.set_config_helper()
                    return False, None, error_msg
        release.set_value('Release Full')
        OK = self.set_config_helper()
        return True, None, 'saved to camera'
    
    def record_preview_video(self, t=1, target_path ='.', resolution_prio=False):
        '''
        Capture a series of previews (i.e. the viewfinder frames, with mirror up)
        for a duration of t seconds, and save them as a video file.
        The file will not be saved to the device.
        Note that this function will overwrite existing files in the specified location!
        Only supported in PHOTO mode.
        Inputs: t=duration in seconds (int or float), target_file=string with file path, resolution_prio=boolean
        '''
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture preview videos"
            print(error_msg)
            return False, None, error_msg
        
        target_file = target_path + '/prev_vid.mp4'
        if os.path.exists(target_file): # always overwrite existing file to prevent ffmpeg error
            os.remove(target_file)

        # if a higher resolution is the priority, record in 'eosmoviemode' at 1024x576 and ~25 fps
        # if a higher frame rate is the priority, record at 960x640 and close to ~60 fps
        if resolution_prio:
            mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmoviemode'))
            mode.set_value(1)
            OK = self.set_config_helper()
        else:
            frame_size = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'liveviewsize'))
            frame_size.set_value('Large') # set to max size: 960x640
            OK = self.set_config_helper()

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
            OK = self.set_config_helper()
        return True, target_file, 'saved to computer'
    
    def capture_burst(self, t=0.5, save_timeout=5):
        '''
        Shoot a quick burst of full-scale images for a duration of t seconds.
        Should achieve about 8-9fps. Returns a list of file locations on the camera.
        Only supported in PHOTO mode.
        Input: t=duration in seconds (int or float)
        '''
        if self.mode == 1:
            error_msg = "Camera must be in PHOTO mode to capture burst"
            print(error_msg)
            return False, None, error_msg

        # Set the drive mode to continuous shooting
        drive_mode = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'drivemode'))
        drive_mode.set_value(list(drive_mode.get_choices())[1])
        release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease'))
        OK = self.set_config_helper()

        # start shooting but activating remote trigger
        release.set_value('Immediate') # 5 == Immediate
        OK = self.set_config_helper()
        time.sleep(t) # wait for the desired duration
        # and turn the trigger OFF again
        release.set_value('Release Full')
        OK = self.set_config_helper()

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
        OK = self.set_config_helper()
        return True, files, 'saved to camera'


    ''' VIDEO mode only methods'''

    def record_video(self, t=1, download=True, target_path='.', save_timeout=5):
        '''
        Record a video for a duration of t seconds.
        Resolution and file formats are set in the camera's menu. Storage medium must be inserted.
        Only supported in VIDEO mode.
        Inputs: t=duration in seconds (int or float), download=boolean, target_path=string
        '''
        if self.mode == 0:
            error_msg = "Camera must be in VIDEO mode to record full-res videos"
            print(error_msg)
            return False, None, error_msg
        
        # recording
        rec_button = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'movierecordtarget'))
        rec_button.set_value('Card')
        OK = self.set_config_helper()
        time.sleep(t)
        rec_button.set_value('None')
        OK = self.set_config_helper()

        # fetching the file
        timeout = time.time() + save_timeout
        if download:
            while True:
                # potential for errors if the new file event is not caught by this wait loop
                event_type, event_data = self.camera.wait_for_event(1000)
                if event_type == gp.GP_EVENT_FILE_ADDED:
                    cam_file = self.camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                    cam_file.save(target_path+'/'+event_data.name)
                    return True, target_path+'/'+event_data.name, 'File downloaded to PC'
                elif time.time() > timeout:
                    error_msg = "Warning: Waiting for new file event timed out, capture may have failed."
                    print(error_msg)
                    return True, None, error_msg
        return True, None, 'saved to camera'

if __name__ == '__main__':

    cam1 = EOS()
    # cam1.live_preview()
    cam1.set_capture_parameters(aperture=2.8, shutterspeed=1/50, c_AF='Off')
    cam1.record_preview_video(t=2)
    cam1.capture_image()
    cam1.set_aperture(5.6)
    print("Camera initalised")
