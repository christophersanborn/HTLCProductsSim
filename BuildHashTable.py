#
#
from HTLCProductsSim import *
import configparser
import datetime
import hashlib
import sys

class HashLadder:

    def __init__(self, meta, rootHash, numDecades = 5):
        #
        # Hash(YYMMDDHH:BASE:QUOTE:[>=/<=]:[price]:[p/m]:[prepre])
        #
        #                                          [roothash]
        #                                              v
        # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
        #                                              v
        # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
        #                                              v
        # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
        #                                             ...

        if not len(rootHash.hex())==64:
            print("Error: base preimage not in expected format")
            raise ValueError

        prices = meta.getPrices(numDecades)

        ladder = [hashlib.sha256(rootHash).digest()]
        for i in range(1, len(prices)):
            ladder.append(hashlib.sha256(ladder[-1]).digest())
        print("Len P, Len L: %d %d" % (len(prices), len(ladder)))

        header = meta.header

        # Get pretexts:
        pretexts = []   # strings
        preimages = []  # byte blobs
        hashes = []     # byte blobs
        for i in range(len(ladder)):
            new_pretext = "%s:i%d:%s"%(header, i, ladder[i].hex())
            new_preimage = hashlib.sha256(new_pretext.encode('utf-8')).digest()
            new_hash = hashlib.sha256(new_preimage).digest()
            pretexts.append(new_pretext)
            preimages.append(new_preimage)
            hashes.append(new_hash)

        for pr, pt in zip(prices, pretexts):
            print("At price %10.2f, pretext: %s" % (pr, pt))

        self.meta = meta
        self.prices = prices
        self.pretexts = pretexts
        self.preimages = preimages
        self.hashes = hashes

    def printPublicTable(self, precision=5):
        print("=========== Advanced-Published Hash Table ===========")
        print("")
        print("## Hash Table: (Price Ladder)")
        print("")
        print("**Target Date:** %s" % self.meta.targetdate.strftime("%b %d %Y (%Y-%m-%d)"))
        print("**Event to Report:** Price of %s as determined on target date."%self.meta.pair.base)
        if self.meta.factor < 1:
            print("**Reporting Method:** Reveal preimages for all hashes for which observed price meets or exceeds hash level.")
        else:
            print("**Reporting Method:** Reveal preimages for all hashes for which observed price meets is at or below hash level.")
        print("**Determination Method:** (Described in detail elsewhere.)")
        print("**Quote Pair:** %s"%str(self.meta.pair))
        print("**Hash Header:** `%s`"%self.meta.header)
        print("**Resolution:** %s each hash, or %s every two hashes,..." % (
              "%0.2f%%"%self.meta.getResolutionPct(1),
              "%0.2f%%"%self.meta.getResolutionPct(2)))
        print("")
        print("Begin Table:")
        print("")
        print("P<sub>obs</sub> | P<sub>hash</sub> | Then preimage will reveal for this hash:")
        print("-|-:|-")
        for pr, h in zip(self.prices, self.hashes):
            print("%s | %s | %s"%( self.meta.gele, ("%%0.%df"%precision)%pr, h.hex() ))


class PriceLadderMetaData:

    def __init__(self, targetDate, originPrice, decadeFactor=0.5, decadeSteps=8):

        if isinstance(targetDate, str):
            targetDate = datetime.datetime.strptime(targetDate, "%y%m%d")

        self.targetdate = targetDate
        self.originprice = originPrice.price
        self.pair = originPrice.pair
        self.factor = decadeFactor
        self.steps = decadeSteps
        self.gele = ">=" if decadeFactor<1 else "<="

        # Header Format:
        #  YYMMDD(HH):[gele]:BASE:QUOTE:startprice:FACTOR:STEPS
        header = "%s:%s:%s:%s:%s:%s" % (
            "d%s"%self.targetdate.strftime("%y%m%d"),
            self.gele,
            "%s"%str(self.pair),
            "%s%g"%("t" if self.factor<1 else "b", self.originprice),
            "f%g"%(self.factor if self.factor > 1 else (1/self.factor)),
            "s%g"%self.steps
        )
        self.header = header

    def getRootHash(self, secret):
        # Returns a deterministic root hash for a priceladder by
        # hashing together a secret and the ladder header.
        if not isinstance(secret, str):
            raise ValueError
            # TODO: be flexible and accept bytes
        root_text = "%s%s"%(self.header, secret)
        return hashlib.sha256(root_text.encode('utf-8')).digest()

    def getPrices(self, numDecades, startidx=0):
        # Returns prices array for some number of decades from the originPrice
        prices = [self.originprice]
        decadeSteps = getDecadeSteps(self.factor, self.steps)
        for i in range(numDecades):
            extend = [prices[-1] * ds for ds in decadeSteps]
            prices.extend(extend)
        return prices[startidx:]

    def getResolutionPct(self, skip=1):
        normfact = self.factor if self.factor>1 else (1/self.factor)
        stepfact = normfact ** (1/self.steps)
        return ((stepfact ** skip) - 1) * 100


def getDecadeSteps(factor=10, steps=10):

    factor = float(factor)
    stepmult = factor ** (1 / steps)
    steppct = (stepmult-1)*100 if stepmult>1 else ((1/stepmult)-1)*100
    print("Info: Single-step percent change (ascending) is %0.3f%%"%steppct)
    print("Info: Decade factor is: %g" % factor)

    result = [ stepmult ** i for i in range(1,1+steps)]
    residual = abs(result[-1]-factor) # measure of accumulated error
    if residual < 1e-12:
        print ("Info: Decade Residual of %g is tolerable." % residual)
    else:
        print ("Warning: Decade Residual of %g may be too large." % residual)
    result[-1] = float(factor) # prevent accumulated error
    return result


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage:   python3 %s <target_date> <top_price> [reveal_price]"%sys.argv[0])
        print("Example: python3 %s \"200110\" \"32000 BTC:USD\" 7965.37"%sys.argv[0])
        print("Be sure file 'ladder.conf' exists and has a good random secret.")
        quit()

    cfg = configparser.ConfigParser()
    cfg.read('ladder.conf')
    try:
        secrettxt = cfg['default']['secret']
        decadefactor = float(cfg['priceladderdown']['factor'])
        decadesteps = int(cfg['priceladderdown']['steps'])
        numdecades = int(cfg['priceladderdown']['decades'])
    except:
        raise ValueError("Config file missing or a necessary value missing.")

    targetdate = sys.argv[1]    # e.g. "200110" for Jan 10, 2020
    topprice = sys.argv[2]      # e.g. "32000 BTC:USD"

    meta = PriceLadderMetaData(targetdate, Price(topprice), decadefactor, decadesteps)
    ladder_root = meta.getRootHash(secrettxt)

    H = HashLadder(meta, ladder_root, numdecades)
    H.printPublicTable(precision=2)
