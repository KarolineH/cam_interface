import gphoto2 as gp
import subprocess as sp, logging, os
import gphoto_util
from PIL import Image

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
        self.mode = self.get_camera_mode() #  # 0 = PHOTO, 1 = VIDEO
        #self.config = gp.check_result(gp.gp_camera_list_config(self.camera))

    def list_all_config(self):
        return [el[0] for el in gp.check_result(gp.gp_camera_list_config(self.camera))]
    
    def get_camera_mode(self):
        # this determines whether the physical switch on the camera is set to photo or video mode
        # 0 = PHOTO, 1 = VIDEO
        switch = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eosmovieswitch'))
        value = gp.check_result(gp.gp_widget_get_value(switch))
        return int(value)
    
    def get_config(self, config_name=''):
        if config_name in self.list_all_config():
            conf = gp.check_result(gp.gp_widget_get_child_by_name(self.config, config_name))
            value = gp.check_result(gp.gp_widget_get_value(conf))
            choices = list(conf.get_choices())
            return value, choices
        else:
            print(f"Config {config_name} not found")
            return None
    
    def trigger_AF(self):
        # Trigger auto-focus
        # equivalent to bash command --set-config autofocusdrive=1
        # only works in PHOTO mode
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
        # Define a pixel position for the auto focus point
        # only works in PHOTO mode
        # equivalent to bash command --set-config eoszoomposition=x,y
        # range normally (1,1) to (8192,5464)
        if self.mode == 1:
            print("Camera must be in PHOTO mode to manually set auto focus location")
            return
        AF_point = gp.check_result(gp.gp_widget_get_child_by_name(self.config, 'eoszoomposition'))
        OK = gp.check_result(gp.gp_widget_set_value(AF_point, f"{x},{y}"))
        OK = gp.check_result(gp.gp_camera_set_config(self.camera, self.config))
        return
    
    def capture_preview(self, target_path='./preview.jpg', show=True):
        camera_file = gp.check_result(gp.gp_camera_capture_preview(self.camera))
        camera_file.save(target_path)
        if show:
            img = Image.open(target_path)
            img.show()
        return target_path



    def capture_image(self, AF=True):
        if AF:
            try:
                file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE) # Capture_image always triggers AF and ONLY captures an image when AF was successful, otherwise returns I/O error
            except gp.GPhoto2Error as er:
                if '-110' in er.args[0]:
                    print("I/O error, Auto-focus failed. Taking immediate capture instead.")
        else: 
            self.capture_immediate()

    # def capture_immediate(self):
    #     target = os.path.join('.', 'test_capture.jpg')
    #     camera_file = self.camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
    #     camera_file.save(target)
    #     return
    #     # 3 followed by 8 does AF and trigger 
    #     # 2 and 5 (immediate) seems to always just trigger shutter
    #     # 3 followed by 6 only does AF
    

    def record(self, t=10):
        # Record video for a duration of t seconds
        pass


if __name__ == '__main__':
    #port = gphoto_util.choose_camera()
    #ports = gphoto_util.detect_EOS_cameras()
    cam1 = EOS(port=None)
    #cam1.set_AF_location(1,1)
    #value, choices = cam1.get_config('shutterspeed')
    #file_location = cam1.capture_preview(show=False)
    #cam1.trigger_AF()
    cam1.capture_image()
    #config_names = cam1.list_all_config()
    print("Camera initalised")
