# PriceIterators.py
#
# Classes that can compute price levels (or other levels, e.g. RVI) as
# indexable sequences.  E.g. logarithmically-spaced intervals where
# the index represetnts a logarithm of the price.
#
# Useage:
#
#  import PriceIterators
#
#  prices = PriceIterators.New(**args)
#
# Classes:
#
#  o _LogSpacer
#  o LogPrices
#
# Module Utils:
#
#  o New(args...)
#
import math
import itertools

def New(**kwargs):
    algorithm = kwargs.pop("iterator", "default")
    if algorithm in ["logarithmic", "default"]:
        newPI = LogPrices(**kwargs)
    elif algorithm in ["interval"]:
        newPI = IntervalPrices(**kwargs)
    return newPI


class IntervalPrices:
    """Prices at fixed intervals."""

    def __init__(self, startprice, interval, steps, plane=1, flip=False):
        self.startprice = startprice
        self.interval = interval
        self.steps = steps
        self.plane = plane # ignored
        self.flip = flip

    def __str__(self):
        # String for appending to pretext header, e.g. "t32000:f2:s24:p2d"
        # Format: (t|b)<startprice>:v<INTERVAL>:s<STEPS>[:p<PLANE>(u|d)]
        descending = (self.interval < 0) ^ self.flip
        tailprice = self.startprice + (self.interval * self.steps)
        headerprice = self.startprice if not self.flip else tailprice
        norminterval = self.interval if (self.interval > 0) else -self.interval
        return "%s:%s:%s" % (
            "%s%g"%("t" if descending else "b", headerprice),
            "v%g"%(norminterval),
            "s%g"%(self.steps)
        )

    def getDescriptiveContext(self):
        context = {}
        context['steps'] = self.steps
        context['plane'] = self.plane
        context['structure'] = "fixed intervals"
        return context

    def getPrices(self):
        deltas = [self.interval * m for m in range(self.steps+1)]
        prices = [self.startprice + d for d in deltas]
        if self.flip:
            prices.reverse()
        return prices

    @property
    def prices(self):
        return self.getPrices()


class LogPrices:
    """Logarithmically indexed price sequence.

    Sequence spans N multiplicative decades consisting of M steps each, for a
    total of N*M+1 total price points.  Price sequences are optionally
    staggered into different interleaved "price planes" to allow multiple
    coursely-spaced tables to combine into a finer coverage of price points.

    The `plane` parameter indicates both which stagger plane is selected and
    how many make up the set. I.e. the table is table n of m, with m indicated
    by the most significant bit.  Examples:

      `plane` = 1  =>  table 1 of 1
                2  =>  table 1 of 2
                3  =>  table 2 of 2
                4  =>  table 1 of 4
                5  =>  table 2 of 4
                8  =>  table 1 of 8
               15  =>  table 7 of 8

    Note that stagger planes 1, 2, 4, 8,... all produce the same price
    sequence, but will produce different hash sequences due to the pretext
    header being different.

    """

    def __init__(self, startprice, factor, decades, steps, plane=1, flip=False):
        self.startprice = startprice
        self.factor = factor
        self.decades = decades
        self.steps = steps
        self.plane = plane    # Table n of m, (m indicated by MSB)
        self.flip = flip

    def __str__(self):
        # String for appending to pretext header, e.g. "t32000:f2:s24:p2d"
        # Format: (t|b)<startprice>:f<FACTOR>:s<STEPS>[:p<PLANE>(u|d)]
        descending = (self.factor < 1) ^ self.flip
        tailprice = self.startprice * (self.factor ** self.decades)
        headerprice = self.startprice if not self.flip else tailprice
        normfactor = self.factor if (self.factor > 1) else (1/self.factor)
        return "%s:%s:%s%s" % (
            "%s%g"%("t" if descending else "b", headerprice),
            "f%g"%(normfactor),
            "s%g"%(self.steps),
            "" if self.plane == 1 else ":p%g%s"%(self.plane,
                                                 "u" if (self.factor > 1) else "d")
        )

    def getDescriptiveContext(self):
        normfactor = self.factor if (self.factor > 1) else (1/self.factor)
        context = {}
        context['decades'] = self.decades
        context['decadeword'] = "octaves" if normfactor==2 else "decades" if normfactor==10 else "multiples"
        context['steps'] = self.steps
        context['plane'] = self.plane
        context['structure'] = "%(decades)s %(decadeword)s, %(steps)s steps each"%context
        return context

    def getPrices(self):
        stagger_m = 2**int(math.log(self.plane,2))
        stagger_n = self.plane - stagger_m # strip leading bit
        multiples = _LogSpacer(self.factor, self.steps, stagger_n).getLevels(self.decades)
        prices = [self.startprice * m for m in multiples]
        if self.flip:
            prices.reverse()
        return prices

    @property
    def prices(self):
        return self.getPrices()


