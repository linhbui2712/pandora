import random

import cirq
import pytest

from benchmarking import benchmark_cirq
from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.optimisation.optimiser import PandoraOptimiser
from pandora.translation.translator import PandoraGateTranslator
from pandora.util.circuit_util import remove_io_gates
from pandora.util.test_util import assert_same_up_to_qubit_permutation, count_t_gates, \
    assert_logically_equivalent_up_to_qubit_permutation

CX = PandoraGateTranslator.CXPowGate
PauliX = PandoraGateTranslator._PauliX
CCX = PandoraGateTranslator.Toffoli

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_ccx_cx_share_2_controls_a(pass_count, timeout):

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q1, q2),
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.CX.on(q1, q2),
            cirq.X.on(q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.X.on(q2),
        ]
    )

    db = PandoraDB("default_config.json")
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(db=db, repo=repo)

        await service.build_circuit(
            circuit=initial_circuit
        )

        optimiser = PandoraOptimiser(
            db=db,
            pass_count=pass_count,
            timeout=timeout,
            logger_id=1,
        )

        optimiser.ccx_cx_share_2_controls(
            dedicated_nproc=1,
        )

        await optimiser.start()

        extracted_circuit = await service.load_circuit(
            circuit_type="cirq"
        )
        extracted_circuit = remove_io_gates(extracted_circuit)

        # print("Initial:")
        # print(initial_circuit)
        # print("Expected:")
        # print(expected_circuit)
        # print("Actual:")
        # print(extracted_circuit)

        assert_same_up_to_qubit_permutation(
            expected=expected_circuit,
            actual=extracted_circuit,
        )

    finally:
        await db.close()

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_ccx_cx_share_2_controls_b(pass_count, timeout):

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q2, q1),
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.CX.on(q2, q1),
            cirq.X.on(q1),
            cirq.CCX.on(q1, q2, q3),
            cirq.X.on(q1),
        ]
    )

    db = PandoraDB("default_config.json")
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(db=db, repo=repo)

        await service.build_circuit(
            circuit=initial_circuit
        )

        optimiser = PandoraOptimiser(
            db=db,
            pass_count=pass_count,
            timeout=timeout,
            logger_id=1,
        )

        optimiser.ccx_cx_share_2_controls(
            dedicated_nproc=1,
        )

        await optimiser.start()

        extracted_circuit = await service.load_circuit(
            circuit_type="cirq"
        )
        extracted_circuit = remove_io_gates(extracted_circuit)

        # print("Initial:")
        # print(initial_circuit)
        # print("Expected:")
        # print(expected_circuit)
        # print("Actual:")
        # print(extracted_circuit)

        assert_same_up_to_qubit_permutation(
            expected=expected_circuit,
            actual=extracted_circuit,
        )

    finally:
        await db.close()

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_ccx_cx_commute_a(pass_count, timeout):

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q1, q3)
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.CX.on(q1, q3),
            cirq.CCX.on(q1, q2, q3)
        ]
    )

    db = PandoraDB("default_config.json")
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(db=db, repo=repo)

        await service.build_circuit(
            circuit=initial_circuit
        )

        optimiser = PandoraOptimiser(
            db=db,
            pass_count=pass_count,
            timeout=timeout,
            logger_id=1,
        )

        optimiser.ccx_cx_commute(
            dedicated_nproc=1,
        )

        await optimiser.start()

        extracted_circuit = await service.load_circuit(
            circuit_type="cirq"
        )
        extracted_circuit = remove_io_gates(extracted_circuit)

        print("Initial:")
        print(initial_circuit)
        print("Expected:")
        print(expected_circuit)
        print("Actual:")
        print(extracted_circuit)

        assert_same_up_to_qubit_permutation(
            expected=expected_circuit,
            actual=extracted_circuit,
        )

    finally:
        await db.close()

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_ccx_cx_commute_b(pass_count, timeout):

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q2, q3)
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.CX.on(q2, q3),
            cirq.CCX.on(q1, q2, q3)
        ]
    )

    db = PandoraDB("default_config.json")
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(db=db, repo=repo)

        await service.build_circuit(
            circuit=initial_circuit
        )

        optimiser = PandoraOptimiser(
            db=db,
            pass_count=pass_count,
            timeout=timeout,
            logger_id=1,
        )

        optimiser.ccx_cx_commute(
            dedicated_nproc=1,
        )

        await optimiser.start()

        extracted_circuit = await service.load_circuit(
            circuit_type="cirq"
        )
        extracted_circuit = remove_io_gates(extracted_circuit)

        print("Initial:")
        print(initial_circuit)
        print("Expected:")
        print(expected_circuit)
        print("Actual:")
        print(extracted_circuit)

        assert_same_up_to_qubit_permutation(
            expected=expected_circuit,
            actual=extracted_circuit,
        )

    finally:
        await db.close()
