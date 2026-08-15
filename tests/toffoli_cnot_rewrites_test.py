import random
import cirq
import pytest

from benchmarking import benchmark_cirq, cirq_util
from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.optimisation.optimiser import PandoraOptimiser
from pandora.translation.translator import PandoraGateTranslator, In, Out
from pandora.util.circuit_util import remove_io_gates
from pandora.util.test_util import assert_same_up_to_qubit_permutation, count_t_gates, \
    assert_logically_equivalent_up_to_qubit_permutation

CX = PandoraGateTranslator.CXPowGate
PauliX = PandoraGateTranslator._PauliX
CCX = PandoraGateTranslator.CCXPowGate

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_rewrite_ccx_cx_share_2_controls_a(pass_count, timeout):

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

        optimiser.rewrite_ccx_cx_share_2_controls(
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
async def test_rewrite_ccx_cx_share_2_controls_b(pass_count, timeout):
    """ Test case for the rewrite rule where 2 Toffoli controls (different predecessors and successors) are shared with a CNOT gate."""
    
    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.Z.on(q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q2, q1),
            cirq.X.on(q1),
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.Z.on(q2),
            cirq.CX.on(q2, q1),
            cirq.X.on(q1),
            cirq.CCX.on(q1, q2, q3),
            cirq.X.on(q1),
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

        optimiser.rewrite_ccx_cx_share_2_controls(
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
async def test_commute_ccx_cx_commute_a(pass_count, timeout):

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

        optimiser.commute_ccx_cx_match_ctrl_tgt(
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
async def test_commuteccx_cx_commute_b(pass_count, timeout):

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q2, q3)
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
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

        optimiser.commute_ccx_cx_match_ctrl_tgt(
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
async def test_commute_ccx_cx_share_1_tgt_ctrl(pass_count, timeout):

    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.H.on(q4),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q3, q4),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.H.on(q3),
            cirq.X.on(q4)

        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.H.on(q4),
            cirq.CX.on(q3, q4),
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q1, q2, q4),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.H.on(q3),
            cirq.X.on(q4)
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

        optimiser.commute_ccx_share_target_with_cx_control(
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
async def test_commute_ccx_cx_share_1_ctrl_tgt_a(pass_count, timeout):

    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q4, q2),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.X.on(q3),
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.CX.on(q4, q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q1, q4, q3),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.X.on(q3),
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

        optimiser.commute_ccx_share_control_with_cx_target(
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
async def test_commute_ccx_cx_share_1_ctrl_tgt_b(pass_count, timeout):

    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q4, q1),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.X.on(q3),
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2),
            cirq.H.on(q3),
            cirq.CX.on(q4, q1),
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q2, q4, q3),
            cirq.Z.on(q1),
            cirq.H.on(q2),
            cirq.X.on(q3),
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

        optimiser.commute_ccx_share_control_with_cx_target(
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
async def test_commute_ccx_cx_share_2_controls_a(pass_count, timeout):

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
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q1, q3),
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

        optimiser.commute_ccx_cx_share_2_controls(
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
async def test_commute_ccx_cx_share_1_control_a(pass_count, timeout):
    
    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [   
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q1, q4),
        ]
    )

    expected_circuit = cirq.Circuit(
        [
            cirq.CX.on(q1, q4),
            cirq.CCX.on(q1, q2, q3),
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

        optimiser.commute_ccx_cx_share_1_control(
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
async def test_commute_ccx_cx_share_1_control_b(pass_count, timeout):
    
    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [   cirq.X.on(q1),
            cirq.Z.on(q2), 
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q2, q4),
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.Z.on(q2), 
            cirq.CX.on(q2, q4),
            cirq.CCX.on(q1, q2, q3),
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

        optimiser.commute_ccx_cx_share_1_control(
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
async def test_commute_ccx_cx_share_1_target_a(pass_count, timeout):
    
    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )

    initial_circuit = cirq.Circuit(
        [   
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q4, q3),
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.CX.on(q4, q3),
            cirq.CCX.on(q1, q2, q3),
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

        optimiser.commute_ccx_cx_share_1_target(
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
async def test_commute_ccx_cx_share_1_target_b(pass_count, timeout):
    """ Test case when the CNOT control depends on the Toffoli qubits."""

    q1, q2, q3, q4 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
        cirq.NamedQubit("q4"),
    )
    initial_circuit = cirq.Circuit([
        cirq.Moment(
            cirq.TOFFOLI(cirq.LineQubit(3), cirq.LineQubit(0), cirq.LineQubit(1)),
        ),
        cirq.Moment(
            cirq.CNOT(cirq.LineQubit(2), cirq.LineQubit(3)),
        ),
        cirq.Moment(
            cirq.CNOT(cirq.LineQubit(3), cirq.LineQubit(2)),
        ),
        cirq.Moment(
            cirq.CNOT(cirq.LineQubit(2), cirq.LineQubit(1)),
        ),
    ])
    expected_circuit = initial_circuit


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

        optimiser.commute_ccx_cx_share_1_target(
            dedicated_nproc=2,
        )

        await optimiser.start()

        extracted_circuit = await service.load_circuit(
            circuit_type="cirq"
        )
        extracted_circuit = remove_io_gates(extracted_circuit)
        print("Initial:")
        print(initial_circuit)
        print("Actual:")
        print(extracted_circuit)

        assert_logically_equivalent_up_to_qubit_permutation(
            expected=initial_circuit,
            actual=extracted_circuit,
        )

        assert_same_up_to_qubit_permutation(
            expected=expected_circuit,
            actual=extracted_circuit,
        )

    finally:
        await db.close()

@pytest.mark.asyncio
@pytest.mark.parametrize("pass_count", [1])
@pytest.mark.parametrize("timeout", [1])
async def test_commute_ccx_cx_share_2_mixed_a(pass_count, timeout):
    """ Test case when the CNOT control depends on the Toffoli qubits."""

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )
    initial_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.H.on(q2),
            cirq.Z.on(q3),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q3, q2),
            cirq.H.on(q1),
            cirq.Z.on(q2),
            cirq.X.on(q3)

        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.H.on(q2),
            cirq.Z.on(q3),
            cirq.CX.on(q3, q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q1, q3, q2),
            cirq.CCX.on(q1, q2, q3),
            cirq.H.on(q1),
            cirq.Z.on(q2),
            cirq.X.on(q3)
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

        optimiser.commute_ccx_cx_share_2_mixed(
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
async def test_commute_ccx_cx_share_2_mixed_b(pass_count, timeout):
    """ Test case when the CNOT control depends on the Toffoli qubits."""

    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )
    initial_circuit = cirq.Circuit(
        [   
            cirq.H.on(q2),
            cirq.X.on(q1),
            cirq.Z.on(q3),
            cirq.CCX.on(q1, q2, q3),
            cirq.CX.on(q3, q1),
            cirq.H.on(q1),
            cirq.Z.on(q2),
            cirq.X.on(q3),
        ]
    )

    expected_circuit = cirq.Circuit(
        [   
            cirq.X.on(q1),
            cirq.H.on(q2),
            cirq.Z.on(q3),
            cirq.CX.on(q3, q1),
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q2, q3, q1),
            cirq.CCX.on(q1, q2, q3),
            cirq.H.on(q1),
            cirq.Z.on(q2),
            cirq.X.on(q3)
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

        optimiser.commute_ccx_cx_share_2_mixed(
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
async def test_cancel_three_qubit_gates(pass_count, timeout):
    q1, q2, q3 = (
        cirq.NamedQubit("q1"),
        cirq.NamedQubit("q2"),
        cirq.NamedQubit("q3"),
    )

    initial_circuit = cirq.Circuit(
        [
            cirq.CCX.on(q1, q2, q3),
            cirq.CCX.on(q1, q2, q3),
        ]
    )

    expected_circuit = cirq.Circuit()

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

        optimiser.cancel_three_qubit_gates(
            gate_types=(CCX, CCX),
            gate_param=1,
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
@pytest.mark.parametrize("pass_count", [int(1e9)])
@pytest.mark.parametrize("stop_after", [5])
async def test_logical_correctness_random(pass_count, stop_after):

    for n_qubits in range(4, 6):
        for n_templates in range(5, 80, 5):
            initial_circuit = cirq_util.create_random_circuit(
                n_qubits=4,
                n_templates=n_templates,
                templates=[
                    "add_toffoli",
                    "add_generic_toffoli_cnot",
                    "add_ccx_cx_ctrl_tgt_share_ctrl_tgt",
                    "add_ccx_cx_ctrls_share_ctrl_tgt",
                    "add_ccx_cx_tgt_share_ctrl",
                    "add_ccx_cx_ctrl_share_tgt",
                    "add_ccx_cx_share_1_ctrl",
                    "add_ccx_cx_share_1_tgt",
                    "add_ccx_cx_ctrl_tgt_share_tgt_ctrl",
                    "add_two_toffolis",
                ],
                add_margins=False,
            )

            print("Initial:")
            print(repr(initial_circuit))
            
            db = PandoraDB("default_config.json")
            await db.connect()

            try:
                repo = GateRepository(db)
                service = PandoraService(db=db, repo=repo)

                await service.build_circuit(circuit=initial_circuit)

                optimiser = PandoraOptimiser(
                    db=db,
                    pass_count=pass_count,
                    timeout=stop_after,
                    logger_id=2,
                )

                optimiser.commute_ccx_cx_share_2_controls(
                    dedicated_nproc=1,
                )
                optimiser.commute_ccx_cx_match_ctrl_tgt(
                    dedicated_nproc=1,
                )
                optimiser.commute_ccx_share_target_with_cx_control(
                    dedicated_nproc=1,
                )
                optimiser.commute_ccx_share_control_with_cx_target(
                    dedicated_nproc=2,
                )
                optimiser.commute_ccx_cx_share_1_control(
                    dedicated_nproc=1,
                )
                optimiser.commute_ccx_cx_share_1_target(
                    dedicated_nproc=1,
                )
                optimiser.rewrite_ccx_cx_share_2_controls(
                    dedicated_nproc=1,
                )
                optimiser.commute_ccx_cx_share_2_mixed(
                    dedicated_nproc=1,
                )

                optimiser.cancel_three_qubit_gates(
                    gate_types=(CCX, CCX),
                    gate_param=1,
                    dedicated_nproc=1,

                )

                await optimiser.start()

                extracted_circuit = await service.load_circuit(circuit_type="cirq")
                extracted_circuit = remove_io_gates(extracted_circuit)

                assert_logically_equivalent_up_to_qubit_permutation(expected=extracted_circuit, actual=initial_circuit)
                
            finally:
                await db.close()

@pytest.mark.asyncio
@pytest.mark.parametrize("stop_after", [1])
@pytest.mark.parametrize("pass_count", [int(1e9)])
@pytest.mark.parametrize("timeout", [2])
@pytest.mark.parametrize("trials", [100])
async def test_race_condition(pass_count, timeout, stop_after, trials):

    initial_circuit = cirq_util.create_random_circuit(
        n_qubits=4,
        n_templates=100,
        templates=[
            "add_generic_toffoli_cnot",
            "add_ccx_cx_ctrl_tgt_share_ctrl_tgt",
            "add_ccx_cx_ctrls_share_ctrl_tgt",
            "add_ccx_cx_tgt_share_ctrl",
            "add_ccx_cx_ctrl_share_tgt",
            "add_ccx_cx_share_1_ctrl",
            "add_ccx_cx_share_1_tgt",
            "add_ccx_cx_ctrl_tgt_share_tgt_ctrl",
            "add_two_toffolis",
        ],
        add_margins=False,
    )
        
    for i in range(trials):
        db = PandoraDB("default_config.json")
        await db.connect()

        try:
            repo = GateRepository(db)
            service = PandoraService(db=db, repo=repo)

            await service.build_circuit(circuit=initial_circuit)

            optimiser = PandoraOptimiser(
                db=db,
                pass_count=pass_count,
                timeout=stop_after,
                logger_id=3,
            )

            optimiser.commute_ccx_cx_share_2_controls(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_cx_match_ctrl_tgt(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_share_target_with_cx_control(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_share_control_with_cx_target(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_cx_share_1_control(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_cx_share_1_target(
                dedicated_nproc=2,
            )
            optimiser.rewrite_ccx_cx_share_2_controls(
                dedicated_nproc=2,
            )
            optimiser.commute_ccx_cx_share_2_mixed(
                dedicated_nproc=2,
            )

            optimiser.cancel_three_qubit_gates(
                gate_types=(CCX, CCX),
                gate_param=1,
                dedicated_nproc=2,
            )

            op

            await optimiser.start()
            
            extracted_circuit = await service.load_circuit(circuit_type="cirq")
            extracted_circuit = remove_io_gates(extracted_circuit)

            if len(extracted_circuit.all_qubits()) != len(initial_circuit.all_qubits()):
                continue

            assert_logically_equivalent_up_to_qubit_permutation(expected=extracted_circuit, actual=initial_circuit)

        finally:
            await db.close()

# @pytest.mark.asyncio
# @pytest.mark.parametrize("pass_count", [int(1e9)])
# @pytest.mark.parametrize("stop_after", [5])
# async def test_fail_circuit_with_each_rule(pass_count, stop_after):

#     initial_circuit = cirq.Circuit([
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(3), cirq.LineQubit(2), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(2), cirq.LineQubit(0)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(2), cirq.LineQubit(0), cirq.LineQubit(3)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(3), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(2), cirq.LineQubit(1), cirq.LineQubit(0)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(3), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(1), cirq.LineQubit(3), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(0), cirq.LineQubit(3)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(2), cirq.LineQubit(0), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(3), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(0), cirq.LineQubit(3), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(2), cirq.LineQubit(3)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(0), cirq.LineQubit(3), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(1), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(3), cirq.LineQubit(2), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(2), cirq.LineQubit(0)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(3), cirq.LineQubit(0), cirq.LineQubit(2)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(0), cirq.LineQubit(1)),
#     ),
#     cirq.Moment(
#         cirq.TOFFOLI(cirq.LineQubit(2), cirq.LineQubit(1), cirq.LineQubit(0)),
#     ),
#     cirq.Moment(
#         cirq.CNOT(cirq.LineQubit(0), cirq.LineQubit(2)),
#     ),
# ])
        
#     for rule in ["commute_ccx_cx_share_2_controls", "commute_ccx_cx_match_ctrl_tgt", "commute_ccx_share_target_with_cx_control", "commute_ccx_share_control_with_cx_target", "commute_ccx_cx_share_1_control", "commute_ccx_cx_share_1_target", "rewrite_ccx_cx_share_2_controls", "commute_ccx_cx_share_2_mixed"]: 
#         test_circuit = initial_circuit.copy()
#         print(f"Testing rule: {rule}")
#         db = PandoraDB("default_config.json")
#         await db.connect()

#         try:
#             repo = GateRepository(db)
#             service = PandoraService(db=db, repo=repo)

#             await service.build_circuit(circuit=initial_circuit)

#             optimiser = PandoraOptimiser(
#                 db=db,
#                 pass_count=pass_count,
#                 timeout=stop_after,
#                 logger_id=2,
#             )

#             optimiser.__getattribute__(rule)(     
#                 dedicated_nproc=1,
#             )

#             await optimiser.start()
            
#             extracted_circuit = await service.load_circuit(circuit_type="cirq")
#             extracted_circuit = remove_io_gates(extracted_circuit)
#             print("Extracted:")
#             print(repr(extracted_circuit))

#             assert_logically_equivalent_up_to_qubit_permutation(expected=extracted_circuit, actual=initial_circuit)

#         finally:
#             await db.close()

   