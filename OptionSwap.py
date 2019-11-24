# OptionSwap.py
#
#
#.
import math
from HTLCProductsSim import *
from HTLCProductsPlot import *

class LongCall(Contract):
    #
    def __init__(self, underlying, strikeprice, premium=1.10):
        #
        if isinstance(underlying, str):
            underlying = AssetBag(facevalue)
        if isinstance(strikeprice, str):
            strikeprice = Price(todayprice)

        Contract.__init__(self)

        escrow = underlying.valuation(strikeprice.pair.quote, [strikeprice])

        self.addNAccounts(2)
        self.accounts[0].name = "Bonded Call Option on %s" % str(underlying)
        self.accounts[0].facevalue = premium * escrow
        self.accounts[0].facevalue.label = "List Price"
        self.accounts[1].name = "Short Call locking %s" % str(underlying)
        self.addTranche(OracleHash.GE(strikeprice), underlying, 1, 0)
        self.addTranche(OracleHash.GE(strikeprice), escrow, 0, 1)
        self.strikeprice = strikeprice


if __name__ == "__main__":

    C = LongCall(AssetBag("10000 BTS"), Price("0.05 BTS:USD"), 1.15)

    P = Price.linspace(0, 0.10, 200, "BTS:USD")
    C.doStudy(P[1:])

    SP = ProductPlot(C, 0, "USD")
    SP.draw()
    SP.plt.plot([0],[0])
    SP.plt.text(0.001, 825, "Paired HTLC \"Atomic Swap.\"\nPreimage provided by oracle\nif price above strike.", va="top")
    SP.plt.text(0.001, 375, "Below Strike:\nReturn of 500 USD bond;\nOther party keeps 10000 BTS\nunderlying asset.", va="top")
    SP.plt.text(0.055, 375, "Above Strike:\nDelivery of 10000 BTS; Other\nparty keeps 500 USD bond.", va="top")
    SP.printtofile("LongCall.png")

    SP = ProductPlot(C, 1, "USD")
    SP.draw()
    SP.plt.plot([0],[0])
    SP.printtofile("ShortCall.png")
