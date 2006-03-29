import math
import time
import data
import tiltcorrelator

class Registration(object):
    def __init__(self, node, presets_client, calibration_clients, instrument,
                       viewer, settings, tilt_axis, target, emtarget,
                       move_type='image shift'):
        self.node = node
        self.move_type = move_type
        self.presets_client = presets_client
        self.calibration_clients = calibration_clients
        self.instrument = instrument
        self.viewer = viewer
        self.settings = settings
        self.target = target
        self.emtarget = emtarget

        self.preset_name = self.settings['registration preset order'][-1]

        self.correlator = tiltcorrelator.Correlator(self.settings['xcf bin'],
                                                    tilt_axis)

        self.registration_image = None

    def removeBacklash(self, tilts):
        preset = self.presets_client.getCurrentPreset()
        if preset is None:
            raise RuntimeError
        old_preset_name = preset['name']
        self.presets_client.toScope(self.preset_name, self.emtarget)

        # TODO: error handling
        self.instrument.setTEM(preset['tem']['name'])
        self.instrument.setCCDCamera(preset['ccdcamera']['name'])

        if self.registration_image is None:
            image_data = self.instrument.getData(data.CorrectedCameraImageData)
            self.registration_image = image_data['image']

        self.viewer.setImage(0, self.registration_image, shift=None)

        self.prepareStage(tilts)

        image_data = self.instrument.getData(data.CorrectedCameraImageData)
        image = image_data['image']
        self.viewer.setImage(1, image)

        self.correlator.reset()
        self.correlator.correlate(self.registration_image, 0)
        correlation_image = self.correlator.correlate(image, 0)
        shift = self.correlator.getShift(False)

        raw_shift = self.correlator.getShift(True)
        s = (raw_shift['x'], raw_shift['y'])
        self.viewer.setXC(correlation_image, s)

        target = data.AcquisitionImageTargetData(initializer=self.target)
        # reverse y
        target['delta row'] += shift['y']
        target['delta column'] -= shift['x']
        self.emtarget = self.node.targetToEMTargetData(target)
        self.node.publish(self.emtarget, database=True)
        self.presets_client.toScope(old_preset_name, self.emtarget)

        time.sleep(3.0)

        self.viewer.clearImages()

        return self.emtarget, shift
        
    def prepareStage(self, tilts):
        if len(tilts) < 2:
            raise ValueError
        #current_alpha = self.instrument.tem.StagePosition['a']
        delta = math.radians(5.0)
        if tilts[1] - tilts[0] > 0:
            alpha = tilts[0] - delta
        else:
            alpha = tilts[0] + delta
        self.instrument.tem.StagePosition = {'a': alpha}
        self.instrument.tem.StagePosition = {'a': tilts[0]}

