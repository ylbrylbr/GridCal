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

"""
This file implements a DC-OPF for time series
That means that solves the OPF problem for a complete time series at once
"""
from GridCal.Engine.Core.numerical_circuit import NumericalCircuit
from GridCal.Engine.Simulations.OPF.opf_templates import Opf
from GridCal.ThirdParty.pulp import *


def add_objective_function(Pg, Pb, LSlack, FSlack1, FSlack2,
                           cost_g, cost_b, cost_l, cost_br):
    """
    Add the objective function to the problem
    :param Pg: generator LpVars (ng, nt)
    :param Pb: batteries LpVars (nb, nt)
    :param LSlack: Load slack LpVars (nl, nt)
    :param FSlack1: Branch overload slack1 (m, nt)
    :param FSlack2: Branch overload slack2 (m, nt)
    :param cost_g: Cost of the generators (ng, nt)
    :param cost_b: Cost of the batteries (nb, nt)
    :param cost_l: Cost of the loss of load (nl, nt)
    :param cost_br: Cost of the overload (m, nt)
    :return: Nothing, just assign the objective function
    """

    f_obj = (cost_g * Pg).sum()

    f_obj += (cost_b * Pb).sum()

    f_obj += (cost_l * LSlack).sum()

    f_obj += (cost_br * (FSlack1 + FSlack2)).sum()

    return f_obj


def set_fix_generation(problem, Pg, P_fix, enabled_for_dispatch):
    """
    Set the generation fixed at the non dispatchable generators
    :param problem: LP problem instance
    :param Pg: Array of generation variables
    :param P_fix: Array of fixed generation values
    :param enabled_for_dispatch: array of "enables" for dispatching generators
    :return: Nothing
    """

    idx = np.where(enabled_for_dispatch == False)[0]

    lpAddRestrictions2(problem=problem,
                       lhs=Pg[idx],
                       rhs=P_fix[idx],
                       name='fixed_generation',
                       op='=')


def get_power_injections(C_bus_gen, Pg, C_bus_bat, Pb, C_bus_load, LSlack, Pl):
    """
    Create the power injections per bus
    :param C_bus_gen: Bus-Generators sparse connectivity matrix (n, ng)
    :param Pg: generator LpVars (ng, nt)
    :param C_bus_bat: Bus-Batteries sparse connectivity matrix (n, nb)
    :param Pb: Batteries LpVars (nb, nt)
    :param C_bus_load: Bus-Load sparse connectivity matrix (n, nl)
    :param LSlack: Load slack LpVars (nl, nt)
    :param Pl: Load values (nl, nt)
    :return: Power injection at the buses (n, nt)
    """

    P = lpDot(C_bus_gen.transpose(), Pg)

    P += lpDot(C_bus_bat.transpose(), Pb)

    P -= lpDot(C_bus_load.transpose(), Pl - LSlack)

    return P


def add_dc_nodal_power_balance(numerical_circuit, problem: LpProblem, theta, P):
    """
    Add the nodal power balance
    :param numerical_circuit: NumericalCircuit instance
    :param problem: LpProblem instance
    :param theta: Voltage angles LpVars (n, nt)
    :param P: Power injection at the buses LpVars (n, nt)
    :return: Nothing, the restrictions are added to the problem
    """

    # do the topological computation
    calculation_inputs = numerical_circuit.compute()

    nodal_restrictions = np.empty(numerical_circuit.nbus, dtype=object)

    # simulate each island and merge the results
    for i, calc_inpt in enumerate(calculation_inputs):

        # if there is a slack it means that there is at least one generator,
        # otherwise these equations do not make sense
        if len(calc_inpt.ref) > 0:

            # find the original indices
            bus_original_idx = np.array(calc_inpt.original_bus_idx)

            # re-pack the variables for the island and time interval
            P_island = P[bus_original_idx]  # the sizes already reflect the correct time span
            theta_island = theta[bus_original_idx]  # the sizes already reflect the correct time span
            B_island = calc_inpt.Ybus.imag

            pqpv = calc_inpt.pqpv
            vd = calc_inpt.ref

            # Add nodal power balance for the non slack nodes
            idx = bus_original_idx[pqpv]
            nodal_restrictions[idx] = lpAddRestrictions2(problem=problem,
                                                         lhs=lpDot(B_island[np.ix_(pqpv, pqpv)], theta_island[pqpv]),
                                                         rhs=P_island[pqpv],
                                                         name='Nodal_power_balance_pqpv_is' + str(i),
                                                         op='=')

            # Add nodal power balance for the slack nodes
            idx = bus_original_idx[vd]
            nodal_restrictions[idx] = lpAddRestrictions2(problem=problem,
                                                         lhs=lpDot(B_island[vd, :], theta_island),
                                                         rhs=P_island[vd],
                                                         name='Nodal_power_balance_vd_is' + str(i),
                                                         op='=')

            # slack angles equal to zero
            lpAddRestrictions2(problem=problem,
                               lhs=theta_island[vd],
                               rhs=np.zeros(len(vd)),
                               name='Theta_vd_zero_is' + str(i),
                               op='=')

    return nodal_restrictions


