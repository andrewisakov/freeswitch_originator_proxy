import os
import sys
import yaml
import xmltodict
from threading import BoundedSemaphore
import logger as _logger

SERVICE_ROOT_DIR = os.path.dirname(__file__)
sys.path.append(SERVICE_ROOT_DIR)

CONFIG = yaml.safe_load(open(os.path.join(SERVICE_ROOT_DIR, 'config.yaml')))
# REDIS = 'redis://{}'.format(CONFIG.get('redis', {}).get('host'))
REDIS = CONFIG.get('redis', {}).get('host')
CHANNELS = CONFIG.get('redis', {}).get('channels')
DSN = CONFIG.get('dsn')
DSN = (DSN.get('minsize'), DSN.get('maxsize'), 'postgres://{}:{}@{}/{}'.format(
    DSN.get('user'), DSN.get('password'), DSN.get('host'), DSN.get('database')
))
FREESWITCH = CONFIG.get('freeswitch', {})
DISTRIBUTORS = xmltodict.parse(open(os.path.join(FREESWITCH.get(
    'path'), FREESWITCH.get('distributors'))))
DISTRIBUTORS = DISTRIBUTORS.get(u'configuration', {}).get(
    u'lists', {}).get(u'list', [])
DISTRIBUTORS = {d[u'@name']: BoundedSemaphore(
    len(d[u'node'])) for d in DISTRIBUTORS if d.get('node')}

ESL_DSN = FREESWITCH.get('esl')
PHONE = CONFIG.get('phone', {})
TIMEOUT_DELIVERED = FREESWITCH.get('timeout_delivered', 15)
ORIGINATE_TIMEOUT = FREESWITCH.get('originate_timeout', 20)
LOGGER = _logger.rotating_log(
    os.path.join(
        SERVICE_ROOT_DIR, 'logs/originator.log',
    ), 'originator')
