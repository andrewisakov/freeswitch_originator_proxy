#!/usr/bin/python2
# -*- coding: utf-8 -*-
import redis
import time
import thread
import threading
import json
import ESL  # Поэтому 2.7
from psycopg2.pool import ThreadedConnectionPool
from cached_property import cached_property_with_ttl
from config import (
    PHONE, DSN, REDIS, DISTRIBUTORS,
    CHANNELS, ESL_DSN, LOGGER,
    TIMEOUT_DELIVERED, ORIGINATE_TIMEOUT,
)


# @cached_property_with_ttl(ttl=300)
def get_distributor(pg_pool, phone):
    if len(phone) == PHONE.get('short'):
        code = PHONE.get('code', '')
        phone = '{}{}'.format(code, phone)
    if len(phone) != 10:
        LOGGER.warning('Incorrect phone number {}!'.format(phone))
        return
    distributor = None
    with pg_pool.getconn() as pgcon:
        with pgcon.cursor() as c:
            SELECT = (
                'select dst.name, dst.cut_code, dst.id '
                'from routes_mask roma '
                'join operators op on (op.id=roma.operator_id) '
                'left join distributors dst on (dst.id=op.distributor_id) '
                'join regions reg on (reg.id=roma.region_id) '
                'where (aaa=%(code)s and %(digits)s between range_a and range_b) and '
                'dst.is_active and (dst.all_home or reg.is_home) '
                'order by roma.timestamp desc '
                'limit 1;'
            )
            c.execute(SELECT,
                      {'code': phone[:3], 'digits': phone[3:]})

            try:
                distributor, cut_code, distributor_id = c.fetchone()
            except Exception as e:
                LOGGER.error('{}'.format(str(e)))
                distributor, cut_code, distributor_id = 'inter_city', None, 0

    return distributor


def channel(data, red, pg_pool):
    data = json.loads(data[u'data'])
    LOGGER.debug('Start channel %s', data)
    phone = data.get('phones', [])
    if not phone:
        return
    phone = phone[0]
    distributor = get_distributor(pg_pool, phone)
    if not distributor:
        red.publish('CALLBACK:ORIGINATE:NO_DISTRIBUTOR', json.dumps(data))
        LOGGER.warning('Distributor for %s not found!', phone)
        return

    data['distributor'] = distributor
    LOGGER.debug('%s: %s', distributor, phone)

    DISTRIBUTORS.get(distributor).acquire()  # Захват дистрибьютора

    esl = ESL.ESLconnection(*ESL_DSN)
    red.publish('CALLBACK:ORIGINATE:ACCEPTED', json.dumps(data))

    if esl.connected:
        red_db = redis.Redis(REDIS, db=1)
        phone = '+7{}'.format(phone)
        uuid = esl.api('create_uuid').getBody()
        data[u'uuid'] = uuid
        red.publish('CALLBACK:ORIGINATE:STARTED', json.dumps(data))
        red_db.set(uuid, json.dumps(data['message']))
        red_db.expire(uuid, 800)
        originate_data = "{origination_uuid=%s,originate_timeout=%s,ignore_early_media=true}sofia/gateway/${distributor(%s)}/%s 6550" % (
            uuid, ORIGINATE_TIMEOUT, distributor, phone)
        resp = esl.api('expand originate', originate_data.encode('UTF-8'))
        data['result'] = json.loads(resp.serialize('json'))['_body']

        code, _data = data['result'].split(' ')
        data = json.dumps(data)
        if code == '+OK':
            event = 'CALLBACK:ORIGINATE:DELIVERED'
            LOGGER.info('{}: {}'.format(code, data))
            time.sleep(TIMEOUT_DELIVERED)
        elif code == '-ERR':
            event = 'CALLBACK:ORIGINATE:%s' % _data.upper()
            LOGGER.error('{}: {}'.format(code, data))
        else:
            event = 'CALLBACK:ORIGINATE:UNKNOWN_ERROR'
            LOGGER.error('{}: {}'.format(code, data))
        red.publish(event, data)

        esl.disconnect()
        red_db.close()
    else:
        LOGGER.error('Esl %s not connected!', ESL_DSN[0])
    DISTRIBUTORS.get(distributor).release()  # Освобождение дистрибютора


def main():
    LOGGER.info('Starting main thread.')
    LOGGER.debug('Registered distributors: %s', str({k: v._initial_value for k, v in DISTRIBUTORS.items()}))
    pg_pool = ThreadedConnectionPool(*DSN)
    pool = redis.ConnectionPool(host=REDIS)
    r = redis.Redis(connection_pool=pool)
    rs = r.pubsub()
    rs.subscribe(*CHANNELS)
    LOGGER.debug('Listening redis channels %s', CHANNELS)
    for event in rs.listen():
        LOGGER.debug('Received %s', event)
        if event['type'] == 'message':
            _channel = thread.start_new_thread(
                channel, (event, r, pg_pool))
            LOGGER.debug('%s: %s', _channel, event)


if __name__ == '__main__':
    try:
        m = threading.Thread(target=main)
        m.start()
        m.join()
    except KeyboardInterrupt as e:
        exit(0)
