import gphoto2 as gp
import subprocess as sp, logging, os
import gphoto_util
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
    
    def download_file(self, camera_path, target_path='.'):
        '''Download a specific file saved on the device to the target path on the PC.'''
        folder, name = os.path.split(camera_path)
        cam_file = self.camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
        target_file = os.path.join(target_path, name)
        cam_file.save(target_file)
        return
    
    def manual_focus(self, step=6):
        '''
        Manually drive the focus nearer or further in three different increment sizes.
        This function will have to be called repeatedly to achieve a specific focus distance.
        To bring the focus point nearer, use [0,1,2] for [small, medium, large] increments.
        To bring the focus point further, use [4,5,6] for [small, medium, large] increments.
        '''

        # 0,1,2 == small, medium, large increment --> nearer
        # 3 == none
        # 4,5,6 == small, medium, large increment --> further 
        mf = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'manualfocusdrive'))
        mf.set_value(list(mf.get_choices())[step])
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        mf.set_value(list(mf.get_choices())[3]) # set back to 'None'
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return


    ''' PHOTO mode only methods'''

    def set_image_format(self, format=0, list_choices=False):
        '''
        Change the target image format, or optionally only list the available options.
        Always treturns the (new) currently active setting.
        Only supported in PHOTO mode.
        '''
        im_format = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'imageformat'))
        choices = list(im_format.get_choices())
        if list_choices:
            for i in range(len(choices)):
                print(i, choices[i])
            return im_format.get_value()
        OK = gp.check_result(gp.gp_widget_set_value(im_format, choices[format]))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return choices[format]
    
    def trigger_AF(self):
        '''
        Trigger auto-focus once. 
        It is currently not possible to check if focus has been achieved.
        This function might need to be called repeatedly to adjust focus.
        (Equivalent to the bash command --set-config autofocusdrive=1)
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to manually trigger auto focus")
            return
        AF_action = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'autofocusdrive'))
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 1))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        OK = gp.check_result(gp.gp_widget_set_value(AF_action, 0))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return
    
    def set_AF_location(self, x, y):
        '''
        Set the auto focus point to a specific pixel location.
        (Equivalent to the bash command --set-config eoszoomposition=x,y)
        Supported range is the image resolution, normally (1,1) to (8192,5464)
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to manually set auto focus location")
            return
        AF_point = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eoszoomposition'))
        OK = gp.check_result(gp.gp_widget_set_value(AF_point, f"{x},{y}"))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return
    
    def capture_preview(self, target_file='./preview.jpg', show=True):
        '''
        Capture a preview image (i.e. viewfinder frame, with the mirror up) and save it to the target file.
        Optionally display the image.
        The taken image is NOT saved on the device, only on the computer.
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to capture a preview")
            return
        camera_file = gp.check_result(gp.gp_camera_capture_preview(self.camera))
        camera_file.save(target_file)
        if show:
            img = Image.open(target_file)
            img.show()
        return target_file

    def capture_image(self, download=True, target_path='.', AF=True):
        '''
        Capture an image, optionally download it to the computer and save it to the target path.
        The file will also be saved to the device and the file name will follow the camera's set naming convention.
        Optionally trigger auto-focus before capturing the image, or capture immediately.
        If the auto-focus fails, an immediate capture will be taken instead. 
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to capture static images")
            return
        if AF:
            try:
                file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE) # Capture_image always triggers AF and ONLY captures an image when AF was successful, otherwise returns I/O error
                if download:
                    camera_file = self.camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
                    camera_file.save(target_path+'/'+file_path.name)
                    return
            except gp.GPhoto2Error as er:
                if '-110' in er.args[0]:
                    print("I/O error, Auto-focus failed. Taking immediate capture instead.")
                    self.capture_immediate(download, target_path)
        else: 
            self.capture_immediate(download, target_path)

    def capture_immediate(self, download=True, target_path='.'):
        '''
        Taken an immeditate capture, without triggering the auto-focus first.
        Optionally download the image to the target path.
        The file will also be saved to the device and the file name will follow the camera's set naming convention.
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to capture static images")
            return
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
                    return
                elif time.time() > timeout:
                    print("Waiting for new file event timed out, please find the file saved on the device.")
                    release.set_value('None')
                    OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
                    return
        release.set_value('None')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return
    
    def record_preview_video(self, t=1, target_file ='./prev_vid.mp4', resolution_prio=False):
        '''
        Capture a series of previews (i.e. the viewfinder frames, with mirror up)
        for a duration of t seconds, and save them as a video file.
        The file will not be saved to the device.
        Note that this function will overwrite existing files in the specified location!
        Only supported in PHOTO mode.
        '''
        if self.mode == 1:
            print("Camera must be in PHOTO mode to capture preview videos")
            return
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
        return


    ''' VIDEO mode only methods'''


    def record_video(self, t=1, download=True, target_path='.'):
        '''
        Record a video for a duration of t seconds.
        Resolution and file formats are set in the camera's menu. Storage medium must be inserted.
        Only supported in VIDEO mode.
        '''
        if self.mode == 0:
            print("Camera must be in VIDEO mode to record full-res videos")
            return
        rec_button = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'movierecordtarget'))
        rec_button.set_value('Card')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        time.sleep(t)
        rec_button.set_value('None')
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
    
        timeout = time.time() + 5
        if download:
            while True:
                # potential for errors if the new file event is not caught by this wait loop
                # loop times out after 10 seconds
                event_type, event_data = self.camera.wait_for_event(1000)
                if event_type == gp.GP_EVENT_FILE_ADDED:
                    cam_file = self.camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                    cam_file.save(target_path+'/'+event_data.name)
                    return
                elif time.time() > timeout:
                    print("Waiting for new file event timed out, please find the file saved on the device.")
                    return
        return

if __name__ == '__main__':
    #port = gphoto_util.choose_camera()
    #ports = gphoto_util.detect_EOS_cameras()
    cam1 = EOS(port=None)
    #cam1.set_AF_location(1,1)
    #value, choices = cam1.get_config('autofocusdrive')
    #file_location = cam1.capture_preview(show=False)
    #cam1.capture_immediate(download=False)
    #cam1.trigger_AF()
    #cam1.list_files()
    #cam1.capture_image(AF=False)
    #cam1.get_file_info(file_path='/store_00020001/DCIM/103_1109/IMG_0426.JPG')
    #cam1.download_file(camera_path='/store_00020001/DCIM/103_1109/IMG_0426.JPG')
    #cam1.record_video()
    #cam1.manual_focus(step=3)
    #cam1.record_preview_video(t=4, target_file ='./res_first.mp4', resolution_prio=True)
    #config_names = cam1.list_all_config()
    cam1.set_image_format(list_choices=True)
    cam1.set_image_format(0)

    cam1.capture_image(AF=True)
    print("Camera initalised")
