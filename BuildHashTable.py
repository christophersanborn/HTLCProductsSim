#
# Hash Ladder Tool:
#
# Usage:    python3 %s <target_date> <top_price> <tag> [reveal_price]\n
#           Pair and Tag-specific config option are read from the config file
#           (ladder.conf) in section [<pair> <tag>].\n
#
# Example:  python3 %s "200110" "0.50 BTS:USD" Down\n
#           Prints descending hash table (no preimages) for Jan 10, 2020 BTS:USD
#           market, taking options from [BTS:USD Down] section.\n
#
# Example:  python3 %s "200110" "32000 BTC:USD" Down 7965.37\n
#            Prints preimage table for BTC:USD observed price of 7965.37\n
#

import configparser
import argparse
import datetime
import hashlib
import sys
import os.path
import PriceIterators
from HTLCProductsSim import *
from HashLadder import *

AppBanner = """(((
((( This is %s; A tool for building oracular hash
((( tables and conditional preimage reveal tables.
((("""%(sys.argv[0])

cfgfile='ladder.conf'

parser = argparse.ArgumentParser(
    description="Hash Ladder Tool: Make [price, hash] tables and preimage tables.",
    epilog="Pair and Tag-specific config option are read from the config file "
           "(ladder.conf) in sections [<pair> <tag>].")
parser.add_argument('targetdate', metavar="DATE", help="Target date in YYMMDD")
parser.add_argument('topprice', metavar="PRICE", help="Extremum (top or bottom) price. Ex: \"32000 BTC:USD\"")
parser.add_argument('tagstring', metavar="TAG", help="Table tag, e.g., \"Up\" or \"Down\"")
parser.add_argument('observedprice', metavar="OBS_PRICE", nargs='?', help="Observed price (numeric, without currency pair)")
parser.add_argument('--outfile', help="File to write table to (default stdout)")

if __name__ == "__main__":

    args = parser.parse_args()

    print(AppBanner)

    targetdate = args.targetdate    # e.g. "200110" for Jan 10, 2020
    topprice = args.topprice        # e.g. "32000 BTC:USD"
    tagstring = args.tagstring      # e.g. "Down" for descending table
    observedprice = float(args.observedprice) if args.observedprice else None
    outfile = args.outfile

    topP = Price(topprice)
    cfgdefaults = {"bidirectional":"False"}
    cfg = configparser.ConfigParser(cfgdefaults)
    cfg.read(cfgfile)
    section = str(topP.pair)+" "+tagstring

    try:
        secrettxt = cfg['default']['secret'].strip('"')
    except:
        print ("Could not read hash secret from config file '%s'."%cfgfile)
        quit()

    htcfg = ConfigArgsExtractor(cfg[section]).getHashTableArgs()
    mtcfg = ConfigArgsExtractor(cfg[section]).getMultiTableArgs()

    HT_list = []
    for flip in [False, True] if mtcfg['bidirectional'] else [False]:
        for plane in mtcfg['planes']:
            PriceIter = PriceIterators.New(
                startprice=topP.price, **htcfg['priceargs'],
                plane=plane, flip=flip
            )
            HT_list.append(
                HashTable(targetdate, topP.pair, PriceIter,
                          secrettxt, htcfg, plane=plane, flip=flip)
            )

    FT = HashTableMDFormatter(HT_list)

    print ("((( An oracle SECRET was read from file '%s'.\n((("%cfgfile)
    HT_list[0].printFingerprint(lineleader="((( ")
    print("(((")

    def check_outfile():
        if outfile is not None:
            print ("((( Table output to be written to: %s"%outfile)
            if os.path.exists(outfile):
                print("Output file exists. Will not overwrite. Exiting.")
                quit()
            print("(((")

    if observedprice:
        print("((( You have requested: PREIMAGE TABLE from section [%s]"%section)
        print("(((        target date: %s, observed price: %g.\n((("%(targetdate, observedprice))
        check_outfile()
        FT.printPreimageRevealTable(observedprice, outfile)
        print("(((\n((( This concludes: PREIMAGE TABLE from section [%s] target date: %s, observed price: %g.\n((("%(section, targetdate, observedprice))
    else:
        print("((( You have requested: HASH TABLE from section [%s] target date: %s.\n((("%(section, targetdate))
        check_outfile()
        FT.printPublicHashTable(outfile)
        print("(((\n((( This concludes: HASH TABLE from section [%s] target date: %s.\n((("%(section, targetdate))

    if outfile is None:
        HT_list[0].printFingerprint(lineleader="((( ")
        print("(((")
