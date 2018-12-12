import context
from decimal import Decimal
import functools
from time import time


class User:
    def __init__(self, name):
        self.name = name
        self.balance = {}
        self.orders = []

    def __repr__(self):
        return "User{name=%s, balance=%s, orders=%s}" % (self.name, self.balance, self.orders)


class Match:
    def __init__(self, order, quantity, price):
        self.order = order
        self.quantity = quantity
        self.price = price

    def __repr__(self):
        return "Match{order=%s, quantity=%s, price=%s}" % (self.order.id, self.quantity, self.price)


class Order:
    id = 0

    def __init__(self, user, side, quantity, price=None, extra={}):
        Order.id = Order.id + 1
        self.id = Order.id
        self.user = user
        self.side = side
        self.quantity = Decimal(quantity)
        self.original_quantity = Decimal(quantity)
        self.price = Decimal(price) if price is not None else None
        self.matches = []
        self.status = 'PENDING'
        self.reject_reason = None
        self.extra = extra
        context.publish_order_feed(OrderFeed(order=self))

    def __repr__(self):
        return "Order{id=%s, user=%s, side=%s, quantity=%s/%s, price=%s, status=%s, reject_reason=%s, matches=%s, extra=%s}" % (self.id, self.user.name, self.side, self.quantity, self.original_quantity, self.price, self.status, self.reject_reason, self.matches, self.extra)


class OrderFeed:

    def __init__(self, order):
        self.timestamp = time()
        self.order = order

    def __repr__(self):
        return "OrderFeed{order=%s}" % (self.order,)


class SettlementFeed:

    def __init__(self, taker, maker, price, quantity):
        self.timestamp = time()
        self.taker = taker
        self.maker = maker
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return "SettlementFeed{taker=%s, maker=%s, price=%s, quantity=%s}" % (self.taker, self.maker, self.price, self.quantity)


def compare_buy(a, b):
    p = Decimal.compare(b.price, a.price)
    if p == 0:
        return a.id - b.id
    return p


def compare_sell(a, b):
    p = Decimal.compare(a.price, b.price)
    if p == 0:
        return a.id - b.id
    return p


def get_peers(order):
    peers = []

    if order.side == 'buy':
        peers = context.sell
    elif order.side == 'sell':
        peers = context.buy

    return peers


def accept_price(order, price):
    if order.side == 'buy':
        return order.price >= price
    elif order.side == 'sell':
        return order.price <= price


def do_place(order):
    if order.side == 'buy':
        context.buy.append(order)
        context.buy = list(sorted(context.buy, key=functools.cmp_to_key(compare_buy)))
    elif order.side == 'sell':
        context.sell.append(order)
        context.sell = list(sorted(context.sell, key=functools.cmp_to_key(compare_sell)))
    # if order.user is not context.xud:
    #     xud_place_order(order.id, order.side, order.quantity, order.price)


def do_settlement(order):
    if order.user == context.xud:
        return
    for match in order.matches:
        context.publish_settlement_feed(SettlementFeed(taker=order, maker=match.order, price=match.price, quantity=match.quantity))
        peer = match.order
        if peer.user == context.xud:
            # xud_execute_swap(peer.extra["xud_order_id"], peer.extra["peer_pub_key"], match.quantity)
            total = match.quantity * match.price
            if order.side == 'buy':
                order.user.balance[context.Q] += match.quantity
                order.user.balance[context.P] -= total
            elif order.side == 'sell':
                order.user.balance[context.Q] -= match.quantity
                order.user.balance[context.P] += total
        else:
            total = match.quantity * match.price
            if order.side == 'buy':
                order.user.balance[context.Q] += match.quantity
                order.user.balance[context.P] -= total
                peer.user.balance[context.Q] -= match.quantity
                peer.user.balance[context.P] += total
            elif order.side == 'sell':
                order.user.balance[context.Q] -= match.quantity
                order.user.balance[context.P] += total
                peer.user.balance[context.Q] += match.quantity
                peer.user.balance[context.P] -= total


def handle_market_order(order):
    order.status = 'MATCHING'

    context.publish_order_feed(OrderFeed(order=order))

    peers = get_peers(order)

    total = 0
    for peer in peers:
        total += peer.quantity
    if total < order.quantity:
        order.status = 'REJECTED'
        order.reject_reason = 'INSUFFICIENT_MARKET_DEPTH'
        print('Insufficient market depth')
        return
    remain = order.quantity
    while len(peers) > 0 and remain > 0:
        first = peers[0]
        if remain >= first.quantity:
            q = first.quantity
            remain = remain - first.quantity
            first.quantity = 0
            first.status = 'CLOSED'
            order.matches.append(Match(order=first, quantity=q, price=first.price))
            peers.pop(0)
        else:
            q = remain
            remain = 0
            first.quantity = first.quantity - remain
            order.matches.append(Match(order=first, quantity=q, price=first.price))

    order.quantity = remain

    order.status = 'CLOSED'

    context.publish_order_feed(OrderFeed(order=order))

    if len(order.matches) > 0:
        do_settlement(order)

    # print(order)


def handle_limit_order(order):
    order.status = 'MATCHING'

    context.publish_order_feed(OrderFeed(order=order))

    peers = get_peers(order)

    remain = order.quantity
    while len(peers) > 0 and remain > 0 and accept_price(order, peers[0].price):
        first = peers[0]
        if remain >= first.quantity:
            q = first.quantity
            remain = remain - first.quantity
            first.quantity = 0
            first.status = 'CLOSED'
            order.matches.append(Match(order=first, quantity=q, price=order.price))
            peers.pop(0)
        else:
            q = remain
            remain = 0
            first.quantity = first.quantity - remain
            order.matches.append(Match(order=first, quantity=q, price=order.price))

    order.quantity = remain

    if remain > 0:
        order.status = 'OPEN'
        do_place(order)
    else:
        order.status = 'CLOSED'

    context.publish_order_feed(OrderFeed(order=order))

    if len(order.matches) > 0:
        do_settlement(order)

    # print(order)


def cancel_order(order_id):
    result = list(filter(lambda x: x.id == order_id, context.orders))
    if len(result) == 0:
        print("Not found!")
        return
    target = result[0]
    if target.status == 'OPEN':
        target.status = 'CANCELLED'
        if target.side == 'buy':
            context.buy.remove(target)
        elif target.side == 'sell':
            context.sell.remove(target)
        context.publish_order_feed(OrderFeed(order=target))
    else:
        print('Too late to cancel')
        return


def cancel_all_xud_orders():
    xud_orders = []
    for order in context.buy:
        if order.user == context.xud:
            xud_orders.append(order.id)
    for order in context.sell:
        if order.user == context.xud:
            xud_orders.append(order.id)
    for order_id in xud_orders:
        cancel_order(order_id)
