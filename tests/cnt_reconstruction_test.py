"""Test reconstruction of circuits with CNOT, NOT, and Toffoli (CNT) gates 
using the Pandora windowed builder."""

import pytest
import cirq

from benchmarking import cirq_util
from pandora.translation.circuit_to_dag import PandoraWindowedBuilder
from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService

from pandora.translation.dag_to_circuit import pandora_to_circuit
from pandora.util.circuit_util import (
    get_adder_as_cirq_circuit,
    remove_io_gates,
    remove_measurements,
    remove_classically_controlled_ops
)
from pandora.util.test_util import assert_same_up_to_qubit_permutation

WINDOW_SIZE = 2
LABEL = 0

def test_simple_cnt_reconstruction():
    """Test reconstruction of a CNT circuit."""

    q = [cirq.NamedQubit('0'), cirq.NamedQubit('1'), cirq.NamedQubit('2')]

    simple_cnt_circuit = cirq.Circuit(
        cirq.X(q[0]),
        cirq.CX(q[0], q[1]),
        cirq.CCX(q[0], q[1], q[2]),
        cirq.CX(q[2], q[1]),
        cirq.CCX(q[2], q[1], q[0]),
    )

    builder = PandoraWindowedBuilder(window_size=WINDOW_SIZE, label=LABEL)

    gates = []
    for batch in builder.consume(simple_cnt_circuit):
        gates.extend(batch)

    gates.extend(builder.finalize())

    recon = pandora_to_circuit(pandora_gates=gates)
    recon = remove_io_gates(recon)

    cirq.testing.assert_same_circuits(simple_cnt_circuit, recon)


def test_random_cnt_reconstruction(n_circuits=100):
    """Test reconstruction of random CNT circuits."""

    templates = ['add_generic_toffoli_cnot',
                'add_ccx_cx_ctrl_tgt_share_ctrl_tgt',
                'add_ccx_cx_ctrls_share_ctrl_tgt',
                'add_ccx_cx_tgt_share_ctrl',
                'add_ccx_cx_ctrl_share_tgt',
                'add_two_nots',
                'add_two_cnots',
                'add_toffoli',
                'add_ccx_cx_ctrl_tgt_share_tgt_ctrl',
                'add_ccx_cx_share_1_ctrl',
                'add_ccx_cx_share_1_tgt',
                'add_two_toffolis'
                ]

    for i in range(n_circuits):

        print(f'Random test {i}')

        rand = cirq_util.create_random_circuit(
            n_qubits=4,
            n_templates=15,
            templates=templates
        )

        builder = PandoraWindowedBuilder(window_size=WINDOW_SIZE, label=LABEL)

        gates = []
        for batch in builder.consume(rand):
            gates.extend(batch)

        gates.extend(builder.finalize())

        recon = pandora_to_circuit(pandora_gates=gates)
        recon = remove_io_gates(recon)

        assert_same_up_to_qubit_permutation(expected=rand, actual=recon)
        print("Test passed!")

