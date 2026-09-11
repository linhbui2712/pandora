import asyncio

from qiskit.circuit.library.arithmetic.adders import VBERippleCarryAdder

from pandora.util.circuit_util import remove_io_gates
from pandora.translation.dag_to_circuit import pandora_to_circuit
from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.translation.translator import PandoraGateTranslator
from pandora import PandoraOptimiser
from benchmarking.benchmark_vbe_adder import get_decomposed_vbe_ripple_adder

async def main():
    timeout = 10
    db = PandoraDB("default_config.json")
    await db.connect()


    X = PandoraGateTranslator._PauliX
    CX = PandoraGateTranslator.CXPowGate
    CCX = PandoraGateTranslator.CCXPowGate
    
    try:
        for n_bits in [2]:

            adder = get_decomposed_vbe_ripple_adder(n_bits=n_bits)
            
            print(f"{n_bits}-bit VBE Adder Initial:")
            print(adder.draw(fold=-1))

            optimiser = PandoraOptimiser(
                db=db,
                pass_count=int(1e7),
                timeout=timeout,
                logger_id=n_bits,
            )

            repo = GateRepository(db)
            service = PandoraService(db=db, repo=repo)
            
            await service.build_circuit(
                circuit=adder
            )

            initial_circuit = await service.load_circuit(circuit_type="qiskit")
            initial_circuit = remove_io_gates(initial_circuit, type="qiskit")
            initial_gate_counts = initial_circuit.count_ops()

            print("Initial circuit after Pandora build:")
            print(f"CNOT count: {initial_gate_counts.get('cx', 0)}")
            print(f"NOT count: {initial_gate_counts.get('x', 0)}")
            print(f"Toffoli count: {initial_gate_counts.get('ccx', 0)}")
            print("Circuit:")
            print(initial_circuit.draw(fold=-1))

            optimiser.rewrite_ccx_cx_share_2_controls_with_snapshot(
                dedicated_nproc=1,
            )
            optimiser.cancel_two_qubit_gates_with_snapshot(
                gate_types=(CX, CX),
                gate_param=1,
                dedicated_nproc=1,
            )
                
            await optimiser.start()
            snapshot_ids = await db.pool.fetch(
                """
                select distinct snapshot_id
                from rewrite_snapshots
                order by snapshot_id
                """
            )
            for index, row in enumerate(snapshot_ids, start=1):
                snapshot_id = row["snapshot_id"]
                gates = await repo.fetch_snapshot(snapshot_id)
                circuit = pandora_to_circuit(gates, "qiskit")
                circuit = remove_io_gates(circuit, type="qiskit")

                gate_counts = circuit.count_ops()

                print()
                print(f"After rewrite application {index}:")
                print(f"CNOT count: {gate_counts.get('cx', 0)}")
                print(f"NOT count: {gate_counts.get('x', 0)}")
                print(f"Toffoli count: {gate_counts.get('ccx', 0)}")
                print(circuit.draw(fold=-1))

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())