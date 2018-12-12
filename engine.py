import context
from decimal import Decimal
import sys
from print import print_balance, print_help, print_orderbook, print_orders, print_users, print_banner
from core import Order, handle_limit_order, handle_market_order, cancel_order
from xud_api import handle_connect, handle_disconnect, xud_place_order, xud_execute_swap


def handle_deposit(cmd):
    if context.user is None:
        print("Login first")
        return
    parts = cmd.split()
    if len(parts) < 2:
        print("Missing <currency>")
        return
    if len(parts) < 3:
        print("Missing <amount>")
        return
    currency = parts[1]
    amount = parts[2]
    context.user.balance[currency] = context.user.balance[currency] + Decimal(amount)


def handle_login(cmd):
    parts = cmd.split()
    if len(parts) < 2:
        print("Missing user!")
        return
    name = parts[1]
    result = list(filter(lambda u: u.name == name, context.users))
    if len(result) == 0:
        print("No such user: %s" % name)
        return
    context.user = result[0]


def place_order(cmd):
    if context.user is None:
        print("Login first")
        return
    parts = cmd.split()
    side = parts[0]
    if len(parts) < 2:
        print("Missing <quantity>[@<price>]")
        return
    qp = parts[1]
    if '@' in qp:
        nums = qp.split('@')
        order = Order(context.user, side, quantity=nums[0], price=nums[1])
        context.orders.append(order)
        handle_limit_order(order)
    else:
        order = Order(context.user, side, quantity=qp)
        context.orders.append(order)
        handle_market_order(order)


def place_xud_order(quantity, price, order_id, side, peer_pub_key, created_at):
    order = Order(context.xud, side, quantity, price, extra={
        "xud_order_id": order_id,
        "peer_pub_key": peer_pub_key,
        "created_at": created_at,
    })
    context.orders.append(order)
    if price is None:
        handle_market_order(order)
    else:
        handle_limit_order(order)


def cancel_order1(cmd):
    if context.user is None:
        print("Login first")
        return
    parts = cmd.split()
    if len(parts) < 2:
        print("Missing <orderId>")
    order_id = int(parts[1])
    cancel_order(order_id)


def cancel_xud_order(order_id):
    result = list(filter(lambda x: "xud_order_id" in x.extra and x.extra["xud_order_id"] == order_id, context.orders))
    if len(result) == 0:
        print("Not found!")
        return
    target = result[0]
    cancel_order(target.id)


def subscribe_order_feeds(feed):
    # print(feed)
    if feed.order.user is not context.xud and feed.order.status == 'OPEN':
        xud_place_order(feed.order.id, feed.order.side, feed.order.quantity, feed.order.price)


def subscribe_settlement_feeds(feed):
    # print(feed)
    peer = feed.maker
    if peer.user == context.xud:
        xud_execute_swap(peer.extra["xud_order_id"], peer.extra["peer_pub_key"], feed.quantity)


def run():

    context.subscribe_order_feeds(subscribe_order_feeds)
    context.subscribe_settlement_feeds(subscribe_settlement_feeds)

    while True:
        if context.user is None:
            cmd = input('\n> ')
        else:
            cmd = input('\n(%s) > ' % context.user.name)
        if cmd == 'exit':
            break
        elif cmd.startswith('login'):
            handle_login(cmd)
        elif cmd == 'logout':
            context.user = None
        elif cmd.startswith('buy') or cmd.startswith('sell'):
            place_order(cmd)
        elif cmd.startswith('cancel'):
            cancel_order1(cmd)
        elif cmd.startswith('balance'):
            print_balance(cmd)
        elif cmd == 'orderbook':
            print_orderbook()
        elif cmd.startswith('connect'):
            handle_connect(cmd)
        elif cmd.startswith('disconnect'):
            handle_disconnect(cmd)
        elif cmd.startswith('deposit'):
            handle_deposit(cmd)
        elif cmd.startswith('orders'):
            print_orders(cmd)
        elif cmd.startswith('users'):
            print_users(cmd)
        elif cmd == 'help':
            print_help()
        else:
            print('Bad command: ' + cmd)
            print('Type `help` for some helps')


if __name__ == '__main__':
    print_banner(sys.argv[1])
    host = sys.argv[2]
    port = sys.argv[3]
    cert = sys.argv[4]
    run()
