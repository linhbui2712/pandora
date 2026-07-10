-- Helper functions for decoding and encoding the compact edge links used by the rewrite rules.
-- Each link stores the target gate id, the port number, and the gate type in a single bigint.
CREATE OR REPLACE FUNCTION get_port_from_link(link bigint)
RETURNS bigint
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT mod(div(link, 100), 10);
$$;

-- Extract the gate type encoded in a link.
CREATE OR REPLACE FUNCTION get_type_from_link(link bigint)
RETURNS bigint
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT mod(link, 100);
$$;

-- Extract the target gate id encoded in a link.
CREATE OR REPLACE FUNCTION get_id_from_link(link bigint)
RETURNS bigint
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT div(link, 1000);
$$;

-- Build a compact link from a gate id, port, and gate type.
CREATE OR REPLACE FUNCTION create_link(id bigint, port int, type smallint)
RETURNS bigint
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT id * 1000 + port * 100 + type;
$$;

--- Update the previous link of a gate, given the port number.
CREATE OR REPLACE FUNCTION update_prev_link(
    gate_id bigint,
    link_port bigint,
    new_link bigint
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    port_connect smallint := get_port_from_link(link_port);
BEGIN
    IF port_connect = 0 THEN
        UPDATE linked_circuit
        SET prev_q1 = new_link
        WHERE id = gate_id;
    ELSIF port_connect = 1 THEN
        UPDATE linked_circuit
        SET prev_q2 = new_link
        WHERE id = gate_id;
    ELSE
        UPDATE linked_circuit
        SET prev_q3 = new_link
        WHERE id = gate_id;
    END IF;
END;
$$;

-- Update the next link of a gate, given the port number.
CREATE OR REPLACE FUNCTION update_next_link(
    gate_id bigint,
    link_port bigint,
    new_link bigint
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    port_connect smallint := get_port_from_link(link_port);
BEGIN
    IF port_connect = 0 THEN
        UPDATE linked_circuit
        SET next_q1 = new_link
        WHERE id = gate_id;
    ELSIF port_connect = 1 THEN
        UPDATE linked_circuit
        SET next_q2 = new_link
        WHERE id = gate_id;
    ELSE
        UPDATE linked_circuit
        SET next_q3 = new_link
        WHERE id = gate_id;
    END IF;
END;
$$;

-- Main circuit representation used by the rewrite procedures.
-- Each row is a gate and its predecessor/successor connections are stored as encoded links.
create table IF NOT EXISTS public.linked_circuit
(
    id      bigserial primary key,
    prev_q1 bigint,
    prev_q2 bigint,
    prev_q3 bigint,
    type    smallint,
    param   real,
    global_shift real default 0,
    switch  boolean,
    next_q1 bigint,
    next_q2 bigint,
    next_q3 bigint,
--     visited boolean,
    visited int default -1 ,
    label   char,
    cl_ctrl boolean,
    meas_key smallint
) WITH (FILLFACTOR = 100);

-- Index used by the equivalence benchmark queries.
CREATE INDEX linked_circuit_type_idx on linked_circuit(type);

-- Index that helps locate gates whose two outgoing links point to the same next gate.
CREATE INDEX linked_circuit_next_ids_equal_idx on linked_circuit(type, (get_type_from_link(next_q1)))
where get_id_from_link(next_q1) = get_id_from_link(next_q2);

-- Registry of supported gate names and their integer ids.
CREATE TABLE IF NOT EXISTS gate_types (
    id smallint unique not null,
    name text unique not null
);

INSERT INTO gate_types (id, name) VALUES
(0, 'in'),
(1, 'out'),
(2, 'rx'),
(3, 'ry'),
(4, 'rz'),
(5, 'xpow'),
(6, 'ypow'),
(7, 'zpow'),
(8, 'h'),
(9, 'paulix'),
(10, 'pauliy'),
(11, 'pauliz'),
(12, 'globalphase'),
(13, 'reset'),
(14, 'meas'),
(15, 'cx'),
(16, 'cz'),
(17, 'czpow'),
(18, 'cxpow'),
(19, 'xxpow'),
(20, 'zzpow'),
(21, 'toffoli'),
(22, 'and'),
(23, 'ccx'),
(24, 'cswap'),
(25, 'globalin'),
(26, 'globalout'),
(27, 's'),
(28, 'sdag'),
(29, 't'),
(30, 'tdag'),
(31, 'swap');

-- Stores aggregate statistics collected while running optimisation procedures.
create table IF NOT EXISTS public.optimization_results
(
    id int,
    logger_id int,
    total_count int,
    t_count int,
    s_count int,
    h_count int,
    cx_count int,
    x_count int
);

-- Batched circuit table used for intermediate processing steps.
create table IF NOT EXISTS public.batched_circuit
(
    id int,
    prev_q1 int,
    prev_q2 int,
    prev_q3 int,
    type    smallint,
    param   numeric,
    global_shift real,
    switch  boolean,
    next_q1 int,
    next_q2 int,
    next_q3 int,
    visited boolean,
    label   serial,
    cl_ctrl boolean,
    meas_key smallint
);

-- Test-oriented variant of linked_circuit with an extra qubit_name column.
create table IF NOT EXISTS public.linked_circuit_test
(
    id      bigserial primary key,
    prev_q1 bigint,
    prev_q2 bigint,
    prev_q3 bigint,
    type    smallint,
    param   real,
    global_shift real,
    switch  boolean,
    next_q1 bigint,
    next_q2 bigint,
    next_q3 bigint,
    visited boolean,
    label   char,
    cl_ctrl boolean,
    meas_key smallint,
    qubit_name varchar(50)
);

-- Stores benchmark timing and count information for the benchmarking pipeline.
create table IF NOT EXISTS public.benchmark_results
(
    id      int primary key,
    pyliqtr_time float,
    pyliqtr_count int,
    decomp_time float,
    pandora_time float,
    pandora_count bigint,
    widgetisation_time float,
    widget_count int,
    extraction_time float
);

create extension IF NOT EXISTS tsm_system_rows;

-- Simple coordination table used to signal when the optimisation loop should stop.
create table if not exists public.stop_condition
(
    stop boolean default false
);

-- Tracks how many optimisation rounds were missed during execution.
create table if not exists public.max_missed_rounds
(
    missed int default 0
);

-- Records how many times each rewrite procedure has been applied.
create table if not exists public.rewrite_count
(
    proc_id int primary key,
    count int default 0
);

-- Stores the graph edges used by the widgetization and decomposition pipeline.
create table if not exists public.edge_list
(
    source bigint,
    target bigint
);

-- Temporary table for tracking CX gates that need special handling.
create table if not exists public.mem_cx
(
    id bigint primary key
);


-- Layered representation used by the LSCOM-related pipeline.
create table IF NOT EXISTS public.layered_lscom
(
    id        bigserial primary key, 
    control_q bigint,
    target_q  bigint,
    type      smallint,
    param     real,
    layer     bigint
);

