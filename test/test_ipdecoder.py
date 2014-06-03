# -*- coding: utf-8 -*-
# Copyright 2014 Michael Helmling
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation

import unittest

import numpy as np

from lpdec.codes import BinaryLinearBlockCode
from lpdec.channels import *
from lpdec.codes.classic import HammingCode
from lpdec.decoders.ip import CplexIPDecoder
from lpdec.persistence import JSONDecodable
from . import testData
from test import requireCPLEX


class TestCplexIPDecoder(unittest.TestCase):
    """Run various test with the (23, 12) Golay code."""
    
    def setUp(self):
        self.code = BinaryLinearBlockCode(parityCheckMatrix=testData('Alist_N23_M11.txt'))

    @requireCPLEX
    def test_minDistance(self):
        """Test if the minimum distance computation works."""
        self.decoder = CplexIPDecoder(self.code)
        distance, codeword = self.decoder.minimumDistance()
        self.assertEqual(distance, 7)
        self.assertEqual(codeword.sum(), 7)
        self.assertIsInstance(codeword, np.ndarray)

    @requireCPLEX
    def test_decoding(self):
        seed = 3498543
        for snr in [0, 2, 4]:
            channelRC = AWGNC(snr, self.code.rate, seed=seed)
            channelZC = AWGNC(snr, self.code.rate, seed=seed)
            decoder = CplexIPDecoder(self.code, cplexParams={'threads': 1})
            sigRC = channelRC.signalGenerator(self.code, wordSeed=seed)
            sigZC = channelZC.signalGenerator(self.code, wordSeed=-1)
            for i in range(10):
                llrRC = next(sigRC)
                llrZC = next(sigZC)
                for useHint in True, False:
                    if useHint:
                        hintRC = sigRC.encoderOutput
                        hintZC = sigZC.encoderOutput
                    else:
                        hintRC = hintZC = None
                    outputRC = decoder.decode(llrRC, sent=hintRC)
                    objRC = decoder.objectiveValue
                    strikedRC = decoder.callback.occured
                    if useHint:
                        self.assertNotEqual(strikedRC, decoder.mlCertificate)
                    outputZC = decoder.decode(llrZC, sent=hintZC)
                    objZC = decoder.objectiveValue
                    strikedZC = decoder.callback.occured
                    if useHint:
                        self.assertNotEqual(strikedZC, decoder.mlCertificate)
                    errorRC = not np.allclose(outputRC, sigRC.encoderOutput)
                    errorZC = not np.allclose(outputZC, sigZC.encoderOutput)
                    self.assertEqual(errorRC, errorZC)
                    if not useHint or (not strikedRC and not strikedZC):
                        self.assertTrue(np.allclose(objRC, objZC + sigRC.correctObjectiveValue()))


class TestCplexIPPersistence(unittest.TestCase):

    def setUp(self):
        self.code = HammingCode(4)

    @requireCPLEX
    def testDefault(self):
        decoders = [CplexIPDecoder(self.code),
                    CplexIPDecoder(self.code, name='OtherDecoder'),
                    CplexIPDecoder(self.code, cplexParams=dict(threads=1))]
        for decoder in decoders:
            self.assertEqual(len(decoders[0].cplex.parameters.get_changed()), 0)
            parms = decoder.toJSON()

            reloaded = JSONDecodable.fromJSON(parms, code=self.code)
            self.assertEqual(decoder, reloaded)

            def reprParms(cpx):
                return [(repr(x), y) for (x, y) in cpx.parameters.get_changed()]
            self.assertEqual(reprParms(decoder.cplex),
                             reprParms(reloaded.cplex))