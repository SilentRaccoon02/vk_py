import datetime
import json
import psycopg2
import requests
import time

with open('config.json') as file:
    config = json.load(file)

TOKEN = config['vk']['token']
VERSION = config['vk']['version']
GROUP_ID = config['vk']['group_id']
OFFSET_SIZE = config['vk']['offset_size']
USER_LIMIT = config['vk']['user_limit']
SUB_LIMIT = config['vk']['sub_limit']

assert OFFSET_SIZE <= 1000
assert SUB_LIMIT <= 500

CON = psycopg2.connect(
    host=config['db']['host'],
    port=config['db']['port'],
    user=config['db']['user'],
    password=config['db']['password'],
    database=config['db']['name']
)


def time_delta(start_time):
    delta = datetime.datetime.now() - start_time

    return delta - datetime.timedelta(microseconds=delta.microseconds)


def smart_request(url, params):
    response = requests.get(url, params=params)

    for i in range(4, 64, 2):
        if 'response' not in response.json():
            time.sleep(0.1 * i)
            response = requests.get(url, params=params)

        else:
            break

    return response


def get_count():
    method = 'groups.getMembers'
    url = f'https://api.vk.com/method/{method}'

    params = {
        'access_token': TOKEN,
        'v': VERSION,
        'group_id': GROUP_ID,
        'count': 0,
        'offset': 0
    }

    response = smart_request(url, params)
    data = response.json()['response']
    count = data['count']

    return count


def get_users(offset):
    method = 'groups.getMembers'
    url = f'https://api.vk.com/method/{method}'

    params = {
        'access_token': TOKEN,
        'v': VERSION,
        'group_id': GROUP_ID,
        'count': OFFSET_SIZE,
        'offset': offset
    }

    response = smart_request(url, params)
    data = response.json()['response']
    user_ids = data['items']
    users = ','.join(str(item) for item in user_ids)

    return users


def get_users_info(users):
    method = 'users.get'
    url = f'https://api.vk.com/method/{method}'

    params = {
        'access_token': TOKEN,
        'v': VERSION,
        'user_ids': users,
    }

    response = smart_request(url, params)
    data = response.json()['response']
    info = []

    for item in data:
        if 'deactivated' not in item and not item['is_closed']:
            info.append((item['id'], item['first_name'], item['last_name']))

    return info


def get_subs(user_id):
    method = 'users.getSubscriptions'
    url = f'https://api.vk.com/method/{method}'

    params = {
        'access_token': TOKEN,
        'v': VERSION,
        'user_id': user_id,
    }

    response = smart_request(url, params)
    data = response.json()['response']
    count = data['groups']['count']
    sub_ids = data['groups']['items']

    if count > SUB_LIMIT:
        sub_ids = sub_ids[0:SUB_LIMIT]

    subs = ','.join(str(item) for item in sub_ids)

    return subs


def get_subs_info(subs):
    method = 'groups.getById'
    url = f'https://api.vk.com/method/{method}'

    params = {
        'access_token': TOKEN,
        'v': VERSION,
        'group_ids': subs,
    }

    response = smart_request(url, params)
    data = response.json()['response']
    info = []

    for item in data:
        info.append((item['id'], item['name']))

    return info


def receive_users():
    count = get_count()
    request_queue = count // OFFSET_SIZE + 1
    sequence = [i * 1000 for i in range(0, request_queue)]

    print('Group ID:', GROUP_ID)
    print('Members count:', count)
    print('Offset size:', OFFSET_SIZE)
    print('Request queue:', request_queue)

    start_time = datetime.datetime.now()

    for item in sequence:
        print(f'\r\bReceiving: {item // 1000 + 1}/{request_queue} {time_delta(start_time)}', end='')
        users = get_users(item)
        info = get_users_info(users)

        with CON:
            cur = CON.cursor()
            cur.executemany('INSERT INTO users (user_id, first_name, last_name) VALUES (%s, %s, %s)', info)

    print(f'\r\bReceiving: <ready> {time_delta(start_time)}')


def receive_one(user_id):
    try:
        subs = get_subs(user_id)

        if not len(subs):
            with CON:
                cur = CON.cursor()
                cur.execute('DELETE FROM users WHERE user_id = %s', (user_id,))

            return

        info = get_subs_info(subs)

    except KeyError as e:
        raise KeyError(f'problem with user https://vk.com/id{user_id}') from e

    for item in info:
        with CON:
            cur = CON.cursor()
            cur.execute('SELECT (id, sub_id, sub_name) FROM subs WHERE sub_id = %s', (item[0],))
            sub = cur.fetchone()

            if sub is None:
                cur.execute('INSERT INTO subs (sub_id, sub_name) VALUES (%s, %s)', item)

            cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            cur.execute('INSERT INTO users_subs (user_id, sub_id) VALUES (%s, %s)', (user_id, item[0]))
            cur.execute('UPDATE users SET status = 1 WHERE user_id = %s', (user_id,))


def receive_subs():
    with CON:
        cur = CON.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        total_users = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM subs')
        total_subs = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM users WHERE status = 1')
        processed_count = cur.fetchone()[0]
        cur.execute('SELECT user_id FROM users WHERE status = 0 LIMIT %s', (USER_LIMIT,))
        user_ids = cur.fetchall()

    print(f'Subs:\n  '
          f'Total: {total_subs}\n  '
          f'Limit: {SUB_LIMIT}')

    print(f'Users:\n  '
          f'Total: {total_users}\n  '
          f'Processed: {processed_count}\n  '
          f'Limit: {USER_LIMIT}\n  '
          f'Queue: {len(user_ids)}')

    i = 0
    start_time = datetime.datetime.now()

    for item in user_ids:
        i += 1

        print(f'\r\bReceiving: {processed_count + i}/{total_users} {time_delta(start_time)}', end='')
        receive_one(item[0])

    if processed_count + i == total_users:
        print(f'\r\bReceiving: <ready> {time_delta(start_time)}')


def main():
    with CON:
        cur = CON.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        count = cur.fetchone()[0]

    if not count:
        print('Database is empty')
        receive_users()

    receive_subs()


if __name__ == '__main__':
    main()
