# HTLCProductsSim.py
#
#   A library for simulating financial products based on hash oracles
#
#   Copyright 2019 Christopher J. Sanborn
#
#   MIT License
#
# Classes contained within:
#
#   class Pair         - A currency pair (e.g. "USD:CNY")
#   class Price        - A price of one currency in another
#   class AssetBag     - A quantity of a currency
#   class Account      - A collection of quantities of currencies
#   class OracleHash   - A "hash" with a condition on preimage revelation
#   class HashTranche  - An HTLC contract using an OracleHash
#   class Contract ... - A collection of HashTranches and destination accounts.
#                        May also be populated with metadata to guide plotting
#                        and introspection of contracts.
#
# Import with:
#
#   from HTLCProductsSim import *
#
# Suggested approach: Derive specialized contracts from Contract. See
# BoundedStableCoin.py for an example.
#
#.

class Pair:
    # A currency pair, e.g. "USD:BTS".
    # Represents, validates, and compares currency pairs.
    def __init__(self, pairstring):
        symbols = pairstring.split(':')
        if len(symbols) != 2:
            raise ValueError("Symbol count != 2")
        for sym in symbols:
            AssetBag.assertSymbolValid(sym)
        self.base = symbols[0]
        self.quote = symbols[1]

    def __str__(self):
        return self.base + ':' + self.quote

    def swap(self):
        return Pair(self.quote+':'+self.base)

    def compat(self, other):
        if self.base == other.base and self.quote == other.quote:
            return True
        if self.base == other.quote and self.quote == other.base:
            return True
        return False

    def same(self, other):
        if self.base == other.base and self.quote == other.quote:
            return True
        return False

    @staticmethod
    def isValidPair(pairstring):
        try:
            pair = Pair(pairstring)
        except ValueError:
            return False
        return True


class Price:
    #
    #  Price(   20, "USD:BTS")   means:  One USD costs 20 BTS
    #  Price( 0.05, "BTS:USD")   means:  One BTS costs 0.05 USD
    #  Price("20 USD:BTS")       alias for: Price(20, "USD:BTS")
    #
    def __init__(self, price, pairstring=None):
        if isinstance(price, str):
            temp = Price.fromString(price)
            price = temp.price
            pairstring = str(temp.pair)
        self.price = price
        self.pair = Pair(pairstring)

    @staticmethod
    def linspace(start, finish, numel, pairstring):
        prices = [start + (finish-start)*i/(numel-1) for i in range(numel)]
        return [Price(p, pairstring) for p in prices]

    def __str__(self):
        return "%g %s" % (self.price, self.pair)

    def flip(self):
        return Price(1/self.price, str(self.pair.swap()))

    def express(self, pairstring):
        raise Unimplemented from ValueError

    def __mul__(self, other):  # multiplication by a scalar
        return Price(float(other) * self.price, str(self.pair))
    __rmul__=__mul__

    def __gt__(self, other):
        if not self.pair.same(other.pair):
            raise ValueError("Incompatible prices")
        return self.price > other.price
    def __lt__(self, other):
        return other > self
    def __ge__(self, other):
        return not other > self
    def __le__(self, other):
        return not self > other

    @staticmethod
    def fromString(pricestring):
        parts = pricestring.split()
        if len(parts) != 2:
            raise ValueError
        price = float(parts[0])
        return Price(price, parts[1])


