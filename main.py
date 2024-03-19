from fastapi import FastAPI

import socketio
import uvicorn
from starlette.staticfiles import StaticFiles

from data import lot_json, flat_lot
from utils.sentry import configure_sentry

BID_INCREMENT = 50.0

configure_sentry()

app = FastAPI()

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

app.mount('/static', StaticFiles(directory='static'), name='static')
app.add_route('/socket.io/', route=socket_app, methods=['OPTIONS', 'GET', 'POST'])
app.add_websocket_route('/socket.io/', socket_app)

connected_users: dict = {}
next_bid: float = 0
track_record: list = []


def authenticate_user(data):
    sid = data.get('sid')
    token = data.get('token')
    lot_id = data.get('lot_id')
    return {'user_id': sid, 'lot_id': lot_id}


@app.get('/')
async def root():
    return {'Hello': 'World'}


@app.get('/lots/{lot_id}')
async def lot(lot_id: str):
    return lot_json


@app.get('/lots/{lot_id}/auction-live')
async def auction_live(lot_id: str):
    return flat_lot


@sio.event
async def message(sid, data):
    session = await sio.get_session(sid)
    if session:
        bid = data.get('bid')
        next_bid = float(bid) + BID_INCREMENT
        next_bid_format = f'{next_bid:.2f}'
        current_bid_format = f'{float(bid):.2f}'
        payload = {
            'action': 'bid',
            'nextBid': next_bid_format,
            'userId': session['user_id'],
            'message': f'<strong>{session["user_id"][-4:]}</strong> has propuesto <strong> US$ {current_bid_format}</strong>'
        }
        track_record.append(payload)
        await sio.emit('message', payload, room=session['lot_id'])


@sio.event
async def authenticate(sid, data):
    data['sid'] = sid
    user = authenticate_user(data)
    if user:
        await sio.save_session(sid, {'user_id': user['user_id'], 'lot_id': user['lot_id']})
        await sio.enter_room(sid, user['lot_id'])
        if user['lot_id'] not in connected_users:
            connected_users[user['lot_id']] = set()

        if sid not in connected_users[user['lot_id']]:
            connected_users.setdefault(user['lot_id'], set()).add(sid)
        # else:
        #     await sio.disconnect(sid)

        initial_payload = {
            'action': 'initial',
            'messages': track_record
        }
        payload = {
            'action': 'totalConnected',
            'number': len(connected_users[user['lot_id']])
        }
        await sio.emit('message', initial_payload, room=sid)
        await sio.emit('message', payload, room=user['lot_id'])
    # else:
    #     await sio.disconnect(sid)


@sio.event
async def connect(sid, environ):
    print(f'User connect: {sid}')


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    if session:
        if session.get('lot_id') in connected_users:
            connected_users[session['lot_id']].discard(sid)

        payload = {
            'action': 'totalConnected',
            'number': len(connected_users[session['lot_id']])
        }
        await sio.emit('message', payload, room=session['lot_id'])
    print(f'User disconnected: {sid}')


def start_server():
    uvicorn.run('main:app', host='0.0.0.0', port=8085, lifespan='on', reload=True)


if __name__ == '__main__':
    start_server()
