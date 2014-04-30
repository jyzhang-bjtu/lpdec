#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Copyright 2011-2012 Michael Helmling
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation

import unittest
import os.path
from collections import defaultdict, OrderedDict
from lpdec.codes import BinaryLinearBlockCode
from lpdec.channels import *
from lpdec.decoders.ip import CplexIPDecoder

import numpy as np
from . import testData


class TestCplexIPDecoder(unittest.TestCase):
    """Run various test with an (8,4) code."""
    
    def setUp(self):
        self.code = BinaryLinearBlockCode(parityCheckMatrix=testData('Alist_N23_M11.txt'))
    
    def test_minDistance(self):
        """Test if the minimum distance computation works."""
        try:
            import cplex
        except ImportError:
            self.skipTest('CPLEX is not installed')
        self.decoder = CplexIPDecoder(self.code)
        distance, codeword = self.decoder.minimumDistance()
        self.assertEqual(distance, 4)
        self.assertEqual(codeword.sum(), 4)
        self.assertIsInstance(codeword, np.ndarray)

    def test_decoding(self):
        seed = 3498543
        for snr in [0, 1.5, 4]:
            channelRC = AWGNC(snr, self.code.rate, seed=seed)
            channelZC = AWGNC(snr, self.code.rate, seed=seed)
            decoderNormal = CplexIPDecoder(self.code)
            decoderSC = CplexIPDecoder(self.code, shortCallback=True)
            sigRC = channelRC.signalGenerator(self.code, wordSeed=seed, randomCodewords=True)
            sigZC = channelZC.signalGenerator(self.code, wordSeed=seed, randomCodewords=False)
            for i in range(100):
                llrRC = next(sigRC)
                llrZC = next(sigZC)
                for decoder in decoderNormal, decoderSC:
                    for useHint in True, False:
                        if useHint:
                            hintRC = sigRC.encoderOutput
                            hintZC = sigZC.encoderOutput
                        else:
                            hintRC = hintZC = None
                        outputRC = decoder.decode(llrRC, hint=hintRC)
                        objRC = decoder.objectiveValue
                        strikedRC = decoderSC.callback.occured
                        outputZC = decoder.decode(llrZC, hint=hintZC)
                        objZC = decoder.objectiveValue
                        strikedSC = decoderSC.callback.occured
                        errorRC = not np.allclose(outputRC, sigRC.encoderOutput)
                        errorZC = not np.allclose(outputZC, sigZC.encoderOutput)
                        if errorRC != errorZC:
                            print(errorRC, errorZC, useHint, strikedRC, strikedSC, decoder is
                                                                        decoderSC)
                            print(objRC, objZC + sigRC.correctObjectiveValue(), sigRC.correctObjectiveValue())
                        if decoder is decoderNormal:
                            if not np.allclose(objRC, objZC + sigRC.correctObjectiveValue()):
                                print('urgh', objRC, objZC + sigRC.correctObjectiveValue())


if __name__=='__main__':
    unittest.main()