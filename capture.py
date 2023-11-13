import gphoto2 as gp
import subprocess as sp, logging, os
import gphoto_util
from PIL import Image
from datetime import datetime
import time

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
            choices = list(conf.get_choices())
            return value, choices
        else:
            print(f"Config {config_name} not found")
            return None
    
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
        Only supported in PHOTO mode.
        (Equivalent to the bash command --set-config eoszoomposition=x,y)
        Supported range is the image resolution, normally (1,1) to (8192,5464)
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
        '''
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
        '''
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
        '''
        # Capture an image without AF
        release = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosremoterelease'))
        release.set_value('Immediate') # 5 == Immediate
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        if download:
            timeout = time.time() + 10
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

    # def record(self, t=10):
    #     # Record video for a duration of t seconds
    #     pass

if __name__ == '__main__':
    #port = gphoto_util.choose_camera()
    #ports = gphoto_util.detect_EOS_cameras()
    cam1 = EOS(port=None)
    #cam1.set_AF_location(1,1)
    #value, choices = cam1.get_config('shutterspeed')
    #file_location = cam1.capture_preview(show=False)
    #cam1.trigger_AF()
    #cam1.list_files()
    #cam1.capture_image(AF=False)
    #cam1.get_file_info(file_path='/store_00020001/DCIM/103_1109/IMG_0426.JPG')
    cam1.download_file(camera_path='/store_00020001/DCIM/103_1109/IMG_0426.JPG')
    #config_names = cam1.list_all_config()
    print("Camera initalised")
