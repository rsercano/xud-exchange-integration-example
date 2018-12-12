import context
import xudrpc_pb2
import xudrpc_pb2_grpc
import grpc
from core import cancel_all_xud_orders


def load_credentials(cert='./tls.cert'):
    with open(cert, 'rb') as f:
        cert = f.read()
    return grpc.ssl_channel_credentials(root_certificates=cert)  # Need binary cert not string!


def xud_list_pairs():
    if context.channel is None:
        return
    stub = xudrpc_pb2_grpc.XudStub(context.channel)
    request = xudrpc_pb2.ListPairsRequest()
    response = stub.ListPairs(request)
    print('Currency Pairs: %s' % (', '.join(response.pairs)))


def xud_get_info():
    if context.channel is None:
        return
    stub = xudrpc_pb2_grpc.XudStub(context.channel)
    request = xudrpc_pb2.GetInfoRequest()
    response = stub.GetInfo(request)
    # print(response)
    print('Connected to xud %s pub_key: %s\n' % (response.version, response.node_pub_key))
    xud_list_pairs()
    print('\nBTC Lightning Channels: %s' % (response.lndbtc.channels.active))
    print('LTC Lightning Channels: %s' % (response.lndltc.channels.active))


# def xud_get_orders():
#     global stub
#     request = xudrpc_pb2.GetOrdersRequest(pair_id='LTC/BTC', include_own_orders=True)
#     response = stub.GetOrders(request)
#     print(response)

def pair():
    return '%s/%s' % (context.Q, context.P)


def xud_place_order(order_id, side, quantity, price):
    if context.channel is None:
        # print("xud is not connected!")
        return
    stub = xudrpc_pb2_grpc.XudStub(context.channel)
    xud_side = xudrpc_pb2.BUY if side == 'buy' else xudrpc_pb2.SELL
    request = xudrpc_pb2.PlaceOrderRequest(price=price, quantity=quantity, pair_id=pair(), order_id='test-%s-%s' % (context.boot_timestamp, order_id), side=xud_side)
    # print('[XUD]PlaceOrder: order_id=%s, side=%s, quantity=%s, price=%s' % (order_id, side, quantity, price))
    for response in stub.PlaceOrder(request):
        print(response)


def xud_execute_swap(order_id, peer_pub_key, quantity):
    if context.channel is None:
        # print("xud is not connected!")
        return
    try:
        stub = xudrpc_pb2_grpc.XudStub(context.channel)
        request = xudrpc_pb2.ExecuteSwapRequest(pair_id=pair(), order_id=order_id, peer_pub_key=peer_pub_key, quantity=quantity)
        print('[XUD]ExecuteSwap: order_id=%s, peer_pub_key=%s, quantity=%s' % (order_id, peer_pub_key, quantity))
        response = stub.ExecuteSwap(request)
        print("--------------SWAP--------------")
        print(response)
    except Exception as e:
        print("Failed to swap", e)


def handle_connect(cmd):
    if context.channel is not None:
        print("Already connected!")
        return
    try:
        context.channel = grpc.secure_channel('%s:%s' % (context.host, context.port), load_credentials(context.cert))
        xud_get_info()
        from xud_subscribe import begin_xud_subscription
        begin_xud_subscription()
    except Exception as e:
        print("Failed to connect", e)


def handle_disconnect(cmd):
    if context.channel is None:
        print("Already disconnected!")
        return
    try:
        context.channel.close()
        context.channel = None
        cancel_all_xud_orders()
    except Exception as e:
        print("Failed to disconnect", e)
