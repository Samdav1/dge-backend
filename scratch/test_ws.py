import asyncio
import websockets
import sys

async def test_ws():
    token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMDU3MjM0OS00NTJkLTRmODAtOWE0Yy1iMjRiMmI5NDFhNDciLCJleHAiOjE3ODE1NDc0NzB9.ssR7CICYe-GJivo0VqrEMhAad23v9vInjaBfr22w703ZLBuhFCIT_mJYu0QjS7LIEW1rqd951MEOBZWDBjTcHM84-mDuJAyhkymi1n9YNQnboT_qMNVdCphOf50CEgx4nvdNjQp8Hq0FnYAo6YZKNZynu3ms8YMVrAd7S4wwgnhjgdrAyOlei1iOB4QHMmjeq6x6Elk29Mbjxnc5ix5pgtnUaeOeo1BJKrODiGQzl4I_rfjhj-G3_5XESXUobMramo1wM9n2B34bWk2uBy4MKZPOMH7W8cYborx2B_26DJNytP-crE-QXSacNERNE3j8vuFoUni2Rhzk3QqFOrXitSmz1da3VqpWULxRNhL8c1NSomcZGhta_zmp1p9eQgb2V64afSQ65kyXXf65MNT9FR1UOD109kaCVtyNs4Vqx6-_wu4UzHInWlKAkPJSb1sEtIpCkOiWJxRRZeE9NB7R5D1uLvNqK0Zz9Z1XTwe03MatxWEr43EY4rJuc8WZQyST9_FN7jYVVYQWsxuqLhXUk563TyMyBDH8DaY5l1m0O8FmUjAdkR0fPtwjNlDrDRTUFLmk1n-n_l7fyXb87mqr8JTzuXdZs7uO-TDelXPeSU7KYU9mN9bJy4rvtuGvDIJ61jssORJrYTt_58qC8Kl8yDUGBQyK6v0lgW-qaZSNi4s"
    uri = f"wss://dge.dgetechs.com/chat/ws?token={token}"
    print(f"Connecting to: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.send('{"action": "join", "conversation_id": "test"}')
            response = await websocket.recv()
            print(f"Received response: {response}")
    except Exception as e:
        print(f"Failed to connect: {e}", file=sys.stderr)

asyncio.run(test_ws())
