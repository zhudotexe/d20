"""
This module exposes a default implementation of the RNG based on the environment the library is installed in.

In a thin installation, this will be MT2002 as implemented in the random stdlib module.
If numpy is installed, this will be PCG64DXSM or PCG64 if available. If neither are available, it will fall back
to whatever NumPy decides is a sane default for a bit generator
(see https://numpy.org/doc/stable/reference/random/bit_generators/index.html).

For more information, see https://github.com/avrae/d20/issues/7.

Thanks to @posita for inspiring the implementation of NumpyRandom.
"""

import random
from typing import Any, NewType, Optional, Sequence, TYPE_CHECKING, Union

__all__ = ("random_impl",)

_BitGenT = NewType('_BitGenT', Any)
_SeedT = Optional[Union[int, Sequence[int]]]

# the default random implementation - just use stdlib random (MT2002)
random_impl = random.Random()

# if np is installed and it has the random module, make use of PCG64
# todo tests, docs
try:
    import numpy.random  # added in numpy 1.17
    from numpy.random import Generator

    if TYPE_CHECKING:
        try:
            # this was only exposed in numpy 1.19 - we only import these for type checking
            # noinspection PyUnresolvedReferences
            from numpy.random import BitGenerator, SeedSequence

            _BitGenT = BitGenerator
            _SeedT = Union[_SeedT, SeedSequence]
        except ImportError:
            pass


    class NumpyRandom(random.Random):
        def __init__(self, generator: _BitGenT, x: _SeedT = None):
            self._gen = Generator(generator)
            super().__init__(x)

        def random(self) -> float:
            return self._gen.random()

        def getrandbits(self, k: int) -> int:
            if k < 0:
                raise ValueError('number of bits must be non-negative')
            numbytes = (k + 7) // 8  # bits / 8 and rounded up
            x = int.from_bytes(self._gen.bytes(numbytes), 'big')
            return x >> (numbytes * 8 - k)  # trim excess bits

        def seed(self, a: _SeedT = None, version: int = 2):
            # note that this takes in a different type than random.Random.seed()
            # this is because BitGenerator's seed requires an int/sequence of ints, while Random accepts
            # floats, strs, etc; for the common case we expect the user to pass an int
            bg_type = type(self._gen.bit_generator)
            self._gen = Generator(bg_type(a))

        def getstate(self):
            return self._gen.bit_generator.state

        def setstate(self, state):
            self._gen.bit_generator.state = state


    if hasattr(numpy.random, "PCG64DXSM"):  # available in numpy 1.21 and up
        random_impl = NumpyRandom(numpy.random.PCG64DXSM())
    elif hasattr(numpy.random, "PCG64"):  # available in numpy 1.17 and up
        random_impl = NumpyRandom(numpy.random.PCG64())
    elif hasattr(numpy.random, "default_rng"):
        random_impl = NumpyRandom(numpy.random.default_rng().bit_generator)
except ImportError:
    pass