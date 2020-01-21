#
#
from HTLCProductsSim import *
import configparser
import datetime
import hashlib
import sys

warningtext = ("_**WARNING:** This is an EXPERIMENTAL Hash Oracle. At this point in time, " +
               "there is NO WARRANTY of any kind, nor any promise or commitment, implied or otherwise, " +
               "as to the reliability, accuracy, or timeliness of the information in this " +
               "post or in any future post concomitant to this one._")

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

        #for pr, pt in zip(prices, pretexts):
        #    print("At price %10.2f, pretext: %s" % (pr, pt))

        self.meta = meta
        self.prices = prices
        self.pretexts = pretexts
        self.preimages = preimages
        self.hashes = hashes

    def printPublicTable(self, precision=5):
        print("=========== Advanced-Published Hash Table: (Copy-Paste to Steemit, e.g.) ===========")
        print("")
        print("(Preamble text, if any.)\n")
        print("## Hash Table: [%s] (Target:%s):" % (
            str(self.meta.pair), self.meta.targetdate.strftime("%Y-%m-%d")
        ))
        print("\nThis is a table of base16-encoded SHA-256 hashes upon which HTLC contracts may be built. "
              "Pending conditions described below, some, none, or all of the 256-bit (32-byte) "
              "base16-encoded preimages may be revealed at appointed times.")
        print("")
        print("**Target Date:**\n * %s\n" % self.meta.targetdate.strftime("%b %d %Y (%Y-%m-%d)"))
        print("**Event to Report:**\n * %s\n" % self.meta.eventdesc)
        print("**Reporting Method:**\n * %s\n" % self.meta.reportmethod)
        print("**Determination Method:**\n * %s\n" % self.meta.determination)
        print("**Time Frame:**\n * %s\n" % self.meta.timeframe)
        print("**Quote Pair:** %s"%str(self.meta.pair))
        print("**Hash Header:** `%s`"%self.meta.header)
        print("**Num Hashes:** %d (%d %s, %d steps each)" % (
            len(self.hashes),
            int((len(self.hashes)-1)/self.meta.steps),
            "octaves" if self.meta.normfactor==2 else "decades" if self.meta.normfactor==10 else "multiples",
            self.meta.steps
        ))
        print("**Resolution:** %s each hash, or %s every two hashes,..." % (
              "%0.2f%%"%self.meta.getResolutionPct(1),
              "%0.2f%%"%self.meta.getResolutionPct(2)))
        print("")
        print("%s\n"%warningtext)
        print("Begin Table:")
        print("")
        print("P<sub>obs</sub> | P<sub>hash</sub> | Then preimage will reveal for this hash:")
        print("-|-:|-")
        for pr, h in zip(self.prices, self.hashes):
            print("%s | %s | %s"%( self.meta.gele, ("%%0.%df"%precision)%pr, h.hex() ))
        print("\n%s"%warningtext)

    def printRevealTable(self, obsprice, precision=5):
        #
        if self.meta.factor > 1:
            print("Oops: Ascending tables not supported yet.")
            return
        #
        generator = "{None}"
        for i in range(len(self.prices)):
            # TODO: this only correct for descending table; adapt to handle either descending or ascending
            if (obsprice >= self.prices[i]):
                generator = self.pretexts[i]
                break
        #
        print("=========== Observation Preimage Table: (Copy-Paste to Steemit, e.g.) ===========")
        print("\n(Preamble text, if any. "
              "NOTE: BE SURE TO FILL OUT BACK REFERENCE URL BELOW. "
              "This should link back to original hash table.)\n")
        print("## Preimage Reveal Table [%s] (%s):"% (
            str(self.meta.pair), self.meta.targetdate.strftime("%Y-%m-%d")
        ))
        print("\nThis is a table of base16-encoded 256-bit (32 byte) preimages, corresponding to a previously-published table of _hashes_.")
        print("")
        print("**Hash Table URL:**\n <PASTE URL HERE>\n")
        print("**Target Date:**\n * %s\n" % self.meta.targetdate.strftime("%b %d %Y (%Y-%m-%d)"))
        print("**Event Reported:**\n * %s\n" % self.meta.eventdesc)
        print("**Reporting Method:**\n * %s\n" % self.meta.reportmethod)
        print("**Determination Method:**\n * %s\n" % self.meta.determination)
        print("**Time Frame:**\n * %s\n" % self.meta.timeframe)
        print("**Quote Pair:** %s"%str(self.meta.pair))
        print("**Hash Header:** `%s`"%self.meta.header)
        print("**Generator:** `%s`" % generator)
        print("**Observed Price:** %s" % ("%%0.%df"%precision)%obsprice)
        print("")
        print("%s\n"%warningtext)
        print("Begin Table:")
        print("")
        print("P<sub>obs</sub> | P<sub>hash</sub> | Preimage:")
        print("-|-:|-")
        for pr, pi in zip(self.prices, self.preimages):
            print("%s | %s | %s"%( self.meta.gele, ("%%0.%df"%precision)%pr,
                                   pi.hex() if obsprice >= pr else "(Condition not met)"
                                   # TODO: don't define condition eval here - this is only for descending tables
            ))
        print("\n%s"%warningtext)


