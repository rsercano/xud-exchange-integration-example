import context
from engine import place_xud_order, cancel_xud_order
import xudrpc_pb2
import xudrpc_pb2_grpc
from decimal import Decimal
from _thread import start_new_thread
import grpc


def subscribe_added_orders():
    try:
        stub = xudrpc_pb2_grpc.XudStub(context.channel)
        request = xudrpc_pb2.SubscribeAddedOrdersRequest(existing=True)
        # print('[XUD]SubscribeAddedOrders')
        for response in stub.SubscribeAddedOrders(request):
            #print("------------ADDED------------")
            #print(response)
            if not response.is_own_order:
                qq = round(response.quantity, 4)
                place_xud_order(str(qq), str(response.price), response.id, 'sell' if response.side == xudrpc_pb2.SELL else 'buy', response.peer_pub_key, response.created_at)
    except Exception as e:
        if e.code() != grpc.StatusCode.CANCELLED:
            print('Failed to subscribe added orders', e.code(), e.details())


def subscribe_removed_orders():
    try:
        stub = xudrpc_pb2_grpc.XudStub(context.channel)
        request = xudrpc_pb2.SubscribeRemovedOrdersRequest()
        # print('[XUD]SubscribeRemovedOrders')
        for response in stub.SubscribeRemovedOrders(request):
            #print("-----------REMOVED-----------")
            #print(response)
            cancel_xud_order(response.order_id)
    except Exception as e:
        if e.code() != grpc.StatusCode.CANCELLED:
            print('Failed to subscribe removed orders', e.code(), e.details())

# order_id: "323c5320-f9f8-11e8-a0e9-75f4ab14fe23"
# local_id: "test-1544171166.0081122-21"
# pair_id: "LTC/BTC"
# quantity: 1.0
# r_hash: "5989278d46c6c338b67fca51811b8f4bcf153e63fd05690a2b7d0e13e71ac657"
# amount_received: 780000
# amount_sent: 100000000
# peer_pub_key: "028fd9e98ca12820aab1ce974c8de42d6b75327a38de5603ff6f2cf87f529b4808"
# role: MAKER
# currency_received: "BTC"
# currency_sent: "LTC"

def handle_xud_swap(swap):
    order_id = int(swap.local_id[23:])
    # print('order_id', order_id)
    q = Decimal(str(swap.quantity))
    result = list(filter(lambda x: x.id == order_id, context.orders))
    if len(result) == 0:
        print('Not found such order %s for swap %s' % (order_id, swap))
        return
    order = result[0]

    # print(order)

    if order.quantity > q:
        order.quantity -= q
    else:
        order.quantity = 0
        order.status = 'CLOSED'
        if order.side == 'buy':
            context.buy.remove(order)
        elif order.side == 'sell':
            context.sell.remove(order)

    # change user balance here
    if order.side == 'buy':
        order.user.balance[context.P] -= Decimal(str(swap.amount_sent)) / Decimal('100000000')
        order.user.balance[context.Q] += Decimal(str(swap.amount_received)) / Decimal('100000000')
    elif order.side == 'sell':
        order.user.balance[context.Q] -= Decimal(str(swap.amount_sent)) / Decimal('100000000')
        order.user.balance[context.P] += Decimal(str(swap.amount_received)) / Decimal('100000000')


def subscribe_swaps():
    try:
        stub = xudrpc_pb2_grpc.XudStub(context.channel)
        request = xudrpc_pb2.SubscribeSwapsRequest()
        # print('[XUD]SubscribeSwaps')
        for response in stub.SubscribeSwaps(request):
            print("------------SWAPS------------")
            print(response)
            handle_xud_swap(response)
    except Exception as e:
        if e.code() != grpc.StatusCode.CANCELLED:
            print('Failed to subscribe swaps', e.code(), e.details())


def begin_xud_subscription():
    start_new_thread(subscribe_added_orders, ())
    start_new_thread(subscribe_removed_orders, ())
    start_new_thread(subscribe_swaps, ())

