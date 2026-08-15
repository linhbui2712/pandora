import asyncio

from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.translation.translator import PandoraGateTranslator
from pandora import PandoraOptimiser

from benchmarking.benchmark_adders import (
    get_adder,
)
from pandora.util.circuit_util import remove_io_gates


TIMEOUT = 60
PASS_COUNT = int(1e7)


async def run_phase_1(n_bits: int):
    """
    Phase 1:
    Build the original Toffoli+CNOT circuit and apply the
    Toffoli/CNOT commutation rewrite rules.
    """
    X = PandoraGateTranslator._PauliX
    CX = PandoraGateTranslator.CXPowGate
    CCX = PandoraGateTranslator.CCXPowGate

    db = PandoraDB("default_config.json")
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(db=db, repo=repo)

        adder_circuit = get_adder(n_bits=n_bits)

        await service.build_circuit(
            circuit=adder_circuit
        )

        optimiser = PandoraOptimiser(
            db=db,
            pass_count=PASS_COUNT,
            timeout=TIMEOUT,
            logger_id=n_bits,
        )

        # ---------------------------------------------------------
        # Phase 1: Toffoli/CNOT commutation
        # ---------------------------------------------------------

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

        #
        # optimiser.commute_ccx_cx_share_2_controls(
        #     dedicated_nproc=1,
        # )
        #
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
        

        # Extract Phase-1 result.
        optimiser.log_cnt()
        await optimiser.start()
        await optimiser.generate_csv_cnt(
                    logger_id=n_bits,
                    out_path=(
                        "benchmarking/thesis_benchmarking/quipper/"
                        "quipper_adder_x_60/"
                        f"quipper_adder_{n_bits}.csv"
                    ),
                )

        

    finally:
        await db.close()


async def main():

    for n_bits in [16, 32, 64, 128, 256, 512, 1024, 2048]:

        print("\n")
        print("=" * 70)
        print(f"STARTING BENCHMARK: {n_bits} bits")
        print("=" * 70)

        # =========================================================
        # PHASE 1
        # =========================================================

        await run_phase_1(
            n_bits=n_bits
        )

  

if __name__ == "__main__":
    asyncio.run(main())