class AssetBag:
    #
    # A numeric balance and an asset symbol.
    #
    #   instance = AssetBag(1.0 "BTS")
    #   instance = AssetBag("1.0 BTS")  # also works
    #
    # The following methods are mutators:
    #
    #   .absorb(other)     -  Increases bag by amount of other, if compatible
    #   .setAmount(amount) -  Sets amount
    #
    precisions = {}   # Precision table, e.g. {"USD": 2, "CNY":, 2}
    #
    def __init__(self, amount, symbol=None):
        if isinstance(amount, str):
            temp_ab = AssetBag.fromString(amount)
            amount = temp_ab.amount
            symbol = temp_ab.symbol
        AssetBag.assertSymbolValid(symbol)
        self.amount = amount
        self.symbol = symbol

    def absorb(self, other):    # mutates
        if self.symbol == other.symbol:
            self.amount += other.amount
        else:
            raise ValueError("Incompatible Assets")

    def setAmount(self, amount): # mutates
        self.amount = amount

    def compatible(self, other):
        return self.symbol == other.symbol

    def clone(self):
        return AssetBag(self.amount, self.symbol)

    def valuation(self, quote, knownprices):
        # Provides value of (self) expressed in units of 'quote' (an asset symbol),
        # provided a compatible price is found in `knownprices`
        if self.symbol == quote:
            return AssetBag(self.amount, quote)
        for price in knownprices:
            if price.pair.base == quote:
                price = price.flip()
            if price.pair.base == self.symbol and price.pair.quote == quote:
                return AssetBag(self.amount * price.price, quote)
        raise ValueError("No compatible price found in knownprices")

    def __mul__(self, other):
        return AssetBag(float(other)*self.amount, self.symbol)
    __rmul__ = __mul__

    def __add__(self, other):
        if not self.compatible(other):
            raise ValueError("Incompatible assets")
        return AssetBag(self.amount + other.amount, self.symbol)

    def __sub__(self, other):
        if not self.compatible(other):
            raise ValueError("Incompatible assets")
        return AssetBag(self.amount - other.amount, self.symbol)

    def __str__(self):
        if self.symbol in AssetBag.precisions:
            return '{0:0.{p}f} {1}'.format(self.amount, self.symbol, p=AssetBag.precisions[self.symbol])
        return "%g %s" % (self.amount, self.symbol)

    def __gt__(self, other):
        if not self.compatible(other):
            raise ValueError("Incompatible assets")
        return self.amount > other.amount
    def __lt__(self, other):
        return other > self
    def __ge__(self, other):
        return not other > self
    def __le__(self, other):
        return not self > other

    @classmethod
    def setPrecision(cls, symbol, prec):
        cls.precisions[symbol] = prec   # Set decimal precision of assets for printing, by symbol

    @staticmethod
    def validSymbol(symbol):
        if not isinstance(symbol, str):
            return False
        if len(symbol) == 0:
            return False
        ok = "QWERTYUIOPASDFGHJKLZXCVBNM."
        if not all(c in ok for c in symbol):
            return False
        return True

    @staticmethod
    def assertSymbolValid(symbol):
        # Either returns True or raises ValueError on invalid symbol
        if not AssetBag.validSymbol(symbol):
            raise ValueError("Invalid symbol: %s" % str(symbol))
        return True

    @staticmethod
    def fromString(assetstring):
        parts = assetstring.split()
        if len(parts) != 2:
            raise ValueError
        amount = float(parts[0])
        return AssetBag(amount, parts[1])


class Account:
    #
    # A list of AssetBags, essentially
    #
    # Note that Contract objects may add baggage to the account in the form of
    # additional members.  These serve as metadata for studies and for plotting
    # and describing contracts.
    #
    def __init__(self):
        self.bags = []

    def receive(self, rbag): # mutates
        for bag in self.bags:
            if bag.compatible(rbag):
                bag.absorb(rbag)
                break
        else:
            self.bags.append(rbag.clone())

    def empty(self): # mutates
        self.bags = []

    def valuation(self, quote, knownprices):
        value = AssetBag(0, quote)
        for bag in self.bags:
            value.absorb(bag.valuation(quote, knownprices))
        return value

    def copy(self):
        # Returns a deep copy of the Account, stripping any additional baggage
        # added by, e.g., Contract objects.
        retval  = Account()
        for bag in self.bags:
            retval.receive(bag.clone())
        return retval

    def prettyPrint(self, quote = None, knownprices = None):
        for bag in self.bags:
            if not quote:
                print (bag)
            else:
                print ("%s (%s)" % (bag, bag.valuation(quote, knownprices)))
        if quote:
            print ("Total valuation: %s" % self.valuation(quote, knownprices))


