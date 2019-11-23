# BoundedStableCoin.py
#
# Produces a pair of products in which one of them maintains stability in
# valuation against an external asset by guaranteeing a collateral pool in a
# native asset, and another which captures the variability by paying an overage
# against actual price increase.
#
# HTLCs and a Hash Oracle direct that balances of native asset go either into
# product A or product B based on price at a closing date.
#
# Two products:
#
#    +-------------------------+  +---------------------------+
#    | [0]  Stable Product     |  | [1]  Variable Product     |
#    +-------------------------+  +---------------------------+
#    | Has a face value        |  |  Offers additional lever- |
#    | denominated in some     |  |  age in the native asset. |
#    | external asset (e.g.    |  |  Ex: A purchase price of  |
#    | USD), Collateralized    |  |  X BTS may yield >X or <X |
#    | in a native asset       |  |  BTS depending on price   |
#    | (e.g. BTS).             |  |  moves, amplifying gains. |
#    +-------------------------+  +---------------------------+
#
# The perfomance ranges of the products are typically some multiple above and
# below a reference price, generally the "today" price.  Example, stability
# might be guaranteed when the "tomorrow" closing price is in a range from 1/8
# x to 8 x the "today" price.  The performance range is tunable.
#
# Use convenience factory methods easily create products of a given "face
# value".  E.g.:
#
#   contract = BoundedStableCoin.Face("100 USD", "0.10 BTS:USD", 4, 1.10)
#
# Resulting contract instance will contain both "products".
#
#.
import math
from HTLCProductsSim import *
from HTLCProductsPlot import *

def _GetGeometricSeries(stepratio, n_above, n_below=0):
    #
    RR = [1]
    invratio = 1/stepratio
    for _ in range(n_below):
        RR.append(invratio*RR[-1])
    RR.reverse()
    for _ in range(n_above):
        RR.append(stepratio*RR[-1])
    print(RR)
    return RR

def _GetGeometricMidpoints(somelist):
    MM = []
    for a,b in zip(somelist[0:-1], somelist[1:]):
        MM.append(math.sqrt(a*b))
    return MM


class BoundedStableCoin(Contract):
    #
    def __init__(self, principle, growthtolerance, todayprice, n_above, n_below):
        #
        # Default constructor is somewhat generic. Use .Face() instead to more
        # intuitively create a product with a given face value and performance
        # range.
        #
        # principle       -  (AssetBag) Denominated in collateral asset.  If downside protection
        #                    is (1/4)x facevalue, then 'principle' should contain 4x the
        #                    collateral equivalent of facevalue.
        #
        # growthtolerance -  (Number) Multiplier that indicates allowed variability of the stable
        #                    coin, as a fraction > 1.  (E.g. 1.1 indicates 10% tolerance)
        #
        # todayprice      -  (Price) The price around which we compute the upside and downside
        #                    stibility bounds on the stable product.
        #
        if not isinstance(principle, AssetBag):
            raise ValueError
        if not isinstance(todayprice, Price):
            raise ValueError
        if not (principle.symbol == todayprice.pair.base):
            raise ValueError

        Contract.__init__(self)

        cutratio = 1.0 - (1/growthtolerance)  # Each hash tranche is this fraction of the
                                              # remaining pie.
        remainder = principle.amount
        pieslices = []
        switchprices = _GetGeometricMidpoints(_GetGeometricSeries(growthtolerance, n_above, n_below))

        for _ in range(len(switchprices)):
            pieslices.append(remainder * cutratio)
            remainder -= pieslices[-1]

        self.addNAccounts(2)
        self.accounts[0].name = "BSC Stable Coin"   # Default generic names
        self.accounts[1].name = "BSC Variable Coin" # Better ones set by factories
        for p,b in zip(switchprices,pieslices):
            self.addTranche(OracleHash.GE(p*todayprice), AssetBag(b,principle.symbol))
        self.addTranche(OracleHash.LT(0*todayprice), AssetBag(remainder,principle.symbol))


    @staticmethod
    def Face(facevalue, todayprice, upside, tolerance):
        # Return a BSC Contract based on a face value, current price, and multiplicative price
        # range.  (Computes computes collateral needed, number of hashes needed, etc...)
        #
        # Example:
        #
        #   BoundedStableCoin.Face("100 USD", "0.10 BTS:USD", 4, 1.10)
        #
        # will return a contract collateralized in BTS that holds a stable value of $100 USD
        # (with no more that 10% variability) over a base price range from (1/4) * .10 BTS:USD
        # to 4 * .10 BTS:USD.
        #
        if isinstance(facevalue, str):
            facevalue = AssetBag(facevalue)
        if isinstance(todayprice, str):
            todayprice = Price(todayprice)
        if tolerance <= 1:
            raise ValueError("Tolerance must be multiplicative fraction > 1.")

        growthtol = tolerance+1
        n_upside = 0
        while tolerance < growthtol:
            n_upside += 1
            growthtol = pow(upside, (1/n_upside))
        principle = upside * facevalue.valuation(todayprice.pair.base, [todayprice])

        ret = BoundedStableCoin(principle, growthtol, todayprice, n_upside, n_upside)
        startvalue = principle - facevalue.valuation(todayprice.pair.base, [todayprice])
        ret.openingbaseprice = todayprice
        ret.accounts[0].name = "%s Ranged Bond"%facevalue
        ret.accounts[0].facevalue = facevalue
        ret.accounts[0].fvspread = pow(growthtol, 0.5)
        ret.accounts[0].startvalue = facevalue.valuation(todayprice.pair.base, [todayprice])
        ret.accounts[1].name = "%s Variabilty Coin"%startvalue
        ret.accounts[1].startvalue = startvalue
        return ret


if __name__ == '__main__':

    AssetBag.setPrecision("USD", 2)

    todayprice = Price(0.10, "BTS:USD")
    stabilityrange = 4
    facevalue = AssetBag(100, "USD")

    BSC = BoundedStableCoin.Face(facevalue, todayprice, stabilityrange, 1.10)

    BSC.printTrancheTable()

    BSC.printAccountValuesLine("USD", printHeader=True, firstcoltext="End Price")
    for p in [f * 0.01 for f in range(2, 14)]:
        price = Price(p, "BTS:USD")
        BSC.reset()
        BSC.conclude([price])
        BSC.printAccountValuesLine("USD", firstcoltext=str(price))
    print()

    P = Price.linspace(0, 0.50, 4000, "BTS:USD")
    BSC.doStudy(P)

    SP = ProductPlot(BSC, 0, "USD")
    SP.draw()
    #SP.plt.text(.15,50, "Stability protection over four doublings.\nProtection range and variance tolerance\nare tunable parameters.", fontstyle="italic")
    SP.printtofile("foo1.png")

    SP = ProductPlot(BSC, 0, "BTS")
    SP.draw()
    #SP.plt.text(.15,50, "Stability protection over four doublings.\nProtection range and variance tolerance\nare tunable parameters.", fontstyle="italic")
    SP.printtofile("foo2.png")

    SP = ProductPlot(BSC, 1, "BTS")
    SP.draw()
    #SP.plt.text(.15,50, "Stability protection over four doublings.\nProtection range and variance tolerance\nare tunable parameters.", fontstyle="italic")
    SP.printtofile("foo3.png")

