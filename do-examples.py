from HTLCProductsSim import *
from HTLCProductsPlot import *
from BoundedStableCoin import *

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
    SP.plt.text(.14,57, "Stability preserved over a 16x performance \nrange, (from 0.025 to 0.40). Performance \nrange and variance tolerance are tunable \nparameters.", fontstyle="italic")
    SP.printtofile("BSC_Stability_USD.png")

    SP = ProductPlot(BSC, 0, "BTS")
    SP.draw()
    SP.plt.text(.15,1500, "As base price drops, more collateral remains \nwith stable product, preserving valuation \nin external asset.", fontstyle="italic")
    SP.printtofile("BSC_Stability_BTS.png")

    SP = ProductPlot(BSC, 1, "BTS")
    SP.draw()
    SP.plt.text(.14,2000, "Variabilty product offers an augmented upside \nfor bullish, risk-tolerant investors.", fontstyle="italic")
    SP.printtofile("BSC_Variability_BTS.png")