class OracleHash:
    #
    #  Defines a threshold to reveal a preimage.
    #
    #  This base class instance reveals preimage when some observed price:
    #
    #    equals or exceeds the threshold,  (exceeds==True, strict==False), or
    #    strictly exceeds the threshold,   (exceeds==True, strict==True), or
    #    equals or is below the threshold, (exceeds==False, strict==False), or
    #    is strictly below the threshold,  (exceeds==False, strict==True), or
    #
    #  `threshprice` is a Price object and defines the price threshold of the
    #  asset being measured (Base) in units of the asset in which it is
    #  denominated (Quote).
    #
    #  Use the factory mathods (.GT(), .LT(), .GE(), .LE()) to simplify
    #  creation.
    #
    def __init__(self, threshprice, strict, exceeds):
        if isinstance(threshprice, str):
            threshprice = Price(threshprice)
        self.threshprice = threshprice
        self.strict = strict
        self.exceeds = exceeds

    def isRevealed(self, obsprice):
        if not obsprice.pair.same(self.threshprice.pair):
            obsprice = obsprice.flip()  # (tolerate compatible but inverted obs price)
        if self.exceeds:
            if self.strict:
                return obsprice > self.threshprice
            else:
                return obsprice >= self.threshprice
        else:
            if self.strict:
                return obsprice < self.threshprice
            else:
                return obsprice <= self.threshprice

    def priceCompatible(self, price):
        return price.pair.compat(self.threshprice.pair)

    def __str__(self):
        return "Oracle<OpensWhen{{Price %s %s}}>" % (
            ">" if (self.strict and self.exceeds) else ">=" if self.exceeds else "<" if self.strict else "<=",
            str(self.threshprice)
        )

    @staticmethod
    def GT(threshprice):  # Reveal when end price > threshprice
        return OracleHash(threshprice, strict=True, exceeds=True)

    @staticmethod
    def GE(threshprice):  # Reveal when end price >= threshprice
        return OracleHash(threshprice, strict=False, exceeds=True)

    @staticmethod
    def LT(threshprice):  # Reveal when end price < threshprice
        return OracleHash(threshprice, strict=True, exceeds=False)

    @staticmethod
    def LE(threshprice):  # Reveal when end price <= threshprice
        return OracleHash(threshprice, strict=False, exceeds=False)


class HashTranche:
    #
    # Represents an HTLC with a price-conditioned preimage (OracleHash), a
    # quantity of asset, and destination accounts for preimage vs time-out
    # conditions.
    #
    #  ohash     -  An OracleHash object
    #  asset     -  An AssetBag object (or string rep)
    #  taccount  -  Account object to receive asset if timeout condition met (HTLC sender)
    #  haccount  -  Account object to receive asset if hash condition met (HTLC receiver)
    #
    # The following methods produce mutations of referenced objects:
    #
    #  .disburse(pricelist)  -  Will disburse `asset` to either `taccount` or `haccount`
    #                           based on reveal state of `ohash` determined by first
    #                           compatible price in `pricelist`
    #
    def __init__(self, ohash, asset, taccount, haccount):
        if isinstance(asset, str):
            asset = AssetBag(asset)
        self.ohash = ohash
        self.asset = asset
        self.taccount = taccount
        self.haccount = haccount

    def disburse(self, knownprices):  # mutates member objects
        for price in knownprices:
            if self.ohash.priceCompatible(price):
                if self.ohash.isRevealed(price):
                    self.haccount.receive(self.asset)
                else:
                    self.taccount.receive(self.asset)
                return
        else:
            raise ValueError("No compatible price in knownprices")

    def __str__(self):
        return "%s \t%s"%(str(self.asset), str(self.ohash))

class Contract:
    #
    # Basically a list of HashTranches and a list of destination accounts.
    #
    def __init__(self):
        self.tranches = []
        self.accounts = []
        self.pricelistcache = [] # set by .conclude()

    def reset(self): # mutates
        for acc in self.accounts:   # Empties (but does not
            acc.empty()             # remove) all accounts

    def addNAccounts(self, n): # mutates
        for _ in range(n):
            self.accounts.append(Account())

    def addTranche(self, ohash, asset, tindex=0, hindex=1): # mutates
        self.tranches.append(
            HashTranche(ohash, asset, taccount=self.accounts[tindex], haccount=self.accounts[hindex])
        )

    def conclude(self, finalprices): # mutates
        self.pricelistcache = finalprices
        for t in self.tranches:
            t.disburse(finalprices)

    def doStudy_deprecated(self, varprices, quote, fixedprices = []): # mutates
        # varprices: list of prices spanning a range (becomes X values)
        # fixedprices: additional external price data (parameters other than X), if any
        YY = []
        for _ in range(len(self.accounts)):
            YY.append([])
        for pr in varprices:
            self.reset()
            self.conclude([pr]+fixedprices)
            for i in range(len(self.accounts)):
                YY[i].append(self.accounts[i].valuation(quote, self.pricelistcache))
        return YY

    def doStudy(self, varprices, fixedprices = []): # mutates
        # For each account in contract:
        #   Make a list of account copies "concluded" at each price in varprices
        #
        # varprices: list of prices spanning a range (becomes X values)
        # fixedprices: additional external price data (parameters other than X), if any
        #
        # Creates following new structure in Contract object, which can be interpreted
        # by the plotting subsystem:
        #
        #   (Contract).StudyX = [a Price series]
        #   (Contract).StudyPriceEnv
        #   (Contract).accounts[...].StudyResults = [ series of Account copies ]
        #
        for ac in self.accounts:
            ac.StudyResults = []
        for pr in varprices:
            self.reset()
            self.conclude([pr]+fixedprices)
            for ac in self.accounts:
                ac.StudyResults.append(ac.copy())
        self.StudyX = varprices
        self.StudyPriceEnv = fixedprices

    def printTrancheTable(self):
        print ("TrancheTable contains %d slices." % len(self.tranches))
        for tr in self.tranches:
            print (tr)

    def printAccountValuesLine(self, quote, firstcoltext="", colwidth = 16, printHeader=False):
        if printHeader:
            print(("{0:>%d}"%colwidth).format(firstcoltext), end='')
            for a in self.accounts:
                print(("{0:>%d}"%colwidth).format("Account"), end='')
            print ()
            print ("-"*(colwidth*(1+len(self.accounts))))
            return
        print(("{0:>%d}"%colwidth).format(firstcoltext), end='')
        for a in self.accounts:
            print(("{0:>%d}"%colwidth).format(str(a.valuation(quote, self.pricelistcache))), end='')
        print()

