from time import time
from decimal import Decimal
from core import User

buy = []
sell = []
user = None

orders = []
users = []
P = 'BTC'
Q = 'LTC'
channel = None
host = 'localhost'
port = 8886
cert = 'tls.cert'

boot_timestamp = time()

# alice = User('alice')
alice = User('satoshi')
alice.balance[P] = Decimal(1)
alice.balance[Q] = Decimal(1)

# bob = User('bob')
bob = User('charlie')
bob.balance[P] = Decimal(1)
bob.balance[Q] = Decimal(1)

xud = User('xud')

users.append(alice)
users.append(bob)

order_feeds_subscribers = []
settlement_feeds_subscribers = []


def subscribe_order_feeds(subscriber):
    order_feeds_subscribers.append(subscriber)


def subscribe_settlement_feeds(subscriber):
    settlement_feeds_subscribers.append(subscriber)


def publish_order_feed(feed):
    for sub in order_feeds_subscribers:
        sub(feed)


def publish_settlement_feed(feed):
    for sub in settlement_feeds_subscribers:
        sub(feed)
