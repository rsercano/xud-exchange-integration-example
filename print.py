import context
from termcolor import colored


class Column:

    def __init__(self, id, title="Untitled", type="text", width=10, render=None):
        self.id = id
        self.title = title
        self.type = type
        self.width = width

        def default_render(row):
            return '%s' % vars(row)[id]

        self.render = default_render if render is None else render


class Table:

    def __init__(self, columns=(), rows=(), gap=3, padding=2):
        self.columns = columns
        self.rows = rows
        self.gap = gap
        self.padding = padding

    def __repr__(self):
        total_width = 0
        result = ""
        gap_space = " " * self.gap
        padding_space = " " * self.padding

        for column in self.columns:
            total_width += column.width
        total_width += (len(self.columns) - 1) * self.gap + self.padding * 2

        result += "=" * total_width + "\n"

        f1 = gap_space.join(list(map(lambda c: "%%-%ds" % c.width, self.columns)))
        result += padding_space + f1 % tuple(map(lambda c: '%s' % c.title, self.columns)) + padding_space + "\n"

        result += "-" * total_width + "\n"

        def m(c):
            if c.type == 'number':
                return "%%%ds" % len(c.title) + " " * (c.width - len(c.title))
            else:
                return "%%-%ds" % c.width

        f2 = gap_space.join(list(map(m, self.columns)))
        for row in self.rows:
            result += padding_space + f2 % tuple(map(lambda c: c.render(row), self.columns)) + padding_space + "\n"

        result += "=" * total_width + "\n"

        return result


def print_orderbook_entry(order):
    text = '   %-13s%s' % (order.price, order.quantity)
    if order.side == 'sell':
        if order.user == context.xud:
            print(colored(text, 'red'))
        else:
            print(colored(text, 'red', attrs=['dark']))
    elif order.side == 'buy':
        if order.user == context.xud:
            print(colored(text, 'green'))
        else:
            print(colored(text, 'green', attrs=['dark']))


def print_orderbook():
    print("============================")
    print(" Price(%s)   Quantity(%s) " % (context.Q, context.P))
    print("----------------------------")
    for e in reversed(context.sell):
        print_orderbook_entry(e)
    for e in context.buy:
        print_orderbook_entry(e)
    print("============================")


def print_users(cmd):
    for u in context.users:
        print(u)


def print_orders(cmd):
    if context.user is None:
        print("Login first!")
        return
    result = list(filter(lambda x: x.user == user, context.orders))

    c1 = Column(id='id', title='  #', type='number', width=5)
    c3 = Column(id='side', title='Side', type='text', width=5)
    c4 = Column(id='quantity', title='Quantity', type='number', render=lambda r: '%s/%s' % (r.quantity, r.original_quantity))
    c5 = Column(id='price', title='Price', type='number', width=6)
    c6 = Column(id='status', title='Status', type='text', width=7)

    table = Table(columns=[c1,c3,c4,c5,c6], rows=result)

    print(table)


def print_help():
    print("login <user>")
    print("logout")
    print("buy/sell <quantity>[@<price>]")
    print("cancel <orderId>")
    print("balance [<currency>]")
    print("deposit <currency> <amount>")
    print("orders")
    print("orderbook")
    print("connect [<host>] [<port>]")
    print("disconnect")
    print("help")
    print("exit")


def print_balance(cmd):
    if context.user is None:
        print("Login first")
        return
    parts = cmd.split()
    if len(parts) == 1:
        for key in context.user.balance:
            print('%s: %s' % (key, context.user.balance[key]))
    else:
        print(context.user.balance[parts[1]])


def print_banner(banner):
    file = open(banner, 'r')
    print(file.read())
