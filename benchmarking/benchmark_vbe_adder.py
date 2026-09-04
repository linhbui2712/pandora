import asyncio

from qiskit import QuantumCircuit
# from qiskit.synthesis.arithmetic import adder_ripple_v95
from qiskit.circuit.library.arithmetic.adders import VBERippleCarryAdder

from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.translation.translator import PandoraGateTranslator
from pandora import PandoraOptimiser

def get_decomposed_vbe_ripple_adder(n_bits: int, kind: str = "full") -> QuantumCircuit:
    # adder = adder_ripple_v95(n_bits)
    # new_adder = QuantumCircuit(*adder.qregs)

    # for instruction in adder.data:
    #     op = instruction.operation

    #     if op.name in {"Carry", "Carry_dg", "Sum"}:
    #         # Insert the internal definition of the composite gate
    #         definition = op.definition
    #         new_adder.compose(
    #             definition,
    #             qubits=[adder.find_bit(q).index for q in instruction.qubits],
    #             inplace=True,
    #         )
    #     else:
    #         # Keep CCX and CX as they are
    #         new_adder.append(op, instruction.qubits)
    # return new_adder

    adder = VBERippleCarryAdder(num_state_qubits=n_bits, kind=kind)
    return adder.decompose().decompose()

async def main():
    # 30 seconds timeout for the optimiser
    timeout = 60
    # print(new_adder.draw())
    db = PandoraDB("default_config.json")
    await db.connect()

    X = PandoraGateTranslator._PauliX
    CX = PandoraGateTranslator.CXPowGate
    CCX = PandoraGateTranslator.CCXPowGate
    
    try:
        for n_bits in [16, 32, 64, 128, 256, 512, 1024, 2048]:
            adder = get_decomposed_vbe_ripple_adder(n_bits=n_bits)
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
            optimiser.commute_ccx_cx_match_ctrl_tgt(
                dedicated_nproc=1,
            )

            optimiser.commute_ccx_cx_share_1_control(
                dedicated_nproc=1,
            )

            optimiser.commute_ccx_cx_share_1_target(
                dedicated_nproc=1,
            )
            optimiser.cancel_three_qubit_gates(
                gate_types=(CCX, CCX),
                gate_param=1,
                dedicated_nproc=1,
            )

            optimiser.cancel_two_qubit_gates(
                gate_types=(CX, CX),
                gate_param=1,
                dedicated_nproc=1,
            )

            optimiser.cancel_single_qubit_gates(
                gate_types=(X, X),
                gate_params=(0, 0),
                dedicated_nproc=1,
            )
            
            # optimiser.commute_ccx_cx_share_2_controls(
            #     dedicated_nproc=1,
            # )
            
            optimiser.commute_ccx_share_target_with_cx_control(
                dedicated_nproc=1,
            )
            
            optimiser.commute_ccx_share_control_with_cx_target(
                dedicated_nproc=1,
            )
            
            optimiser.commute_ccx_cx_share_2_mixed(
                dedicated_nproc=1,
            )

            optimiser.rewrite_ccx_cx_share_2_controls(
                dedicated_nproc=1,
            )
            

            optimiser.log_cnt()
                
            await optimiser.start()
            await optimiser.generate_csv_cnt(logger_id=n_bits, out_path=f"benchmarking/thesis_benchmarking/vbe/vbe_full_adder_60/vbe_adder_{n_bits}.csv")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())