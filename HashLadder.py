# HashLadder.py
#
# Second iteration of developing this concept.
#
# Here we define classes HashLadder and HashTable. HashLadder is
# boiled down to just the ladder of pre-texts and their corresponding
# preimages and hashes. HashTable brings in the correspondence of each
# hash to a particular price point, market, and date target, and also
# includes output mechanisms to print the tables.
#
import configparser
import datetime
import hashlib
import textwrap
from HTLCProductsSim import *
from LadderElements import *

######
## Class:  HashLadder
##
class HashLadder:
    """
    Hash Ladder: A determinstic sequence generator "pre-texts" that
    result in a Hash Table.

    """
    # This class is responsible ONLY for generating and representing the
    # sequence of generators, preimages, and hashes, and for associated
    # services.  It is NOT knowledgeable about the associated markets,
    # target dates, etc., of a particular table. It is given a root hash and
    # a generator "header" to produce the sequence.
    #
    # The root hash is iteratively hashed to produce the "kernels" of the
    # sequence of pretexts.  Any individual pretext is capable of serving as
    # a "generator" for subsequent pretexts.  (But because the kernels
    # result from hashing, you can't generate *previous* pretexts.)
    #
    # Pretexts concatenate a header string, an integer sequence number (as a
    # string), and the kernel (as a string of base16 digits).
    #
    #                                          [roothash]
    #                                              v
    # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
    #                                              v
    # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
    #                                              v
    # [hash] <-- [preimage] <-- [pretext] <-- [ladderhash]
    #                                             ...
    def __init__(self,
                 header, rootHash, numHashes = 24,
                 hash_function=hashlib.sha256
                ):

        self.hash_function = hash_function

        if not len(rootHash.hex())==64:
            print("Error: base preimage not in expected format")
            raise ValueError
        if not numHashes > 0:
            raise ValueError

        ladder = []
        ladder.append( self.BytesHash(rootHash) ) # first,
        for i in range(1, numHashes):             # ...and the rest.
            ladder.append( self.BytesHash(ladder[-1]) )

        # Get pretexts:
        self.pretexts = []   # strings
        self.preimages = []  # byte blobs
        self.hashes = []     # byte blobs
        for i in range(len(ladder)):
            new_pretext = "%s:i%d:%s"%(header, i, ladder[i].hex())
            new_preimage = self.StringHash(new_pretext)
            new_hash = self.BytesHash(new_preimage)
            self.pretexts.append(new_pretext)
            self.preimages.append(new_preimage)
            self.hashes.append(new_hash)


    ####
    ## HASH Helpers:
    def BytesHash(self, msgbytes):
        # Bytes blob in, bytes blob out
        return self.hash_function(msgbytes).digest()
    def StringHash(self, msgstring):
        # String in, bytes blob out
        return self.BytesHash(msgstring.encode('utf-8'))

    def getMerkleRoot(self):
        return SimpleMerkleRoot(self.hashes, self.hash_function)

    ####
    ## DIAG Helpers:
    def diag_print_contents(self):
        # Intended for diagnostics
        for h,p,t in zip(self.hashes, self.preimages, self.pretexts):
            print("%s %s %s"%(t,p.hex(),h.hex()))
        merk = SimpleMerkleRoot(self.hashes, self.hash_function)
        print("Merkle Root: %s" % merk.hex())


