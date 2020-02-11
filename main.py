# -*- coding: utf-8 -*-
import redis
import time
import thread
import threading
import json
import ESL
from psycopg2.pool import ThreadedConnectionPool
from repoze.lru import lru_cache
from config import PHONE, DSN, REDIS, DISTRIBUTORS, CHANNELS, ESL_DSN, LOGGER


@lru_cache(maxsize=100)
def get_distributor(pg_pool, phone):
    if len(phone) == PHONE.get('short'):
        code = PHONE.get('code', '')
        phone = '{}{}'.format(code, phone)
    if len(phone) != 10:
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
                distributor, cut_code, distributor_id = 'inter_city', None, 0

    return distributor


def channel(data, red, pg_pool):
    data = json.loads(data[u'data'])
    LOGGER.debug('Start channel %s', data)
    phone = data.get('phones', [])[0]
    distributor = get_distributor(pg_pool, phone)
    if not distributor:
        red.publish('CALLBACK:ORIGINATE:NO_DISTRIBUTOR', json.dumps(data))
        LOGGER.warning('Distributor for %s not found!', phone)
        return

    LOGGER.debug('%s: %s', distributor, phone)
    data['distributor'] = distributor
    DISTRIBUTORS.get(distributor).acquire()

    esl = ESL.ESLconnection(*ESL_DSN)
    red.publish('CALLBACK:ORIGINATE:ACCEPTED', json.dumps(data))

    if esl.connected:
        red_db = redis.Redis(REDIS, db=1)
        phone = '+7{}'.format(phone)
        uuid = esl.api('create_uuid').getBody()
        data[u'uuid'] = uuid
        red.publish('CALLBACK:ORIGINATE:STARTED', json.dumps(data))
        red_db.set(uuid, data['message'])
        originate_data = "{origination_uuid=%s,originate_timeout=%s,ignore_early_media=true}sofia/gateway/${distributor(%s)}/%s 6500" % (
            uuid, 20, distributor, phone)
        resp = esl.api('expand originate', originate_data.encode('UTF-8'))
        data['result'] = json.loads(resp.serialize('json'))['_body']
        code, _data = data['result'].split(' ')
        if code == '+OK':
            red.publish('CALLBACK:ORIGINATE:DELIVERED', json.dumps(data))
            time.sleep(15)
        elif code == '-ERR':
            red.publish('CALLBACK:ORIGINATE:%s' %
                        _data.upper(), json.dumps(data))
        else:
            red.publish('CALLBACK:ORIGINATE:UNKNOWN_ERROR',
                        json.dumps(data))
        esl.disconnect()
        red_db.delete(uuid)
        red_db.close()
    else:
        LOGGER.error('Esl %s not connected!', ESL_DSN[0])
    DISTRIBUTORS.get(distributor).release()


def main():
    LOGGER.info('Starting main thread.')
    pg_pool = ThreadedConnectionPool(*DSN)
    pool = redis.ConnectionPool(host=REDIS)
    r = redis.Redis(connection_pool=pool)
    rs = r.pubsub()
    rs.subscribe(CHANNELS)
    LOGGER.debug('Listening redis channels %s', CHANNELS)
    for event in rs.listen():
        LOGGER.debug('Received %s', event)
        if event['type'] == 'message':
            _channel = thread.start_new_thread(
                channel, (event, r, pg_pool))
            LOGGER.debug('%s: %s', _channel, event)


if __name__ == '__main__':
    m = threading.Thread(target=main)
    m.start()
    m.join()
