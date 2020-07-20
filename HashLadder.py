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
import json
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

    def __init__(self, targetdate, pricepair, priceiter, secret, cfg,
                 plane=1, flip=False, hash_function=hashlib.sha256):

        if isinstance(targetdate, str):
            targetdate = datetime.datetime.strptime(targetdate, "%y%m%d")
        self.date = targetdate
        self.pair = pricepair

        self.PriceItr = priceiter
        self.prices = self.PriceItr.prices

        self.predicates = cfg['predicates']
        self.predicate = self.predicates[0 if not flip else 1]

        self.priceprec    =  cfg['precision']
        self.eventdesc    =  cfg['eventdesc']
        self.reportmethod =  cfg['reportmethod']
        self.determination = cfg['determination']
        self.timeframe    =  cfg['timeframe']

        self.header       =  self.ConstructPretextHeader()
        self.numhashes    =  len(self.prices)
        self.roothash     =  self.getRootHash(secret)
        self.fingerprint  =  HashTable.getSecretFingerprint(secret)

        self.ladder     = HashLadder(self.header, self.roothash, self.numhashes, hash_function)
        self.merkleroot = self.ladder.getMerkleRoot()


    def ConstructPretextHeader(self):
        # Header Format:
        #  YYMMDD:predicate:BASE:QUOTE:[PRICEHEADER...]
        return "%s:%s:%s:%s" % (
            "d%s"%self.date.strftime("%y%m%d"),
            self.predicate,
            "%s"%str(self.pair),
            "%s"%self.PriceItr
        )

    def getRootHash(self, secret):
        # Returns a deterministic root hash for a priceladder by
        # hashing together a secret and the ladder header.
        if not isinstance(secret, str):
            raise ValueError
            # TODO: be flexible and accept bytes
        root_text = "%s%s"%(self.header, secret)
        return hashlib.sha256(root_text.encode('utf-8')).digest()

    def getDescriptiveContext(self):    # Metadata, basically
        context = {}
        context.update(self.__dict__)   # TODO: be more selective about included keys
        context.update(self.PriceItr.getDescriptiveContext())
        return context

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

    def checkPredicate(self, l, r):
        if self.predicate == ">=":
            compare = lambda l,r: l >= r
        elif self.predicate == "<=":
            compare = lambda l,r: l <= r
        else:
            raise Exception("Don't know how to apply predicate '%s'."%self.predicate)
        return compare(l,r)

    def checkConditionMet(self, price, obsprice):
        return True if self.checkPredicate(obsprice, price) else False

    def getGenerator(self, obsprice):
        for i in range(len(self.prices)):
            if self.checkPredicate(obsprice, self.prices[i]):
                return self.ladder.pretexts[i]

    def diag_print_contents(self):
        # Intended for diagnostics
        for pc,h,p,t in zip(self.prices, self.ladder.hashes, self.ladder.preimages, self.ladder.pretexts):
            print("%g %s %s %s"%(pc, t,p.hex(),h.hex()))
        merk = SimpleMerkleRoot(self.ladder.hashes, self.ladder.hash_function)
        print("Merkle Root: %s" % merk.hex())


class ConfigArgsExtractor:
    # Convert configparser sections to dicts
    def __init__(self, configparsersection):
        self.section = configparsersection

    def getHashTableArgs(self):
        cfg = self.section
        args = {}
        args['priceargs'] = json.loads(cfg.get('prices', fallback="{}").strip('"'))
        args['predicates'] = json.loads(cfg.get('predicates', fallback="[]").strip('"'))
        args['precision'] = int(cfg.get('precision', fallback="8").strip('"'))
        args['formatter'] = cfg.get('formatter', fallback="default").strip('"')
        for key in ["eventdesc", "reportmethod", "determination", "timeframe"]:
            args[key] = cfg.get(key, fallback="N/A").strip('"')
        return args

    def getMultiTableArgs(self):
        cfg = self.section
        args = {}
        args['bidirectional'] = cfg.getboolean('bidirectional', fallback=False)
        planes = json.loads(cfg.get('planes', fallback="[1]").strip('"'))
        planes = planes if isinstance(planes, list) else [planes]
        args['planes'] = planes
        return args


if __name__ == "__main__":

    import PriceIterators

    print("Testing...")

    def hashbad(msgbytes):
        # A truly terrible 24-bit hash...
        class AwfulHash:
            def __init__(self, msgbytes):
                self.hash = hashlib.sha256(msgbytes).digest()
            def digest(self):
                return self.hash[0:3]
        return AwfulHash(msgbytes)

    topP = Price("32000 CJS:EUR")
    section = str(topP.pair)+" "+"Down"
    cfg = configparser.ConfigParser()
    cfg.read('ladder.conf')
    htcfg = ConfigArgsExtractor(cfg[section]).getHashTableArgs()
    mtcfg = ConfigArgsExtractor(cfg[section]).getMultiTableArgs()

    PriceIter = PriceIterators.New(**htcfg['priceargs'], startprice=topP.price)

    HT = HashTable("200223", topP.pair, PriceIter, "SuperSecret", htcfg, hash_function=hashbad)

    FT = HashTableMDFormatter(HT)
    FT.printPreimageRevealTable(9010)
    HT.printFingerprint()

    print("Finished Tests.")
