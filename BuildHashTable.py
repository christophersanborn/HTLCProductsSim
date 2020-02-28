#
#
import configparser
import datetime
import hashlib
import sys
from HTLCProductsSim import *
from HashLadder import *


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

AppBanner = """(((
((( This is %s; A tool for building oracular hash
((( tables and conditional preimage reveal tables.
((("""%(sys.argv[0])

cfgfile='ladder.conf'

if __name__ == "__main__":

    print(AppBanner)

    if len(sys.argv) < 4:
        print(AppDesc)
        quit()

    targetdate = sys.argv[1]    # e.g. "200110" for Jan 10, 2020
    topprice = sys.argv[2]      # e.g. "32000 BTC:USD"
    tagstring = sys.argv[3]     # e.g. "Down" for descending table
    observedprice = float(sys.argv[4]) if len(sys.argv)>4 else None

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

    HT = HashTable(targetdate, topP, secrettxt, cfg[section])
    HT2 = None
    if (cfg.getboolean(section,'bidirectional')):
        HT2 = HashTable(targetdate, topP, secrettxt, cfg[section], flip=True)
    FT = HashTableMDFormatter(HT, HT2)

    print ("((( An oracle SECRET was read from file '%s'.\n"%cfgfile)
    HT.printFingerprint()
    print("\n(((")

    if observedprice:
        print("((( You have requested: PREIMAGE TABLE from section [%s]"%section)
        print("(((        target date: %s, observed price: %g.\n((("%(targetdate, observedprice))
        FT.printPreimageRevealTable(observedprice)
        print("(((\n((( This concludes: PREIMAGE TABLE from section [%s] target date: %s, observed price: %g.\n((("%(section, targetdate, observedprice))
    else:
        print("((( You have requested: HASH TABLE from section [%s] target date: %s.\n((("%(section, targetdate))
        FT.printPublicHashTable()
        print("(((\n((( This concludes: HASH TABLE from section [%s] target date: %s.\n((("%(section, targetdate))

    HT.printFingerprint()
