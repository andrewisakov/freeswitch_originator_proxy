#!/usr/bin/python2
# -*- coding: utf-8 -*-
import redis
import json
import freeswitch as fs


LOG = fs.consoleLog
REDIS = '192.168.222.90'


def get_variables(session, *variables):
    return [session.getVariable(v) for v in variables]


def hangup_hook(session, what, args=''):
    LOG("info", "hangup_hook from %s->what: %s, %s" % (
        session, what, args
    ))


def input_callback(session, what, obj, args=''):
    LOG("info", "input_callback from %s->what: %s, %s" % (
        session, what, obj
    ))


def get_callback_data(uuid):
    red_db = redis.Redis(REDIS, db=1)
    data = red_db.get(uuid)
    data = json.loads(data)
    return data


def playback(session, message):
    for p in message:
        LOG("debug", "callback handler callback_data: %s\n" %
            p.encode('UTF-8'))
        session.execute("playback", p.encode('UTF-8'))


def redis_push_event(event, data):
    if event:
        redcon = redis.Redis(REDIS)
        redcon.pubsub()
        redcon.publish(event, json.dumps(data))
        redcon.close()


def handler(session, args):
    uuid, recipient, caller, dest = get_variables(
        session, ["uuid", "recipient", "caller_id_number", "destination_number"])
    LOG("info", "callback handler PRE-ANSWER callback from %s for destination %s, uuid is %s\n" %
        (caller, dest, uuid))
    session.answer()
    session.setHangupHook(hangup_hook)
    session.setInputCallback(input_callback)
    fs.consoleLog(
        "info", "callback handler PLAYBACK callback handler from %s -> %s, uuid is %s\n" % (caller, dest, uuid))

    callback_data = get_callback_data(uuid)

    if 'choice' not in callback_data:
        playback(session, callback_data['message'])
    else:
        choices = callback_data['choice']
        tries = callback_data.get('tries', 3)
        timeout = callback_data.get('timeout', 5000)
        p = callback_data['message'][0]
        digits = session.playAndGetDigits(
            1, 1, tries, timeout, "", p.encode('UTF-8'), "", "\\d{1}")

        event = choices.get(digits)
        order_id = callback_data.get('order_id')
        redis_push_event(event, {'order_id': order_id})
