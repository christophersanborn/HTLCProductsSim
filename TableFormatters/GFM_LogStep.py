# GFM_LogStep.py
#
# A formatter plugin for Logarithmically stepped hash tables formatted
# for GitHub-Flavored Markdown (GFM), e.g. as used by Steemit
# articles.
#
# Generally not imported directly.
# Use TableFormatters.GetFMT("gfm_logstep", ...) to get instance.
#
import textwrap
from .common import *

@register_formatter("default")
@register_formatter("gfm_logstep")
class Formatter:
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
    **Num Hashes:** %(numhashes)d (%(structure)s)\n
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

    def __init__(self, HTObjOrList, HTobj_alt=None):
        self.HT = HTObjOrList if isinstance(HTObjOrList, list) else [HTObjOrList]
        if HTobj_alt is not None:
            self.HT.append(HTobj_alt) # Often a bottom-up pair to a top-down chart.

    def getContext(self, HT, obsprice=None):
        # Get dictionary of template variables, starting with the HashTable
        # dictionary and supplementing with some additional values:
        def ResolutionPct(p1, p2):
            ratio = p2/p1 if p2>p1 else p1/p2
            return (ratio-1) * 100
        context = HT.getDescriptiveContext()
        context.update({
            "date_long": HT.date.strftime("%Y-%m-%d"),
            "date_verbose": HT.date.strftime("%B %d, %Y (%Y-%m-%d)"),
            "resskip1": ResolutionPct(HT.prices[0], HT.prices[1]),
            "resskip2": ResolutionPct(HT.prices[0], HT.prices[2]),
            "merkleroot": HT.merkleroot.hex(), # Replace/reformat as string
            "sequenceword": "Ascending" if HT.predicate[0]=="<" else "Descending" if HT.predicate[0]==">" else "Unsequenced"
        })
        if (obsprice is not None):
            context.update({"obsprice": ("%%0.%df"%HT.priceprec)%obsprice,
                            "generator": HT.getGenerator(obsprice)})
        return context

    def constructPublicHashTableText(self):
        context = self.getContext(self.HT[0])
        table_string  = Formatter.Template_HashTable_Public_Intro % context
        for i in range(len(self.HT)):
            context = self.getContext(self.HT[i])
            table_string += Formatter.Template_HashTable_Public_Table % context
            for pr, h in zip(self.HT[i].prices, self.HT[i].ladder.hashes):
                table_string+=Formatter.Template_Hashes_TableRow % (
                    self.HT[i].predicate, ("%%0.%df"%self.HT[i].priceprec)%pr, h.hex()
                )
            table_string += "\n"
        table_string += Formatter.warningtext + "\n"
        return table_string

    def constructPreimageRevealTableText(self, obsprice):
        context = self.getContext(self.HT[0], obsprice)
        table_string  = Formatter.Template_PreimageTable_Reveal_Intro % context
        for i in range(len(self.HT)):
            context = self.getContext(self.HT[i], obsprice)
            table_string += Formatter.Template_PreimageTable_Reveal_Table % context
            for pr, preimg in zip(self.HT[i].prices, self.HT[i].ladder.preimages):
                table_string+=Formatter.Template_Preimage_TableRow % (
                    self.HT[i].predicate, ("%%0.%df"%self.HT[i].priceprec)%pr,
                    (preimg.hex().upper() if self.HT[i].checkConditionMet(pr, obsprice) else "(Condition not met)")
                )
            table_string += "\n"
        table_string += Formatter.warningtext + "\n"
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
