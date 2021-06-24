import numpy as np

class myStock:
    InitCut = 0.01
    OperCut = 2
    SaveDays = 3

    def __init__(self, name):
        self.name   = name
        self.prices = np.array([])
        self.hands  = np.array([])
        self.opers  = np.array([]) # number of operations that satisfy the cuts
        self.maxs   = np.array([])
        self.mins   = np.array([])
        self.pricesToday = np.array([])
        self.buyToday = 0
        self.maxSell  = 0
        self.isInit   = False

    def buy(self, price, hand):
        np.append(self.prices, price)
        np.append(self.hands, hand)
        self.buyToday += hand

    def sell(self, hand):
        if hand > self.maxSell:
            hand = self.maxSell
        if hand <= self.hands[-1]:
            self.hands[-1] -= hand
        else:
            while hand > self.hands[-1]:
                hand -= self.hands[-1]
                self.hands  = self.hands[:-1]
                self.prices = self.prices[:-1]
        self.maxSell -= hand

    def countOperation(self):
        self.pricesToday

        return count

    def updatePricesToday(self, pricesToday):
        self.pricesToday = pricesToday

    def nextDay(self):
        while len(self.opers) >= SaveDays:
            self.opers = self.opers[1:]
        while len(self.maxs) >= SaveDays:
            self.maxs = self.maxs[1:]
        while len(self.mins) >= SaveDays:
            self.mins = self.mins[1:]
        count = self.countOperation()
        np.append(self.opers, count)
        np.append(self.maxs, max(self.pricesToday))
        np.append(self.mins, min(self.pricesToday))
        if self.opers.all() >= OperCut:
            self.isInit = True
        else:
            self.isInit = False
        self.maxSell += self.buyToday
        self.buyToday = 0
        self.pricesToday = np.array([])