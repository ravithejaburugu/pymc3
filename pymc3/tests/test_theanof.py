import itertools
import unittest
import numpy as np
import theano
from ..theanof import DataGenerator, GeneratorOp, generator
from theano.tests import unittest_tools as utt
from pymc3.theanof import LogDet, logdet
from .helpers import SeededTest

def integers():
    i = 0
    while True:
        yield np.float32(i)
        i += 1


def integers_ndim(ndim):
    i = 0
    while True:
        yield np.ones((2,) * ndim) * i
        i += 1

class TestLogDet(SeededTest):

    def setUp(self):
        utt.seed_rng()
        self.op_class = LogDet
        self.op = logdet

    def validate(self, input_mat):
        x = theano.tensor.matrix()
        f = theano.function([x], self.op(x))
        out = f(input_mat)
        svd_diag = np.linalg.svd(input_mat, compute_uv=False)
        numpy_out = np.sum(np.log(np.abs(svd_diag)))

        # Compare the result computed to the expected value.
        utt.assert_allclose(numpy_out, out)

        # Test gradient:
        utt.verify_grad(self.op, [input_mat])

    def test_basic(self):
        # Calls validate with different params
        test_case_1 = np.random.randn(3, 3) / np.sqrt(3)
        test_case_2 = np.random.randn(10, 10) / np.sqrt(10)
        self.validate(test_case_1.astype(theano.config.floatX))
        self.validate(test_case_2.astype(theano.config.floatX))


class TestGenerator(unittest.TestCase):
    def test_basic(self):
        generator = DataGenerator(integers())
        gop = GeneratorOp(generator)()
        self.assertEqual(gop.tag.test_value, np.float32(0))
        f = theano.function([], gop)
        self.assertEqual(f(), np.float32(0))
        self.assertEqual(f(), np.float32(1))
        for _ in range(2, 100):
            f()
        self.assertEqual(f(), np.float32(100))

    def test_ndim(self):
        for ndim in range(10):
            res = list(itertools.islice(integers_ndim(ndim), 0, 2))
            generator = DataGenerator(integers_ndim(ndim))
            gop = GeneratorOp(generator)()
            f = theano.function([], gop)
            self.assertEqual(ndim, res[0].ndim)
            np.testing.assert_equal(f(), res[0])
            np.testing.assert_equal(f(), res[1])

    def test_cloning_available(self):
        gop = generator(integers())
        res = gop ** 2
        shared = theano.shared(np.float32(10))
        res1 = theano.clone(res, {gop: shared})
        f = theano.function([], res1)
        self.assertEqual(f(), np.float32(100))

    def test_nans_produced(self):
        def gen():
            for _ in range(2):
                yield np.ones((10, 10))

        gop = generator(gen())
        f = theano.function([], gop)
        res = [f() for _ in range(3)]
        np.testing.assert_equal(np.ones((10, 10)), res[0])
        np.testing.assert_equal(np.ones((10, 10)), res[1])
        self.assertTrue(res[2].shape == (10, 10))
        self.assertTrue(np.isnan(res[2]).all())

    def test_setvalue(self):
        def gen():
            for _ in range(2):
                yield np.ones((10, 10))

        gop = generator(gen())
        f = theano.function([], gop)
        res = [f() for _ in range(3)]
        np.testing.assert_equal(np.ones((10, 10)), res[0])
        np.testing.assert_equal(np.ones((10, 10)), res[1])
        self.assertTrue(res[2].shape == (10, 10))
        self.assertTrue(np.isnan(res[2]).all())
        gop.set_gen(gen())
        res = [f() for _ in range(3)]
        np.testing.assert_equal(np.ones((10, 10)), res[0])
        np.testing.assert_equal(np.ones((10, 10)), res[1])
        self.assertTrue(res[2].shape == (10, 10))
        self.assertTrue(np.isnan(res[2]).all())
