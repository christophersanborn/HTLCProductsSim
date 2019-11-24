# HTLCProductsPlot.py
#
# Provides a class that knows how to plot the "products" contained
# within Contract objects.
#
#.
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from HTLCProductsSim import *

class ProductPlot:

    facecolors = {"USD": "honeydew", "default": "cornsilk"} # Chart backgrounds by denominated currency

    def __init__(self, contract, acct_idx, quote):
        plt.clf()
        self.quote = quote
        self.X = contract.StudyX
        self.contract = contract
        self.product = contract.accounts[acct_idx] # actually Account but with "product metadata" baggage attached
        self.Y = [y.valuation(quote, [x]+contract.StudyPriceEnv) for x,y in zip(self.X, self.product.StudyResults)]
        self.productname = self.product.name if hasattr(self.product,"name") else "Default"
        self.openingbaseprice = contract.openingbaseprice if hasattr(contract, "openingbaseprice") else None
        self.plt = plt # Duck access??

    def draw(self):
        self.initAxes()
        self.drawPriceAnnotations()
        plt.plot([x.price for x in self.X], [y.amount for y in self.Y], label="Closing Value", color="navy")
        plt.legend()

    def initAxes(self):
        plt.gcf().set_size_inches(6.9,4.8, forward=True)
        plt.gca().set_facecolor(ProductPlot.facecolors.get(self.quote, ProductPlot.facecolors["default"]))
        plt.xlabel("Closing Base Price (%s)" % str(self.X[0].pair), fontweight="bold")
        plt.ylabel("Product Value (%s)" % self.Y[0].symbol, fontweight="bold")
        plt.title("%s - Value at Close" % self.productname, fontweight="bold")

    def drawPriceAnnotations(self):
        # Draws todayprice and face value
        if hasattr(self.product, "startvalue") and self.product.startvalue.compatible(self.Y[0]):
            xmin = min(self.X).price
            xmax = max(self.X).price
            y = self.product.startvalue.amount
            plt.plot([xmin, xmax], [y, y], label="Opening Value", color="cornflowerblue", dashes=[6, 2], linewidth=1.0)
        if hasattr(self.product, "facevalue") and self.product.facevalue.compatible(self.Y[0]):
            xmin = min(self.X).price
            xmax = max(self.X).price
            y = self.product.facevalue.amount
            label = self.product.facevalue.label if hasattr(self.product.facevalue, "label") else "Face Value"
            plt.plot([xmin, xmax], [y, y], label=label, color="royalblue", dashes=[4, 2])
            if hasattr(self.product, "fvspread") and self.product.fvspread > 1:
                ybot = self.product.facevalue.amount/self.product.fvspread
                ytop = self.product.facevalue.amount*self.product.fvspread
                rect = patches.Rectangle((xmin,ybot),(xmax-xmin),(ytop-ybot), facecolor="lavender")
                plt.gca().add_patch(rect)
                plt.plot([xmin, xmax], [ytop, ytop], label="Variance tolerance",
                         color="lightsteelblue", linewidth=0.75, dashes=[3, 3])
                plt.plot([xmin, xmax], [ybot, ybot], color="lightsteelblue", linewidth=0.75, dashes=[3, 3])
        # Opening Base Price:
        if self.openingbaseprice is not None and self.openingbaseprice.pair.same(self.X[0].pair):
            x = self.openingbaseprice.price
            ymax = max(self.Y).amount
            plt.plot([x, x], [0, ymax], color="sienna", linewidth=1.25, dashes=[4, 3])
            plt.text(x, ymax/40, " Opening Base Price", color="sienna")
        # Strikeprice:
        if hasattr(self.contract, "strikeprice") and self.contract.strikeprice.pair.same(self.X[0].pair):
            x = self.contract.strikeprice.price
            ymax = max(self.Y).amount
            plt.plot([x, x], [0, ymax], color="sienna", linewidth=1.25, dashes=[4, 3])
            plt.text(x, ymax/40, " Strike Price", color="sienna")


    def show(self):
        plt.show()

    def printtofile(self, filename, dpi=240):
        plt.savefig(filename, bbox_inches='tight', dpi=dpi)
