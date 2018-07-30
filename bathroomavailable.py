import logging
from logging.handlers import RotatingFileHandler
import json

import requests
import RPi.GPIO as GPIO
import web
from web.webapi import BadRequest, Unauthorized

from hipchat_notify import hipchat_notify
from raspberrypi_utils.utils import ReadConfigMixin
from raspberrypi_utils.input_devices import LightSensor


log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log_filehandler = RotatingFileHandler(
    '/var/log/bathroomavailable/bathroomavailable.log',
    maxBytes=1024**2,
    backupCount=100
)
log_filehandler.setFormatter(log_formatter)
log_filehandler.setLevel(logging.INFO)

log_consolehandler = logging.StreamHandler()
log_consolehandler.setFormatter(log_formatter)
log_consolehandler.setLevel(logging.ERROR)

log = logging.getLogger(__name__)
log.addHandler(log_filehandler)
log.addHandler(log_consolehandler)
log.setLevel(logging.DEBUG)

utils_log = logging.getLogger('raspberrypi_utils.input_devices')
utils_log.setLevel(logging.DEBUG)
utils_log.addHandler(log_consolehandler)


class BathroomAvailable(ReadConfigMixin):
    def __init__(self):
        super(BathroomAvailable, self).__init__()
        self.config = self.read_config()
        GPIO.setmode(GPIO.BCM)
        self.sensor = LightSensor(
            self.config['Main']['SENSOR_PIN'],
            self.update,
            on_threshold=self.config['Main']['LIGHT_ON_THRESHOLD'],
            frequency=1,
        )
        self.is_master = self.config['Main']['MASTER']
        if self.is_master:
            self.bathroom_status = {
                self.config['Main']['BATHROOM_NAME']: None
            }
        log.info('Initialized')

    def send_notification(self, bathroom_name):
        print 'NOTIFICATION: {bathroom} light turned {status}'.format(
            bathroom=bathroom_name,
            status='ON' if self.bathroom_status[bathroom_name] else 'OFF'
        )
        log.debug('Notification sent: {}'.format(self.bathroom_status))
        if self.config['Main']['NOTIFICATION_HIPCHAT']:
            self.send_notification_hipchat()

    def send_notification_hipchat(self):
        message = '<ul>'
        for bathroom, occupied in self.bathroom_status.iteritems():
            message += '<li> {} is {}'.format(
                bathroom,
                'occupied' if occupied else 'available'
            )
        message += '</ul>'
        if all(self.bathroom_status.itervalues()):
            color = 'red'
        elif any(self.bathroom_status.itervalues()):
            color = 'yellow'
        else:
            color = 'green'

        try:
            hipchat_notify(
                self.config['HipChat']['AUTH_TOKEN'],
                self.config['HipChat']['ROOM'],
                message,
                color=color,
                format='html',
                host=self.config['HipChat']['SERVER'],
            )
        except requests.HTTPError as e:
            log.warn('HipChat notification failed to be sent: {}'.format(e))

    def update(self, light_on, bathroom_name=None):
        if bathroom_name is None:
            bathroom_name = self.config['Main']['BATHROOM_NAME']

        if self.is_master:
            previous_status = self.bathroom_status.get(bathroom_name, None)
            self.bathroom_status[bathroom_name] = light_on
            if previous_status != light_on:
                self.send_notification(bathroom_name)
        else:
            req = requests.post(
                self.config['Main']['MASTER_URL'],
                data={
                    'BathroomName': bathroom_name,
                    'Occupied': light_on,
                },
                headers={
                    'Authorization': 'Bearer {}'.format(self.config['Main']['AUTH_TOKEN']),
                }
            )
            if req.status_code != 200:
                log.warn('Error sending bathroom status to master: {}'.format(req.content))

    def status(self):
        return self.bathroom_status

    @staticmethod
    def cleanup():
        GPIO.cleanup()


class AuthorizedMixin(object):
    @staticmethod
    def authorized(auth):
        if auth and auth.startswith('Bearer'):
            bathroom_available = web.config.bathroom_available
            return auth[7:] == bathroom_available.config['Main']['AUTH_TOKEN']
        return False


class UpdateBathroomStatus(AuthorizedMixin):
    # noinspection PyPep8Naming
    def POST(self):
        auth = web.ctx.env.get('HTTP_AUTHORIZATION')
        if self.authorized(auth):
            try:
                data = web.input()
                bathroom_name = data.BathroomName
                occupied = data.Occupied
                if occupied.lower() not in ('true', 'false'):
                    return BadRequest()
                bathroom_available = web.config.bathroom_available
                bathroom_available.update(occupied.lower() == 'true', str(bathroom_name))
                web.header('Content-Type', 'application/json')
                return json.dumps(bathroom_available.status())
            except AttributeError:
                return BadRequest()
        else:
            return Unauthorized()


class GetBathroomStatus(AuthorizedMixin):
    # noinspection PyPep8Naming
    def GET(self):
        auth = web.ctx.env.get('HTTP_AUTHORIZATION')
        if self.authorized(auth):
            bathroom_available = web.config.bathroom_available
            web.header('Content-Type', 'application/json')
            return json.dumps(bathroom_available.status())
        else:
            return Unauthorized()