###
## TESTS:
#
def _Test_HashOracle():
    print ("\nHash Oracle Test:\n")
    oracle = []
    for pricepoint in [7, 8, 9, 10, 11, 12, 13][::-1]:
        oracleprice = Price(pricepoint, "USD:BTS")
        oracle.append(OracleHash.LE(oracleprice))

    price = Price(11, "USD:BTS")
    for orc in oracle:
        print ("%s, which at %s is %s." % (
            orc, price, "revealed" if orc.isRevealed(price) else "NOT revealed"
        ))

def _Test_Account():
    print ("\nAccount Test:\n")
    ac = Account()
    ac.receive(AssetBag(10, "BTS"))
    ac.receive(AssetBag(10, "USD"))
    ac.receive(AssetBag(10, "USD"))
    ac.receive(AssetBag(10, "CNY"))
    ac.prettyPrint("BTS", [Price(0.027, "BTS:USD"), Price(6, "CNY:BTS")])


def _Test_HashTranche():
    print ("\nHashTranche Test:\n")
    A = Account()
    B = Account()
    TT = []
    TT.append(HashTranche(OracleHash.GT("12 USD:BTS"), AssetBag(100, "BTS"), A, B))
    TT.append(HashTranche(OracleHash.GT("11 USD:BTS"), AssetBag(100, "BTS"), A, B))
    TT.append(HashTranche(OracleHash.GT("10 USD:BTS"), AssetBag(100, "BTS"), A, B))
    TT.append(HashTranche(OracleHash.GT("9 USD:BTS"), AssetBag(100, "BTS"), A, B))
    TT.append(HashTranche(OracleHash.GT("8 USD:BTS"), AssetBag(100, "BTS"), A, B))

    endprices = [Price(12, "USD:BTS")]
    for T in TT:
        T.disburse(endprices)

    A.prettyPrint()
    B.prettyPrint()


def _Test_Contract():
    print("\nContract Test\n")
    C = Contract()
    C.addNAccounts(2)
    C.addTranche(OracleHash.GT("12 USD:BTS"), "100 BTS")
    C.addTranche(OracleHash.GT("11 USD:BTS"), "100 BTS")
    C.addTranche(OracleHash.GT("10 USD:BTS"), "100 BTS")
    C.addTranche(OracleHash.GT("9 USD:BTS"), "100 BTS")
    C.addTranche(OracleHash.GT("8 USD:BTS"), "100 BTS")

    AssetBag.setPrecision("USD", 2)
    C.printAccountValuesLine("USD", printHeader=True, firstcoltext="End Price")
    for p in [13, 12, 11, 10, 9, 8, 7]:
        price = Price(p, "USD:BTS")
        C.reset()
        C.conclude([price])
        C.printAccountValuesLine("BTS", firstcoltext=str(price))
    print()


if __name__ == '__main__':

    _Test_HashOracle()
    _Test_Account()
    _Test_HashTranche()
    _Test_Contract()