####
## Class:  HashTable
##
## A full table. Includes a HashLadder object.
##
class HashTable:

    class ConfigError(Exception):
        pass

    def __init__(self, targetdate, leadprice, secret, cfgsection,
                 flip=False, hash_function=hashlib.sha256):

        if isinstance(targetdate, str):
            targetdate = datetime.datetime.strptime(targetdate, "%y%m%d")
        self.date = targetdate
        self.leadprice = leadprice.price  # Unless flip is true, see below
        self.pair = leadprice.pair

        self.cfg = cfgsection   # A ConfigParser section.
        self.decadefactor =  float(self.TryReadCfgOpt('factor'))
        self.steps        =  int(self.TryReadCfgOpt('steps'))
        self.numdecades   =  int(self.TryReadCfgOpt('decades'))
        self.priceprec    =  int(self.TryReadCfgOpt('precision'))
        self.eventdesc    =  self.TryReadCfgOpt('eventdesc')
        self.reportmethod =  self.TryReadCfgOpt('reportmethod')
        self.determination = self.TryReadCfgOpt('determination')
        self.timeframe    =  self.TryReadCfgOpt('timeframe')

        self.tailprice = self.leadprice * self.decadefactor ** self.numdecades
        if (flip):  # then swap lead and tail to flip direction of table
            self.leadprice, self.tailprice = self.tailprice, self.leadprice
            self.decadefactor = 1/self.decadefactor

        self.ascending    =  (self.decadefactor > 1)
        self.descending   =  (self.decadefactor < 1)
        self.normfactor   =  self.decadefactor if self.ascending else (1/self.decadefactor)
        self.decadeword   =  "octaves" if self.normfactor==2 else "decades" if self.normfactor==10 else "multiples"
        self.gele         =  ">=" if self.descending else "<="
        self.header       =  self.ConstructPretextHeader()
        self.numhashes    =  self.steps * self.numdecades + 1
        self.roothash     =  self.getRootHash(secret)
        self.fingerprint  =  HashTable.getSecretFingerprint(secret)

        self.ladder     = HashLadder(self.header, self.roothash, self.numhashes, hash_function)
        self.merkleroot = self.ladder.getMerkleRoot()
        self.prices     = self.getPrices()


    def ConstructPretextHeader(self):
        # Header Format:
        #  YYMMDD:[gele]:BASE:QUOTE:startprice:FACTOR:STEPS
        return "%s:%s:%s:%s:%s:%s" % (
            "d%s"%self.date.strftime("%y%m%d"),
            self.gele,
            "%s"%str(self.pair),
            "%s%g"%("t" if self.descending else "b", self.leadprice),
            "f%g"%(self.normfactor),
            "s%g"%self.steps )

    def getRootHash(self, secret):
        # Returns a deterministic root hash for a priceladder by
        # hashing together a secret and the ladder header.
        if not isinstance(secret, str):
            raise ValueError
            # TODO: be flexible and accept bytes
        root_text = "%s%s"%(self.header, secret)
        return hashlib.sha256(root_text.encode('utf-8')).digest()

    def printFingerprint(self, lineleader=""):
        fplen = len(self.fingerprint)
        fplen2 = int(fplen/2)
        print(lineleader + "Fingerprint: [ %s ]" % self.fingerprint[0:fplen2])
        print(lineleader + "             [ %s ]" % self.fingerprint[fplen2:fplen])

    def getSecretFingerprint(secret):
        finger_pre = "f:"+hashlib.sha256(secret.encode('utf-8')).digest().hex()+":fingerprint"
        finger_mid = hashlib.sha256(finger_pre.encode('utf-8')).digest()
        tmpA = [x^y for x,y in zip(finger_mid[0:16], finger_mid[16:32])]
        tmpB = [(x^y)&31 for x,y in zip(tmpA[0:12], tmpA[4:16])]
        charlist = "_/|\-~..,oO:;+LTU^abspg*#378%?''"
        return ''.join(charlist[i] for i in tmpB)

    def getPrices(self, startidx=0):
        # Returns prices array for some number of decades from the originPrice
        prices = [self.leadprice]
        decadeSteps = HashTable.getDecadeSteps(self.decadefactor, self.steps)
        for i in range(self.numdecades):
            extend = [prices[-1] * ds for ds in decadeSteps]
            prices.extend(extend)
        return prices[startidx:]

    def getDecadeSteps(factor=10, steps=10):
        # Generate sequnce of product multiplier that span a "decade" of
        # proportionality given by 'factor' over a series of 'steps'
        # intervals.
        factor = float(factor)
        stepmult = factor ** (1 / steps)
        steppct = (stepmult-1)*100 if stepmult>1 else ((1/stepmult)-1)*100
        result = [ stepmult ** i for i in range(1,1+steps)]
        residual = abs(result[-1]-factor) # measure of accumulated error
        if residual > 1e-12:
            print ("Warning: Decade Residual of %g may be too large." % residual)
        result[-1] = float(factor) # prevent accumulated error of many decades
        return result

    def checkConditionMet(self, price, obsprice):
        if self.descending:
            return True if (obsprice >= price) else False
        elif self.ascending:
            return True if (obsprice <= price) else False
        else:
            raise Exception("Condition eval: table neither ascending nor descending.")

    def getGenerator(self, obsprice):
        if self.descending:
            for i in range(len(self.prices)):
                if (obsprice >= self.prices[i]):
                    return self.ladder.pretexts[i]
        elif self.ascending:
            for i in range(len(self.prices)):
                if (obsprice <= self.prices[i]):
                    return self.ladder.pretexts[i]
        else:
            raise Exception("Don't know how to select generator for table neither ascending nor descending.")

    def getResolutionPct(self, skip=1):
        stepfact = self.normfactor ** (1/self.steps)
        return ((stepfact ** skip) - 1) * 100

    def TryReadCfgOpt(self, key):
        try:
            return self.cfg[key].strip('"')
        except KeyError as e:
            msg = "Missing key '%s' in section [%s]."%(key,self.cfg.name)
            raise HashTable.ConfigError(msg) from None

    def diag_print_contents(self):
        # Intended for diagnostics
        for pc,h,p,t in zip(self.prices, self.ladder.hashes, self.ladder.preimages, self.ladder.pretexts):
            print("%g %s %s %s"%(pc, t,p.hex(),h.hex()))
        merk = SimpleMerkleRoot(self.ladder.hashes, self.ladder.hash_function)
        print("Merkle Root: %s" % merk.hex())


