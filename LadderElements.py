#
import hashlib

def SimpleMerkleRoot(hashes, hash_function=hashlib.sha256):
    """
    Return the "Simple" Merkle Root Hash as a byte blob from an iterable
    ordered list of byte blobs containing the leaf node hashes.

    Works by recursively hashing together pairs of consecutive hashes to
    form a reduced set one level up from the leafs, repeat until we are
    reduced to a single hash.  If list is odd-length, then last element is
    copied, not hashed.

    """

    def BytesHasher(msgbytes):
        return hash_function(msgbytes).digest()

    if len(hashes) == 0:
        hashes = [ BytesHasher(bytes()) ] # Hash of empty data

    #line = ""
    #for h in hashes:
    #    line = line + h.hex() + "  "
    #print(line)

    if len(hashes) == 1:
        return hashes[0]

    reduced = []
    ilast = len(hashes) - 1

    for i in range(len(hashes))[0::2]: # 0, 2, 4, 6, ...
        if i < ilast:
            pre = hashes[i] + hashes[i+1]
            reduced.append( BytesHasher(pre) )
        else:
            reduced.append(hashes[i])

    return SimpleMerkleRoot(reduced, hash_function)


if __name__ == "__main__":

    print ("Aye!")

    pretexts = []#"A","B","C"]#,"D"]
    hashes = [hashlib.sha256(bytes(s,'utf8')).digest() for s in pretexts]

    root = SimpleMerkleRoot(hashes)
