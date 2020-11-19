from GridCal.Engine.basic_structures import Logger
from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.basic_structures import BranchImpedanceMode
from GridCal.Engine.basic_structures import BusMode
from GridCal.Engine.Devices.enumerations import ConverterControlType, TransformerControlType
from GridCal.Engine.Core.DataStructures import *


def get_bus_data(circuit: MultiCircuit, time_series=False, ntime=1):
    """

    :param circuit:
    :param time_series:
    :return:
    """
    bus_data = BusData(nbus=len(circuit.buses), ntime=ntime)

    for i, bus in enumerate(circuit.buses):

        # bus parameters
        bus_data.bus_names[i] = bus.name

        if time_series:
            bus_data.bus_active[i, :] = bus.active_prof
        else:
            bus_data.bus_active[i] = bus.active

        bus_data.bus_types[i] = bus.determine_bus_type().value

    return bus_data


def get_load_data(circuit: MultiCircuit, bus_dict, opf_results=None, time_series=False, opf=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param opf_results:
    :param time_series:
    :param opf:
    :param ntime:
    :return:
    """

    devices = circuit.get_loads()

    if opf:
        data = LoadOpfData(nload=len(devices), nbus=len(circuit.buses), ntime=ntime)
    else:
        data = LoadData(nload=len(devices), nbus=len(circuit.buses), ntime=ntime)

    for k, elm in enumerate(devices):

        i = bus_dict[elm.bus]

        data.load_names[k] = elm.name
        data.load_active[k] = elm.active

        if time_series:
            data.load_s[k, :] = elm.P_prof + 1j * elm.Q_prof

            if opf:
                data.load_cost[k, :] = elm.Cost_prof

            if opf_results is not None:
                data.load_s[k, :] -= opf_results.load_shedding[:, k]

        else:
            data.load_s[k] = complex(elm.P, elm.Q)

            if opf:
                data.load_cost[k] = elm.Cost

            if opf_results is not None:
                data.load_s[k] -= opf_results.load_shedding[k]

        data.C_bus_load[i, k] = 1

    return data


def get_static_generator_data(circuit: MultiCircuit, bus_dict, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param time_series:
    :return:
    """
    devices = circuit.get_static_generators()

    data = StaticGeneratorData(nstagen=len(devices), nbus=len(circuit.buses), ntime=ntime)

    for k, elm in enumerate(devices):

        i = bus_dict[elm.bus]

        data.static_generator_names[k] = elm.name

        if time_series:
            data.static_generator_active[k, :] = elm.active_prof
            data.static_generator_s[k, :] = elm.P_prof + 1j * elm.Q_prof
        else:
            data.static_generator_active[k] = elm.active
            data.static_generator_s[k] = complex(elm.P, elm.Q)

        data.C_bus_static_generator[i, k] = 1

    return data


def get_shunt_data(circuit: MultiCircuit, bus_dict, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param time_series:
    :return:
    """
    devices = circuit.get_shunts()

    data = ShuntData(nshunt=len(devices), nbus=len(circuit.buses), ntime=ntime)

    for k, elm in enumerate(devices):

        i = bus_dict[elm.bus]

        data.shunt_names[k] = elm.name

        if time_series:
            data.shunt_active[k, :] = elm.active_prof
            data.shunt_admittance[k, :] = elm.G_prof + 1j * elm.B_prof
        else:
            data.shunt_active[k] = elm.active
            data.shunt_admittance[k] = complex(elm.G, elm.B)

        data.C_bus_shunt[i, k] = 1

    return data


def get_generator_data(circuit: MultiCircuit, bus_dict, Vbus, logger: Logger,
                       opf_results=None, time_series=False, opf=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param Vbus:
    :param logger:
    :param opf_results:
    :param time_series:
    :return:
    """
    devices = circuit.get_generators()

    if opf:
        data = GeneratorOpfData(ngen=len(devices), nbus=len(circuit.buses), ntime=ntime)
    else:
        data = GeneratorData(ngen=len(devices), nbus=len(circuit.buses), ntime=ntime)

    for k, elm in enumerate(devices):

        i = bus_dict[elm.bus]

        data.generator_names[k] = elm.name
        data.generator_qmin[k] = elm.Qmin
        data.generator_qmax[k] = elm.Qmax
        data.generator_controllable[k] = elm.is_controlled
        data.generator_installed_p[k] = elm.Snom

        if time_series:
            data.generator_p[k] = elm.P_prof
            data.generator_active[k] = elm.active_prof
            data.generator_pf[k] = elm.Pf_prof
            data.generator_v[k] = elm.Vset_prof

            if opf:
                data.generator_dispatchable[k] = elm.enabled_dispatch
                data.generator_pmax[k] = elm.Pmax
                data.generator_pmin[k] = elm.Pmin
                data.generator_cost[k] = elm.Cost_prof
                data.generator_cost[k] = elm.Cost_prof

            if opf_results is not None:
                data.generator_p[k, :] = opf_results.generator_power[:, k] - opf_results.generator_shedding[:, k]

        else:
            data.generator_p[k] = elm.P
            data.generator_active[k] = elm.active
            data.generator_pf[k] = elm.Pf
            data.generator_v[k] = elm.Vset

            if opf:
                data.generator_dispatchable[k] = elm.enabled_dispatch
                data.generator_pmax[k] = elm.Pmax
                data.generator_pmin[k] = elm.Pmin
                data.generator_cost[k] = elm.Cost

            if opf_results is not None:
                data.generator_p[k] = opf_results.generator_power[k] - opf_results.generator_shedding[k]

        data.C_bus_gen[i, k] = 1

        if Vbus[i, 0].real == 1.0:
            Vbus[i, :] = complex(elm.Vset, 0)
        elif elm.Vset != Vbus[i, 0]:
            logger.append('Different set points at ' + elm.bus.name + ': ' + str(elm.Vset) + ' !=' + str(Vbus[i, 0]))

    return data


def get_battery_data(circuit: MultiCircuit, bus_dict, Vbus, logger: Logger,
                     opf_results=None, time_series=False, opf=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param Vbus:
    :param logger:
    :param opf_results:
    :param time_series:
    :param opf:
    :param ntime:
    :return:
    """
    devices = circuit.get_batteries()

    if opf:
        data = BatteryOpfData(nbatt=len(devices), nbus=len(circuit.buses), ntime=ntime)
    else:
        data = BatteryData(nbatt=len(devices), nbus=len(circuit.buses), ntime=ntime)

    for k, elm in enumerate(devices):

        i = bus_dict[elm.bus]

        data.battery_names[k] = elm.name
        data.battery_qmin[k] = elm.Qmin
        data.battery_qmax[k] = elm.Qmax

        data.battery_controllable[k] = elm.is_controlled
        data.battery_installed_p[k] = elm.Snom

        if time_series:
            data.battery_p[k, :] = elm.P_prof
            data.battery_active[k, :] = elm.active_prof
            data.battery_pf[k, :] = elm.Pf_prof
            data.battery_v[k, :] = elm.Vset_prof

            if opf:
                data.battery_dispatchable[k] = elm.enabled_dispatch
                data.battery_pmax[k] = elm.Pmax
                data.battery_pmin[k] = elm.Pmin
                data.battery_enom[k] = elm.Enom
                data.battery_min_soc[k] = elm.max_soc
                data.battery_max_soc[k] = elm.max_soc
                data.battery_soc_0[k] = elm.soc_0
                data.battery_discharge_efficiency[k] = elm.discharge_efficiency
                data.battery_charge_efficiency[k] = elm.charge_efficiency
                data.battery_cost[k] = elm.Cost_prof

            if opf_results is not None:
                data.battery_p[k, :] = opf_results.battery_power[:, k]

        else:
            data.battery_p[k] = elm.P
            data.battery_active[k] = elm.active
            data.battery_pf[k] = elm.Pf
            data.battery_v[k] = elm.Vset

            if opf:
                data.battery_dispatchable[k] = elm.enabled_dispatch
                data.battery_pmax[k] = elm.Pmax
                data.battery_pmin[k] = elm.Pmin
                data.battery_enom[k] = elm.Enom
                data.battery_min_soc[k] = elm.max_soc
                data.battery_max_soc[k] = elm.max_soc
                data.battery_soc_0[k] = elm.soc_0
                data.battery_discharge_efficiency[k] = elm.discharge_efficiency
                data.battery_charge_efficiency[k] = elm.charge_efficiency
                data.battery_cost[k] = elm.Cost

            if opf_results is not None:
                data.battery_p[k] = opf_results.battery_power[k]

        data.C_bus_batt[i, k] = 1

        if Vbus[i, 0].real == 1.0:
            Vbus[i, :] = complex(elm.Vset, 0)
        elif elm.Vset != Vbus[i, 0]:
            logger.append('Different set points at ' + elm.bus.name + ': ' + str(elm.Vset) + ' !=' + str(Vbus[i, 0]))

    return data


def get_line_data(circuit: MultiCircuit, bus_dict,
                  apply_temperature, branch_tolerance_mode: BranchImpedanceMode, time_series=False, ntime=1):

    """

    :param circuit:
    :param bus_dict:
    :param apply_temperature:
    :param branch_tolerance_mode:
    :return:
    """

    nc = LinesData(nline=len(circuit.lines), nbus=len(circuit.buses))

    # Compile the lines
    for i, elm in enumerate(circuit.lines):
        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        nc.line_names[i] = elm.name

        if apply_temperature:
            nc.line_R[i] = elm.R_corrected
        else:
            nc.line_R[i] = elm.R

        if branch_tolerance_mode == BranchImpedanceMode.Lower:
            nc.line_R[i] *= (1 - elm.tolerance / 100.0)
        elif branch_tolerance_mode == BranchImpedanceMode.Upper:
            nc.line_R[i] *= (1 + elm.tolerance / 100.0)

        nc.line_X[i] = elm.X
        nc.line_B[i] = elm.B
        nc.C_line_bus[i, f] = 1
        nc.C_line_bus[i, t] = 1

    return nc


def get_transformer_data(circuit: MultiCircuit, bus_dict, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :return:
    """
    data = TransformerData(ntr=len(circuit.transformers2w), nbus=len(circuit.buses))

    # 2-winding transformers
    for i, elm in enumerate(circuit.transformers2w):

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        # impedance
        data.tr_names[i] = elm.name
        data.tr_R[i] = elm.R
        data.tr_X[i] = elm.X
        data.tr_G[i] = elm.G
        data.tr_B[i] = elm.B

        data.C_tr_bus[i, f] = 1
        data.C_tr_bus[i, t] = 1

        # tap changer
        data.tr_tap_mod[i] = elm.tap_module
        data.tr_tap_ang[i] = elm.angle
        data.tr_is_bus_to_regulated[i] = elm.bus_to_regulated
        data.tr_tap_position[i] = elm.tap_changer.tap
        data.tr_min_tap[i] = elm.tap_changer.min_tap
        data.tr_max_tap[i] = elm.tap_changer.max_tap
        data.tr_tap_inc_reg_up[i] = elm.tap_changer.inc_reg_up
        data.tr_tap_inc_reg_down[i] = elm.tap_changer.inc_reg_down
        data.tr_vset[i] = elm.vset
        data.tr_control_mode[i] = elm.control_mode

        data.tr_bus_to_regulated_idx[i] = t if elm.bus_to_regulated else f

        # virtual taps for transformers where the connection voltage is off
        data.tr_tap_f[i], data.tr_tap_t[i] = elm.get_virtual_taps()

    return data


def get_vsc_data(circuit: MultiCircuit, bus_dict, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :return:
    """
    nc = VscData(nvsc=len(circuit.vsc_converters), nbus=len(circuit.buses), ntime=ntime)

    # VSC
    for i, elm in enumerate(circuit.vsc_converters):

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        # vsc values
        nc.vsc_names[i] = elm.name
        nc.vsc_R1[i] = elm.R1
        nc.vsc_X1[i] = elm.X1
        nc.vsc_G0[i] = elm.G0
        nc.vsc_Beq[i] = elm.Beq
        nc.vsc_m[i] = elm.m
        nc.vsc_theta[i] = elm.theta
        # nc.vsc_Inom[i] = (elm.rate / nc.Sbase) / np.abs(nc.Vbus[f])
        nc.vsc_Pset[i] = elm.Pset
        nc.vsc_Qset[i] = elm.Qset
        nc.vsc_Vac_set[i] = elm.Vac_set
        nc.vsc_Vdc_set[i] = elm.Vdc_set
        nc.vsc_control_mode[i] = elm.control_mode

        nc.C_vsc_bus[i, f] = 1
        nc.C_vsc_bus[i, t] = 1

    return nc


def get_dc_line_data(circuit: MultiCircuit, bus_dict,
                     apply_temperature, branch_tolerance_mode: BranchImpedanceMode, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param apply_temperature:
    :param branch_tolerance_mode:
    :return:
    """
    nc = DcLinesData(ndcline=len(circuit.dc_lines), nbus=len(circuit.buses), ntime=ntime)

    # DC-lines
    for i, elm in enumerate(circuit.dc_lines):

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        # dc line values
        nc.dc_line_names[i] = elm.name

        if apply_temperature:
            nc.dc_line_R[i] = elm.R_corrected
        else:
            nc.dc_line_R[i] = elm.R

        if branch_tolerance_mode == BranchImpedanceMode.Lower:
            nc.dc_line_R[i] *= (1 - elm.tolerance / 100.0)
        elif branch_tolerance_mode == BranchImpedanceMode.Upper:
            nc.dc_line_R[i] *= (1 + elm.tolerance / 100.0)

        nc.dc_line_impedance_tolerance[i] = elm.tolerance
        nc.C_dc_line_bus[i, f] = 1
        nc.C_dc_line_bus[i, t] = 1
        nc.dc_F[i] = f
        nc.dc_T[i] = t

        # Thermal correction
        nc.dc_line_temp_base[i] = elm.temp_base
        nc.dc_line_temp_oper[i] = elm.temp_oper
        nc.dc_line_alpha[i] = elm.alpha

    return nc


def get_branch_data(circuit: MultiCircuit, bus_dict, apply_temperature,
                    branch_tolerance_mode: BranchImpedanceMode, time_series=False, opf=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param apply_temperature:
    :param branch_tolerance_mode:
    :param time_series:
    :param opf:
    :param ntime:
    :return:
    """
    nline = len(circuit.lines)
    ntr = len(circuit.transformers2w)
    nvsc = len(circuit.vsc_converters)
    ndcline = len(circuit.dc_lines)
    nbr = nline + ntr + nvsc + ndcline

    if opf:
        data = BranchOpfData(nbr=nbr, nbus=len(circuit.buses), ntime=ntime)
    else:
        data = BranchData(nbr=nbr, nbus=len(circuit.buses), ntime=ntime)

    # Compile the lines
    for i, elm in enumerate(circuit.lines):
        # generic stuff
        data.branch_names[i] = elm.name

        if time_series:
            data.branch_active[i, :] = elm.active_prof
            data.branch_rates[i, :] = elm.rate_prof

            if opf:
                data.branch_cost[i, :] = elm.Cost_prof

        else:
            data.branch_active[i] = elm.active
            data.branch_rates[i] = elm.rate


            if opf:
                data.branch_cost[i] = elm.Cost

        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]
        data.C_branch_bus_f[i, f] = 1
        data.C_branch_bus_t[i, t] = 1
        data.F[i] = f
        data.T[i] = t

        if apply_temperature:
            data.R[i] = elm.R_corrected
        else:
            data.R[i] = elm.R

        if branch_tolerance_mode == BranchImpedanceMode.Lower:
            data.R[i] *= (1 - elm.tolerance / 100.0)
        elif branch_tolerance_mode == BranchImpedanceMode.Upper:
            data.R[i] *= (1 + elm.tolerance / 100.0)

        data.X[i] = elm.X
        data.B[i] = elm.B

    # 2-winding transformers
    for i, elm in enumerate(circuit.transformers2w):
        ii = i + nline

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        data.branch_names[ii] = elm.name

        if time_series:
            data.branch_active[ii, :] = elm.active_prof
            data.branch_rates[ii, :] = elm.rate_prof

            if opf:
                data.branch_cost[ii, :] = elm.Cost_prof
        else:
            data.branch_active[ii] = elm.active
            data.branch_rates[ii] = elm.rate

            if opf:
                data.branch_cost[ii, :] = elm.Cost

        data.C_branch_bus_f[ii, f] = 1
        data.C_branch_bus_t[ii, t] = 1
        data.F[ii] = f
        data.T[ii] = t

        data.R[ii] = elm.R
        data.X[ii] = elm.X
        data.G[ii] = elm.G
        data.B[ii] = elm.B
        data.m[ii] = elm.tap_module
        data.theta[ii] = elm.angle
        data.control_mode[ii] = elm.control_mode
        data.tap_f[ii], data.tap_t[ii] = elm.get_virtual_taps()

        if elm.control_mode == TransformerControlType.v_to:
            data.Vbus[t] = elm.vset

        elif elm.control_mode == TransformerControlType.power_v_to:  # 2a:Vdc
            data.Vbus[t] = elm.vset

    # VSC
    for i, elm in enumerate(circuit.vsc_converters):
        ii = i + nline + ntr

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        data.branch_names[ii] = elm.name

        if time_series:
            data.branch_active[ii, :] = elm.active_prof
            data.branch_rates[ii, :] = elm.rate_prof
            if opf:
                data.branch_cost[ii, :] = elm.Cost_prof
        else:
            data.branch_active[ii] = elm.active
            data.branch_rates[ii] = elm.rate
            if opf:
                data.branch_cost[ii] = elm.Cost

        data.C_branch_bus_f[ii, f] = 1
        data.C_branch_bus_t[ii, t] = 1
        data.F[ii] = f
        data.T[ii] = t

        data.R[ii] = elm.R1
        data.X[ii] = elm.X1
        data.G0[ii] = elm.G0
        data.Beq[ii] = elm.Beq
        data.m[ii] = elm.m
        data.k[ii] = 1.0  # 0.8660254037844386  # sqrt(3)/2
        data.theta[ii] = elm.theta
        data.Pset[ii] = elm.Pset
        data.Qset[ii] = elm.Qset
        data.Kdp[ii] = elm.kdp
        data.vf_set[ii] = elm.Vac_set
        data.vt_set[ii] = elm.Vdc_set
        data.control_mode[ii] = elm.control_mode

        if elm.control_mode == ConverterControlType.type_1_vac:  # 1d:Vac
            data.Vbus[t] = elm.Vac_set
        elif elm.control_mode == ConverterControlType.type_2_vdc:  # 2a:Vdc
            data.Vbus[f] = elm.Vdc_set

    # DC-lines
    for i, elm in enumerate(circuit.dc_lines):
        ii = i + nline + ntr + nvsc

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        data.branch_names[ii] = elm.name

        if time_series:
            data.branch_active[ii, :] = elm.active_prof
            data.branch_rates[ii, :] = elm.rate_prof
            if opf:
                data.branch_cost[ii, :] = elm.Cost_prof
        else:
            data.branch_active[ii] = elm.active
            data.branch_rates[ii] = elm.rate
            if opf:
                data.branch_cost[ii] = elm.Cost

        data.C_branch_bus_f[ii, f] = 1
        data.C_branch_bus_t[ii, t] = 1
        data.F[ii] = f
        data.T[ii] = t

        if apply_temperature:
            data.R[i] = elm.R_corrected
        else:
            data.R[i] = elm.R

        if branch_tolerance_mode == BranchImpedanceMode.Lower:
            data.R[i] *= (1 - elm.tolerance / 100.0)
        elif branch_tolerance_mode == BranchImpedanceMode.Upper:
            data.R[i] *= (1 + elm.tolerance / 100.0)

    return data


def get_hvdc_data(circuit: MultiCircuit, bus_dict, bus_types, time_series=False, ntime=1):
    """

    :param circuit:
    :param bus_dict:
    :param bus_types:
    :return:
    """
    data = HvdcData(nhvdc=len(circuit.hvdc_lines), nbus=len(circuit.buses), ntime=ntime)

    # HVDC
    for i, elm in enumerate(circuit.hvdc_lines):

        # generic stuff
        f = bus_dict[elm.bus_from]
        t = bus_dict[elm.bus_to]

        # hvdc values
        data.hvdc_names[i] = elm.name

        if time_series:
            data.hvdc_active[i, :] = elm.active_prof
            data.hvdc_rate[i, :] = elm.rate_prof
            data.hvdc_Pf[i, :], data.hvdc_Pt[i, :] = elm.get_from_and_to_power()
            data.hvdc_Vset_f[i, :] = elm.Vset_f_prof
            data.hvdc_Vset_t[i, :] = elm.Vset_t_prof
        else:
            data.hvdc_active[i] = elm.active
            data.hvdc_rate[i] = elm.rate
            data.hvdc_Pf[i], data.hvdc_Pt[i] = elm.get_from_and_to_power()
            data.hvdc_Vset_f[i] = elm.Vset_f
            data.hvdc_Vset_t[i] = elm.Vset_t

        data.hvdc_loss_factor[i] = elm.loss_factor
        data.hvdc_Qmin_f[i] = elm.Qmin_f
        data.hvdc_Qmax_f[i] = elm.Qmax_f
        data.hvdc_Qmin_t[i] = elm.Qmin_t
        data.hvdc_Qmax_t[i] = elm.Qmax_t

        # hack the bus types to believe they are PV
        if elm.active:
            bus_types[f] = BusMode.PV.value
            bus_types[t] = BusMode.PV.value

        # the the bus-hvdc line connectivity
        data.C_hvdc_bus_f[i, f] = 1
        data.C_hvdc_bus_t[i, t] = 1

    return data