def add_branch_loading_restriction(problem: LpProblem, theta_f, theta_t, Bseries, rating, FSlack1, FSlack2):
    """
    Add the branch loading restrictions
    :param problem: LpProblem instance
    :param theta_f: voltage angles at the "from" side of the branches (m)
    :param theta_t: voltage angles at the "to" side of the branches (m)
    :param Bseries: Array of branch susceptances (m)
    :param rating: Array of branch ratings (m)
    :param FSlack1: Array of branch loading slack variables in the from-to sense
    :param FSlack2: Array of branch loading slack variables in the to-from sense
    :return: load_f and load_t arrays (LP+float)
    """

    load_f = Bseries * (theta_f - theta_t)
    load_t = Bseries * (theta_t - theta_f)

    # from-to branch power restriction
    lpAddRestrictions2(problem=problem,
                       lhs=load_f,
                       rhs=rating + FSlack1,  # rating + FSlack1
                       name='from_to_branch_rate',
                       op='<=')

    # to-from branch power restriction
    lpAddRestrictions2(problem=problem,
                       lhs=load_t,
                       rhs=rating + FSlack2,  # rating + FSlack2
                       name='to_from_branch_rate',
                       op='<=')

    return load_f, load_t


class OpfSimple(Opf):

    def __init__(self, numerical_circuit: NumericalCircuit):
        """
        DC time series linear optimal power flow
        :param numerical_circuit: NumericalCircuit instance
        """
        Opf.__init__(self, numerical_circuit=numerical_circuit)

        # build the formulation
        self.problem = None

    def solve(self, msg=False):
        """

        :param msg:
        :return:
        """
        nc = self.numerical_circuit

        # general indices
        n = nc.nbus
        m = nc.nbr
        ng = nc.n_ctrl_gen
        nb = nc.n_batt
        nl = nc.n_ld
        Sbase = nc.Sbase

        # battery
        # Capacity = nc.battery_Enom / Sbase
        # minSoC = nc.battery_min_soc
        # maxSoC = nc.battery_max_soc
        # if batteries_energy_0 is None:
        #     SoC0 = nc.battery_soc_0
        # else:
        #     SoC0 = (batteries_energy_0 / Sbase) / Capacity
        # Pb_max = nc.battery_pmax / Sbase
        # Pb_min = nc.battery_pmin / Sbase
        # Efficiency = (nc.battery_discharge_efficiency + nc.battery_charge_efficiency) / 2.0
        # cost_b = nc.battery_cost_profile[a:b, :].transpose()

        # generator
        Pg_max = nc.generator_pmax / Sbase
        # Pg_min = nc.generator_pmin / Sbase
        # P_profile = nc.generator_power_profile[a:b, :] / Sbase
        # cost_g = nc.generator_cost_profile[a:b, :]
        # enabled_for_dispatch = nc.generator_active_prof

        # load
        Pl = np.zeros(nl)
        Pg = np.zeros(ng)
        Pb = np.zeros(nb)
        E = np.zeros(nb)
        theta = np.zeros(n)

        # generator share:
        Pavail = Pg_max * nc.generator_active
        Gshare = Pavail / Pavail.sum()

        Pl = (nc.load_active * nc.load_power.real) / Sbase

        Pg = Pl.sum() * Gshare

        # Assign variables to keep
        # transpose them to be in the format of GridCal: time, device
        self.theta = theta
        self.Pg = Pg
        self.Pb = Pb
        self.Pl = Pl
        self.E = E
        self.load_shedding = np.zeros(nl)
        self.s_from = np.zeros(m)
        self.s_to = np.zeros(m)
        self.overloads = np.zeros(m)
        self.rating = nc.br_rates / Sbase
        self.nodal_restrictions = np.zeros(n)

        return True

    def get_voltage(self):
        """
        return the complex voltages (time, device)
        :return: 2D array
        """
        return np.ones_like(self.theta) * np.exp(-1j * self.theta)

    def get_overloads(self):
        """
        return the branch overloads (time, device)
        :return: 2D array
        """
        return self.overloads

    def get_loading(self):
        """
        return the branch loading (time, device)
        :return: 2D array
        """
        return self.s_from / self.rating

    def get_branch_power(self):
        """
        return the branch loading (time, device)
        :return: 2D array
        """
        return self.s_from * self.numerical_circuit.Sbase

    def get_battery_power(self):
        """
        return the battery dispatch (time, device)
        :return: 2D array
        """
        return self.Pb * self.numerical_circuit.Sbase

    def get_battery_energy(self):
        """
        return the battery energy (time, device)
        :return: 2D array
        """
        return self.E * self.numerical_circuit.Sbase

    def get_generator_power(self):
        """
        return the generator dispatch (time, device)
        :return: 2D array
        """
        return self.Pg * self.numerical_circuit.Sbase

    def get_load_shedding(self):
        """
        return the load shedding (time, device)
        :return: 2D array
        """
        return self.load_shedding * self.numerical_circuit.Sbase

    def get_load_power(self):
        """
        return the load shedding (time, device)
        :return: 2D array
        """
        return self.Pl * self.numerical_circuit.Sbase

    def get_shadow_prices(self):
        """
        Extract values fro the 2D array of LP variables
        :return: 2D numpy array
        """
        return self.nodal_restrictions


if __name__ == '__main__':

        from GridCal.Engine.IO.file_handler import FileOpen

        # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/Lynn 5 Bus pv.gridcal'
        # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/IEEE39_1W.gridcal'
        fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/grid_2_islands.xlsx'
        # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/Lynn 5 Bus pv (2 islands).gridcal'

        main_circuit = FileOpen(fname).open()

        main_circuit.buses[3].controlled_generators[0].enabled_dispatch = False

        numerical_circuit_ = main_circuit.compile()
        problem = OpfSimple(numerical_circuit=numerical_circuit_)

        print('Solving...')
        status = problem.solve()

        # print("Status:", status)

        v = problem.get_voltage()
        print('Angles\n', np.angle(v))

        l = problem.get_loading()
        print('Branch loading\n', l)

        g = problem.get_generator_power()
        print('Gen power\n', g)

        pr = problem.get_shadow_prices()
        print('Nodal prices \n', pr)

        pass