#!/usr/bin/env python
from __future__ import absolute_import,  unicode_literals, print_function

import os
import sys
import hashlib
import collections
import multiprocessing
from functools import partial

PY3 = sys.version_info >= (3,0,0)

class DataIntegrityFingerprint:
    """A class representing a DataIntegrityFingerprint (DIF).

    Example
    -------
    dif = DataIntegrityFingerPrint("~/Downloads")
    dif.generate()
    print(dif)

    """

    def __init__(self, data, hash_algorithm="sha256"): # TODO: Why not specifying data folder with generate?
        """Create a DataIntegrityFingerprint object.

        Parameters
        ----------
        data : str
            the path to the data
        hash_algorithm : str
            the hash algorithm (optional, default: sha256)

        """

        if hash_algorithm not in hashlib.algorithms_available:
            raise ValueError('unsupported hash type ' + name)

        self._hash_algorithm = hash_algorithm
        self._data = os.path.abspath(data)
        self._file_hashes = collections.OrderedDict()
        if os.path.isfile(data):
            self._file_hashes[data] = None
        else:
            for dir_, _, files in os.walk(self._data):
                for filename in files:
                    filename = os.path.join(os.path.relpath(dir_, self._data),
                                            filename)
                    if filename.startswith("./"):
                        filename = filename[2:]
                    self._file_hashes[filename] = None

    def __str__(self):
        return str(self.master_hash)

    @property
    def data(self):
        return self._data

    @property
    def file_hashes(self):
        return self._file_hashes

    @property
    def master_hash(self):
        """DOCU"""

        if self._file_hashes is None:
            return None

        file_hashes = sorted(self._file_hashes.values())
        if len(file_hashes) > 1:
            hasher = hashlib.new(self._hash_algorithm)
            for file_hash in file_hashes:
                hasher.update(file_hash.encode("ascii"))
            return hasher.hexdigest()
        else:
            return self._file_hashes[self._file_hashes.keys()[0]]

    def generate(self, progress=None):
        """Calculate the fingerprint.

        Parameters
        ----------
        progress: function, optional
            a callback function for a progress reporting that takes the
            following parameters:
                count  -- the current count
                total  -- the total count
                status -- a string describing the status

        """

        if len(self._file_hashes) > 1:
            tmp = [os.path.join(self._data, filename) for \
                   filename in self._file_hashes.keys()]
            func = partial(_hash_file, hash_algorithm = self._hash_algorithm)
            for counter, rtn in enumerate(
                    multiprocessing.Pool().imap_unordered(func, tmp)):
                if progress is not None:
                    progress(counter + 1, len(self._file_hashes),
                             "{0}/{1} files".format(counter + 1,
                                                    len(self._file_hashes)))
                self._file_hashes[rtn[0].replace(
                    self._data + os.path.sep, "")] = rtn[1]
        else:
            rtn = _hash_file(self._file_hashes.keys()[0])
            self._file_hashes[rtn[0]] = rtn[1]


    def load_hash_file(self, filename):
        """load hash list"""
        self._file_hashes = {}
        with open(filename, "rb") as fl:
            for l in fl:
                tmp = string_decode(l).strip().split("  ")
                if len(tmp) == 2:
                    self._file_hashes[tmp[1]] = tmp[0]


def string_decode(s, enc='utf-8', errors='strict'):
    """bytestring to unicode"""

    if (PY3 and isinstance(s, str)) or (not PY3 and isinstance(s, unicode)):
        return s
    if (PY3 and isinstance(s, bytes)) or (not PY3 and isinstance(s, str)):
        return s.decode(enc, errors)


def _hash_file(filename, hash_algorithm):
    hasher = hashlib.new(hash_algorithm)
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(64*1024), b''):
            hasher.update(block)
    return filename, hasher.hexdigest()


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(
            description="Create a Data Integrity Fingerprint (DIF).",
            epilog="(c) F. Krause & O. Lindemann")
    parser.add_argument("PATH", nargs='?', default=None,
                        help="the path to the data folder or file")
    parser.add_argument("-c", "--checksums", dest="checksums",
                        action="store_true",
                        help="save checksums to file",
                        default = False)
    parser.add_argument("-f", "--hashfile", dest="hashfile",
                        action="store_true",
                        help="create DIF from existing hash file",
                        default = False)
    args = vars(parser.parse_args())

    if args["PATH"] is None:
        print("Use -h for help")
        sys.exit()

    if sys.version[0] == '2':
        input = raw_input
        args["PATH"] = args["PATH"].decode(sys.stdin.encoding)

    def progress(count, total, status=''):
        bar_len = 50
        filled_len = int(round(bar_len * count / float(total)))
        percents = round(100.0 * count / float(total), 1)
        bar = '=' * filled_len + ' ' * (bar_len - filled_len)
        sys.stdout.write('{:5.1f}% [{}] {}\r'.format(percents, bar, status))
        sys.stdout.flush()

    if args['hashfile']:
        dif = DataIntegrityFingerprint(data=".", hash_algorithm="sha256")
        dif.load_hash_file(args["PATH"])
    else:
        dif = DataIntegrityFingerprint(data=args["PATH"], hash_algorithm="sha256")
        dif.generate(progress=progress)
        print("")
    print("DIF: {0}".format(dif))

    if args['checksums']:
        import codecs
        outfile = os.path.split(dif.data)[-1] + ".sha256"
        answer = "y"
        if os.path.exists(outfile):
            answer = input(
                    "'{0}' already exists! Overwrite? [y/N]: ".format(outfile))
        if answer == "y":
            with codecs.open(outfile, 'w', encoding="utf-8") as f:
                for filename in dif.file_hashes:
                    f.write(dif.file_hashes[filename] + "  " + os.path.join(
                        os.path.split(dif._data)[1], filename + "\n"))
            print("Checksums have been written to '{0}'.".format(outfile))
        else:
            print("Checksums have NOT been written.".format(outfile))