####
## Class:  _LogSpacer
##
## Generates sequences of factors where each factor is a constant
## ratio to the preceding one.  Note we aren't dealing with "prices"
## here, just factors, so one end of the sequence will always be 1.00.
##
## Can generate the sequence either "forward" or "reverse".
##
## Handles "staggering", where multiple course-grained sequences, when
## combined together, make a fine-grained sequence.
##
class _LogSpacer:

    def __init__(self, decadefactor=None, steps=None, stagger=None):
        self.decadefactor = decadefactor
        self.steps = steps
        self.stagger = stagger

    def getLevels(self, numDecades):
        self._levels = [1.0]
        decadeSteps = self.getDecadeSteps()
        stepFactor = decadeSteps[0]
        (n, d) = _LogSpacer.staggerRatioPair(self.stagger)
        staggerFactor = stepFactor ** (n/d)
        self._levels = [1.0 * staggerFactor]
        for i in range(numDecades):
            extend = [self._levels[-1] * ds for ds in decadeSteps]
            self._levels.extend(extend)
        return self._levels

    def getDecadeSteps(self):
        # Generate sequence of product multiplier that span a "decade" of
        # proportionality given by 'factor' over a series of 'steps'
        # intervals.
        factor = float(self.decadefactor)
        steps = int(self.steps)
        stepmult = factor ** (1 / steps)
        steppct = (stepmult-1)*100 if stepmult>1 else ((1/stepmult)-1)*100
        result = [ stepmult ** i for i in range(1,1+steps)]
        residual = abs(result[-1]-factor) # measure of accumulated error
        if residual > 1e-12:
            print ("Warning: Decade Residual of %g may be too large." % residual)
        result[-1] = float(factor) # prevent accumulated error of many decades
        return result

    def staggerRatioPair(idx):
        """ Compute power ratio used to compute the idx'th stagger of a series.

        Returns (n, d) such that a price point in a series spaced with
        stepfactor F is staggered by P(n, idx) = P(n, 0) * pow(F,(n/d)).
        """
        if idx==0: return (0, 1)
        msbidx = 2**int(math.log(idx,2))    # keeps only MSB of idx
        d = msbidx*2
        (n0, d0) = _LogSpacer.staggerRatioPair(idx-msbidx)
        n = 1 + n0*d/d0
        return (n, d)


if __name__ == '__main__':
    print("Test 1:")

    lines = ["", "", ""]
    for i in range(0,33):
        (n,d) = _LogSpacer.staggerRatioPair(i)
        lines[0] += "%3d  "%n
        lines[1] += " --  "
        lines[2] += "%3d  "%d
        #print("idx: %2d, (%2d, %2d)"%(i,n,d))
    print(lines[0])
    print(lines[1])
    print(lines[2])

    print("\nTest 2:")

    LS = _LogSpacer(64, 3, 2)
    for i in LS.getLevels(2):
        print(i)

    print("\nTest 3:\n")

    P1 = LogPrices(32000,0.5,5,6,8,False)
    P2 = LogPrices(32000,0.5,5,6,8,True)
    P3 = LogPrices(32000,0.5,5,6,12,False)
    P4 = LogPrices(32000,0.5,5,6,12,True)
    P5 = LogPrices(32000,0.5,5,6,1,False)
    P6 = LogPrices(32000,0.5,5,6,1,True)
    P7 = LogPrices(1000,2,5,6,24,False)
    P8 = LogPrices(1000,2,5,6,24,True)

    print("%20s%20s%20s%20s%20s%20s%20s%20s"%(P1,P2,P3,P4,P5,P6,P7,P8))
    for (a,b,c,d,f,g,h,i) in itertools.zip_longest(P1.prices,P2.prices,P3.prices,P4.prices,
                                                   P5.prices,P6.prices,P7.prices,P8.prices):
        print("%20g%20g%20g%20g%20g%20g%20g%20g"%(a,b,c,d,f,g,h,i))