class PriceLadderMetaData:

    def __init__(self, targetDate, originPrice, decadeFactor=0.5, decadeSteps=8,
                 eventdesc = "Price of X as determined on target date.",
                 reportmethod = "", determination = "", timeframe = ""):

        if isinstance(targetDate, str):
            targetDate = datetime.datetime.strptime(targetDate, "%y%m%d")

        self.targetdate = targetDate
        self.originprice = originPrice.price
        self.pair = originPrice.pair
        self.factor = decadeFactor
        self.normfactor = decadeFactor if decadeFactor >= 1 else (1/decadeFactor)
        self.steps = decadeSteps
        self.gele = ">=" if decadeFactor<1 else "<="
        self.eventdesc = eventdesc
        self.reportmethod = reportmethod
        self.determination = determination
        self.timeframe = timeframe

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


AppDesc = """Hash Ladder Tool:\n
  Usage:    python3 %s <target_date> <top_price> <tag> [reveal_price]\n
            Pair and Tag-specific config option are read from the config file
            (ladder.conf) in section [<pair> <tag>].\n
  Example:  python3 %s "200110" "0.50 BTS:USD" Down\n
            Prints descending hash table (no preimages) for Jan 10, 2020 BTS:USD
            market, taking options from [BTS:USD Down] section.\n
  Example:  python3 %s "200110" "32000 BTC:USD" Down 7965.37\n
            Prints preimage table for BTC:USD observed price of 7965.37\n
"""%(sys.argv[0], sys.argv[0], sys.argv[0])

if __name__ == "__main__":

    if len(sys.argv) < 4:
        print(AppDesc)
        quit()

    targetdate = sys.argv[1]    # e.g. "200110" for Jan 10, 2020
    topprice = sys.argv[2]      # e.g. "32000 BTC:USD"
    tagstring = sys.argv[3]     # e.g. "Down" for descending table
    observedprice = float(sys.argv[4]) if len(sys.argv)>4 else None

    topP = Price(topprice)
    cfgsection = str(topP.pair)+" "+tagstring

    cfg = configparser.ConfigParser()
    cfg.read('ladder.conf')
    kwoptions = {}
    try:
        secrettxt = cfg['default']['secret'].strip('"')
    except:
        print ("Could not read hash secret from config file. Does ladder.conf exist?")
        quit()
    try:
        decadefactor = float(cfg[cfgsection]['factor'])
        decadesteps = int(cfg[cfgsection]['steps'])
        numdecades = int(cfg[cfgsection]['decades'])
        prec = int(cfg[cfgsection]['precision'])
        for kwkey in ["eventdesc", "reportmethod", "determination", "timeframe"]:
            kwoptions[kwkey] = cfg[cfgsection][kwkey].strip('"')
    except:
        print("Could not read option '%s' from config section [%s]."%(kwkey, cfgsection))
        quit()

    meta = PriceLadderMetaData(targetdate, topP, decadefactor, decadesteps,
                               **kwoptions)
    ladder_root = meta.getRootHash(secrettxt)
    H = HashLadder(meta, ladder_root, numdecades)

    if observedprice:
        H.printRevealTable(observedprice, precision=prec)
    else:
        H.printPublicTable(precision=prec)