class HashTableMDFormatter:
    """Markdown formatter for Hash and Preimage tables"""

    warningtext = ("_**WARNING:** This is an EXPERIMENTAL Hash Oracle. At this point in time, " +
               "there is NO WARRANTY of any kind, nor any promise or commitment, implied or " +
               "otherwise, as to the reliability, accuracy, or timeliness of the information " +
               "in this post or in any future post concomitant to this one._")

    Template_HashTable_Public_Intro = textwrap.dedent("""
    (Preamble text, if any.)\n
    ## Hash Table: [%(pair)s] (Target: %(date_long)s)\n
    """ +
        "These are tables of base16-encoded SHA-256 hashes upon which HTLC contracts " +
        "may be built. Pending conditions described below, some, none, or all of the " +
        "256-bit (32-byte) base16-encoded preimages may be revealed at appointed times.\n" +
    """
    **Target Date:**
     * %(date_verbose)s\n
    **Event to Report:**
     * %(eventdesc)s\n
    **Reporting Method:**
     * %(reportmethod)s\n
    **Determination Method:**
     * %(determination)s\n
    **Time Frame:**
     * %(timeframe)s\n
    **Quote Pair:** %(pair)s\n
    """).strip("\n")+"\n\n"

    Template_HashTable_Public_Table = textwrap.dedent("""
    <hr>

    ### %(sequenceword)s Table:\n
    &nbsp;
    **Hash Header:** `%(header)s`\n
    **Simple Merkle Root:** `%(merkleroot)s`\n
    **Num Hashes:** %(numhashes)d (%(numdecades)d %(decadeword)s, %(steps)d steps each)\n
    **Resolution:** %(resskip1)0.2f%% each hash, or %(resskip2)0.2f%% every two hashes,...\n
    """+warningtext+"""\n
    Begin Table:\n
    P<sub>obs</sub> | P<sub>hash</sub> | Then preimage will reveal for this hash:
    -|-:|-
    """).strip("\n")+"\n"

    Template_PreimageTable_Reveal_Intro = textwrap.dedent("""
    (Preamble text, if any.)
    NOTE: BE SURE TO FILL OUT BACK REFERENCE URL BELOW.
    (This should link back to original hash table.)\n
    ## Preimage Reveal Table: [%(pair)s] (%(date_long)s)\n
    """ +
        "These are tables of base16-encoded 256-bit (32 byte) hash function preimages, " +
        "corresponding to one or more previously published tables of SHA256 hash values.\n" +
    """
    **Hash Table URL:**
     <PASTE URL HERE>\n
    **Target Date:**
     * %(date_verbose)s\n
    **Event Reported:**
     * %(eventdesc)s\n
    **Reporting Method:**
     * %(reportmethod)s\n
    **Determination Method:**
     * %(determination)s\n
    **Time Frame:**
     * %(timeframe)s\n
    **Quote Pair:** %(pair)s\n
    **Observed Price:** %(obsprice)s\n
    """).strip("\n")+"\n\n"

    Template_PreimageTable_Reveal_Table = textwrap.dedent("""
    <hr>

    ### %(sequenceword)s Table:\n
    &nbsp;
    **Hash Header:** `%(header)s`\n
    **Simple Merkle Root:** `%(merkleroot)s`\n
    **Generator:** `%(generator)s`\n
    """+warningtext+"""\n
    Begin Table:\n
    P<sub>obs</sub> | P<sub>hash</sub> | Preimage:
    -|-:|-
    """).strip("\n")+"\n"

    Template_Hashes_TableRow = "%s | %s | %s\n"
    Template_Preimage_TableRow = "%s | %s | %s\n"

    def __init__(self, HTobj, HTobj_alt=None):
        self.HT = HTobj
        self.HT2 = HTobj_alt  # Usually a bottom-up pair to a top-down chart.

    def getContext(self, HT, obsprice=None):
        # Get dictionary of template variables, starting with the HashTable
        # dictionary and supplementing with some additional values:
        context = {}
        context.update(HT.__dict__)
        context.update({
            "date_long": HT.date.strftime("%Y-%m-%d"),
            "date_verbose": HT.date.strftime("%B %d, %Y (%Y-%m-%d)"),
            "resskip1": HT.getResolutionPct(1),
            "resskip2": HT.getResolutionPct(2),
            "merkleroot": HT.merkleroot.hex(), # Replace/reformat as string
            "sequenceword": "Ascending" if HT.ascending else "Descending" if HT.descending else "Unsequenced"
        })
        if (obsprice is not None):
            context.update({"obsprice": ("%%0.%df"%HT.priceprec)%obsprice,
                            "generator": HT.getGenerator(obsprice)})
        return context

    def constructPublicHashTableText(self):
        context = self.getContext(self.HT)
        table_string  = HashTableMDFormatter.Template_HashTable_Public_Intro % context
        table_string += HashTableMDFormatter.Template_HashTable_Public_Table % context
        for pr, h in zip(self.HT.prices, self.HT.ladder.hashes):
            table_string+=HashTableMDFormatter.Template_Hashes_TableRow % (
                self.HT.gele, ("%%0.%df"%self.HT.priceprec)%pr, h.hex()
            )
        if (self.HT2 is not None):
            context = self.getContext(self.HT2)
            table_string += "\n" + HashTableMDFormatter.Template_HashTable_Public_Table % context
            for pr, h in zip(self.HT2.prices, self.HT2.ladder.hashes):
                table_string+=HashTableMDFormatter.Template_Hashes_TableRow % (
                    self.HT2.gele, ("%%0.%df"%self.HT2.priceprec)%pr, h.hex()
                )
        table_string += "\n" + HashTableMDFormatter.warningtext + "\n"
        return table_string

    def constructPreimageRevealTableText(self, obsprice):
        context = self.getContext(self.HT, obsprice)
        table_string  = HashTableMDFormatter.Template_PreimageTable_Reveal_Intro % context
        table_string += HashTableMDFormatter.Template_PreimageTable_Reveal_Table % context
        for pr, preimg in zip(self.HT.prices, self.HT.ladder.preimages):
            table_string+=HashTableMDFormatter.Template_Preimage_TableRow % (
                self.HT.gele, ("%%0.%df"%self.HT.priceprec)%pr,
                (preimg.hex().upper() if self.HT.checkConditionMet(pr, obsprice) else "(Condition not met)")
            )
        if (self.HT2 is not None):
            context = self.getContext(self.HT2, obsprice)
            table_string += "\n" + HashTableMDFormatter.Template_PreimageTable_Reveal_Table % context
            for pr, preimg in zip(self.HT2.prices, self.HT2.ladder.preimages):
                table_string+=HashTableMDFormatter.Template_Preimage_TableRow % (
                    self.HT2.gele, ("%%0.%df"%self.HT2.priceprec)%pr,
                    (preimg.hex().upper() if self.HT2.checkConditionMet(pr, obsprice) else "(Condition not met)")
                )
        table_string += "\n" + HashTableMDFormatter.warningtext + "\n"
        return table_string

    def printTableToConsole(self, table_string):
        print("="*24+"BEGIN_COPY_PASTE_REGION"+"="*24+"\n")
        print(table_string)
        print("="*25+"END_COPY_PASTE_REGION"+"="*25)

    def printTableToFile(self, table_string, outfile):
        with open(outfile, 'w') as table_file:
            table_file.write(table_string)
        print("((( Wrote table to file: %s"%outfile)

    def printPublicHashTable(self, outfile=None):
        table_string = self.constructPublicHashTableText()
        if not outfile:
            self.printTableToConsole(table_string)
        else:
            self.printTableToFile(table_string, outfile)

    def printPreimageRevealTable(self, obsprice, outfile=None):
        table_string = self.constructPreimageRevealTableText(obsprice)
        if not outfile:
            self.printTableToConsole(table_string)
        else:
            self.printTableToFile(table_string, outfile)


if __name__ == "__main__":

    print("Testing...")

    def hashbad(msgbytes):
        # A truly terrible 24-bit hash...
        class AwfulHash:
            def __init__(self, msgbytes):
                self.hash = hashlib.sha256(msgbytes).digest()
            def digest(self):
                return self.hash[0:3]
        return AwfulHash(msgbytes)

    topP = Price("32000 BTC:USD")
    section = str(topP.pair)+" "+"Down"
    cfg = configparser.ConfigParser()
    cfg.read('ladder.conf')

    HT = HashTable("200223", topP, "SuperSecret", cfg[section], hash_function=hashbad)

    FT = HashTableMDFormatter(HT)
    FT.printPreimageRevealTable(9010)
    HT.printFingerprint()

    print("Finished Tests.")
