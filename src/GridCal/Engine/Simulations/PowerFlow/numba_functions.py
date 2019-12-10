# This file is part of GridCal.
#
# GridCal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GridCal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GridCal.  If not, see <http://www.gnu.org/licenses/>.


import numba as nb
import numpy as np


@nb.njit("c16[:](i8, i4[:], i4[:], c16[:], c16[:], c16[:], i8)", parallel=True)
def calc_power_csr_numba(n, Yp, Yj, Yx, V, I, n_par=500):
    """
    Compute the power vector from the CSR admittance matrix
    :param m: number of rows
    :param n: number of columns
    :param Yp: pointers
    :param Yj: indices
    :param Yx: data
    :param V: vector x (n)
    :param I
    :param n_par: Number upon which the computation is done in parallel
    :return: vector y (m)
    """

    assert n == V.shape[0]
    S = np.zeros(n, dtype=nb.complex128)

    if n < n_par:
        # serial version
        for i in range(n):  # for every row
            s = complex(0, 0)
            for p in range(Yp[i], Yp[i+1]):  # for every column
                s += Yx[p] * V[Yj[p]]
            S[i] = V[i] * np.conj(s - I[i])
    else:
        # parallel version
        for i in nb.prange(n):  # for every row
            s = complex(0, 0)
            for p in range(Yp[i], Yp[i+1]):  # for every column
                s += Yx[p] * V[Yj[p]]
            S[i] = V[i] * np.conj(s - I[i])
    return S