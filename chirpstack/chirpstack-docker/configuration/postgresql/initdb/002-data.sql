--
-- PostgreSQL database dump
--

\restrict aBYoDDSh7oRICMMoHi8r7leEhsFZZWjaQ07gndVqAcs4MszOy8ZLJB6gelUxLRz

-- Dumped from database version 14.22
-- Dumped by pg_dump version 14.22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: hstore; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS hstore WITH SCHEMA public;


--
-- Name: EXTENSION hstore; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION hstore IS 'data type for storing sets of (key, value) pairs';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: __diesel_schema_migrations; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.__diesel_schema_migrations (
    version character varying(50) NOT NULL,
    run_on timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.__diesel_schema_migrations OWNER TO chirpstack;

--
-- Name: api_key; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.api_key (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    is_admin boolean NOT NULL,
    tenant_id uuid,
    is_read_only boolean NOT NULL
);


ALTER TABLE public.api_key OWNER TO chirpstack;

--
-- Name: application; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.application (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    mqtt_tls_cert bytea,
    tags jsonb NOT NULL
);


ALTER TABLE public.application OWNER TO chirpstack;

--
-- Name: application_integration; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.application_integration (
    application_id uuid NOT NULL,
    kind character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    configuration jsonb NOT NULL
);


ALTER TABLE public.application_integration OWNER TO chirpstack;

--
-- Name: device; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device (
    dev_eui bytea NOT NULL,
    application_id uuid NOT NULL,
    device_profile_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone,
    scheduler_run_after timestamp with time zone,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    external_power_source boolean NOT NULL,
    battery_level numeric(5,2),
    margin integer,
    dr smallint,
    latitude double precision,
    longitude double precision,
    altitude real,
    dev_addr bytea,
    enabled_class character(1) NOT NULL,
    skip_fcnt_check boolean NOT NULL,
    is_disabled boolean NOT NULL,
    tags jsonb NOT NULL,
    variables jsonb NOT NULL,
    join_eui bytea NOT NULL,
    secondary_dev_addr bytea,
    device_session bytea,
    app_layer_params jsonb NOT NULL,
    f_cnt_up bigint NOT NULL
);


ALTER TABLE public.device OWNER TO chirpstack;

--
-- Name: device_keys; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_keys (
    dev_eui bytea NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    nwk_key bytea NOT NULL,
    app_key bytea NOT NULL,
    dev_nonces jsonb NOT NULL,
    join_nonce integer NOT NULL,
    gen_app_key bytea NOT NULL
);


ALTER TABLE public.device_keys OWNER TO chirpstack;

--
-- Name: device_profile; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_profile (
    id uuid NOT NULL,
    tenant_id uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    region character varying(10) NOT NULL,
    mac_version character varying(10) NOT NULL,
    reg_params_revision character varying(20) NOT NULL,
    adr_algorithm_id character varying(100) NOT NULL,
    payload_codec_runtime character varying(20) NOT NULL,
    uplink_interval integer NOT NULL,
    device_status_req_interval integer NOT NULL,
    supports_otaa boolean NOT NULL,
    supports_class_b boolean NOT NULL,
    supports_class_c boolean NOT NULL,
    tags jsonb NOT NULL,
    payload_codec_script text NOT NULL,
    flush_queue_on_activate boolean NOT NULL,
    description text NOT NULL,
    measurements jsonb NOT NULL,
    auto_detect_measurements boolean NOT NULL,
    region_config_id character varying(100),
    allow_roaming boolean NOT NULL,
    rx1_delay smallint NOT NULL,
    abp_params jsonb,
    class_b_params jsonb,
    class_c_params jsonb,
    relay_params jsonb,
    app_layer_params jsonb NOT NULL,
    device_id uuid,
    firmware_version character varying(20) NOT NULL,
    vendor_profile_id integer NOT NULL,
    supported_uplink_data_rates smallint[] NOT NULL
);


ALTER TABLE public.device_profile OWNER TO chirpstack;

--
-- Name: device_profile_device; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_profile_device (
    id uuid NOT NULL,
    vendor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE public.device_profile_device OWNER TO chirpstack;

--
-- Name: device_profile_template; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_profile_template (
    id text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    vendor character varying(100) NOT NULL,
    firmware character varying(100) NOT NULL,
    region character varying(10) NOT NULL,
    mac_version character varying(10) NOT NULL,
    reg_params_revision character varying(20) NOT NULL,
    adr_algorithm_id character varying(100) NOT NULL,
    payload_codec_runtime character varying(20) NOT NULL,
    payload_codec_script text NOT NULL,
    uplink_interval integer NOT NULL,
    device_status_req_interval integer NOT NULL,
    flush_queue_on_activate boolean NOT NULL,
    supports_otaa boolean NOT NULL,
    supports_class_b boolean NOT NULL,
    supports_class_c boolean NOT NULL,
    class_b_timeout integer NOT NULL,
    class_b_ping_slot_periodicity integer NOT NULL,
    class_b_ping_slot_dr smallint NOT NULL,
    class_b_ping_slot_freq bigint NOT NULL,
    class_c_timeout integer NOT NULL,
    abp_rx1_delay smallint NOT NULL,
    abp_rx1_dr_offset smallint NOT NULL,
    abp_rx2_dr smallint NOT NULL,
    abp_rx2_freq bigint NOT NULL,
    tags jsonb NOT NULL,
    measurements jsonb NOT NULL,
    auto_detect_measurements boolean NOT NULL
);


ALTER TABLE public.device_profile_template OWNER TO chirpstack;

--
-- Name: device_profile_vendor; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_profile_vendor (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    vendor_id integer NOT NULL,
    ouis text[] NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE public.device_profile_vendor OWNER TO chirpstack;

--
-- Name: device_queue_item; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.device_queue_item (
    id uuid NOT NULL,
    dev_eui bytea NOT NULL,
    created_at timestamp with time zone NOT NULL,
    f_port smallint NOT NULL,
    confirmed boolean NOT NULL,
    data bytea NOT NULL,
    is_pending boolean NOT NULL,
    f_cnt_down bigint,
    timeout_after timestamp with time zone,
    is_encrypted boolean NOT NULL,
    expires_at timestamp with time zone
);


ALTER TABLE public.device_queue_item OWNER TO chirpstack;

--
-- Name: fuota_deployment; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.fuota_deployment (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    name character varying(100) NOT NULL,
    application_id uuid NOT NULL,
    device_profile_id uuid NOT NULL,
    multicast_addr bytea NOT NULL,
    multicast_key bytea NOT NULL,
    multicast_group_type character(1) NOT NULL,
    multicast_class_c_scheduling_type character varying(20) NOT NULL,
    multicast_dr smallint NOT NULL,
    multicast_class_b_ping_slot_periodicity smallint NOT NULL,
    multicast_frequency bigint NOT NULL,
    multicast_timeout smallint NOT NULL,
    multicast_session_start timestamp with time zone,
    multicast_session_end timestamp with time zone,
    unicast_max_retry_count smallint NOT NULL,
    fragmentation_fragment_size smallint NOT NULL,
    fragmentation_redundancy_percentage smallint NOT NULL,
    fragmentation_session_index smallint NOT NULL,
    fragmentation_matrix smallint NOT NULL,
    fragmentation_block_ack_delay smallint NOT NULL,
    fragmentation_descriptor bytea NOT NULL,
    request_fragmentation_session_status character varying(20) NOT NULL,
    payload bytea NOT NULL,
    on_complete_set_device_tags jsonb NOT NULL
);


ALTER TABLE public.fuota_deployment OWNER TO chirpstack;

--
-- Name: fuota_deployment_device; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.fuota_deployment_device (
    fuota_deployment_id uuid NOT NULL,
    dev_eui bytea NOT NULL,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    mc_group_setup_completed_at timestamp with time zone,
    mc_session_completed_at timestamp with time zone,
    frag_session_setup_completed_at timestamp with time zone,
    frag_status_completed_at timestamp with time zone,
    error_msg text NOT NULL
);


ALTER TABLE public.fuota_deployment_device OWNER TO chirpstack;

--
-- Name: fuota_deployment_gateway; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.fuota_deployment_gateway (
    fuota_deployment_id uuid NOT NULL,
    gateway_id bytea NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.fuota_deployment_gateway OWNER TO chirpstack;

--
-- Name: fuota_deployment_job; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.fuota_deployment_job (
    fuota_deployment_id uuid NOT NULL,
    job character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    max_retry_count smallint NOT NULL,
    attempt_count smallint NOT NULL,
    scheduler_run_after timestamp with time zone NOT NULL,
    warning_msg text NOT NULL,
    error_msg text NOT NULL
);


ALTER TABLE public.fuota_deployment_job OWNER TO chirpstack;

--
-- Name: gateway; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.gateway (
    gateway_id bytea NOT NULL,
    tenant_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    altitude real NOT NULL,
    stats_interval_secs integer NOT NULL,
    tls_certificate bytea,
    tags jsonb NOT NULL,
    properties jsonb NOT NULL
);


ALTER TABLE public.gateway OWNER TO chirpstack;

--
-- Name: multicast_group; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.multicast_group (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    region character varying(10) NOT NULL,
    mc_addr bytea NOT NULL,
    mc_nwk_s_key bytea NOT NULL,
    mc_app_s_key bytea NOT NULL,
    f_cnt bigint NOT NULL,
    group_type character(1) NOT NULL,
    dr smallint NOT NULL,
    frequency bigint NOT NULL,
    class_b_ping_slot_periodicity smallint NOT NULL,
    class_c_scheduling_type character varying(20) NOT NULL
);


ALTER TABLE public.multicast_group OWNER TO chirpstack;

--
-- Name: multicast_group_device; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.multicast_group_device (
    multicast_group_id uuid NOT NULL,
    dev_eui bytea NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.multicast_group_device OWNER TO chirpstack;

--
-- Name: multicast_group_gateway; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.multicast_group_gateway (
    multicast_group_id uuid NOT NULL,
    gateway_id bytea NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.multicast_group_gateway OWNER TO chirpstack;

--
-- Name: multicast_group_queue_item; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.multicast_group_queue_item (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    scheduler_run_after timestamp with time zone NOT NULL,
    multicast_group_id uuid NOT NULL,
    gateway_id bytea NOT NULL,
    f_cnt bigint NOT NULL,
    f_port smallint NOT NULL,
    data bytea NOT NULL,
    emit_at_time_since_gps_epoch bigint,
    expires_at timestamp with time zone
);


ALTER TABLE public.multicast_group_queue_item OWNER TO chirpstack;

--
-- Name: relay_device; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.relay_device (
    relay_dev_eui bytea NOT NULL,
    dev_eui bytea NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.relay_device OWNER TO chirpstack;

--
-- Name: relay_gateway; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.relay_gateway (
    tenant_id uuid NOT NULL,
    relay_id bytea NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    stats_interval_secs integer NOT NULL,
    region_config_id character varying(100) NOT NULL
);


ALTER TABLE public.relay_gateway OWNER TO chirpstack;

--
-- Name: tenant; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.tenant (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    can_have_gateways boolean NOT NULL,
    max_device_count integer NOT NULL,
    max_gateway_count integer NOT NULL,
    private_gateways_up boolean NOT NULL,
    private_gateways_down boolean NOT NULL,
    tags jsonb NOT NULL
);


ALTER TABLE public.tenant OWNER TO chirpstack;

--
-- Name: tenant_user; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public.tenant_user (
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_admin boolean NOT NULL,
    is_device_admin boolean NOT NULL,
    is_gateway_admin boolean NOT NULL
);


ALTER TABLE public.tenant_user OWNER TO chirpstack;

--
-- Name: user; Type: TABLE; Schema: public; Owner: chirpstack
--

CREATE TABLE public."user" (
    id uuid NOT NULL,
    external_id text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_admin boolean NOT NULL,
    is_active boolean NOT NULL,
    email text NOT NULL,
    email_verified boolean NOT NULL,
    password_hash character varying(200) NOT NULL,
    note text NOT NULL
);


ALTER TABLE public."user" OWNER TO chirpstack;

--
-- Data for Name: __diesel_schema_migrations; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.__diesel_schema_migrations (version, run_on) FROM stdin;
00000000000000	2026-05-10 15:02:40.215546
20220426153628	2026-05-10 15:02:40.499526
20220428071028	2026-05-10 15:02:40.50434
20220511084032	2026-05-10 15:02:40.507603
20220614130020	2026-05-10 15:02:40.561948
20221102090533	2026-05-10 15:02:40.566677
20230103201442	2026-05-10 15:02:40.57462
20230112130153	2026-05-10 15:02:40.579117
20230206135050	2026-05-10 15:02:40.582215
20230213103316	2026-05-10 15:02:40.604219
20230216091535	2026-05-10 15:02:40.608808
20230925105457	2026-05-10 15:02:40.666412
20231019142614	2026-05-10 15:02:40.669732
20231122120700	2026-05-10 15:02:40.702932
20240207083424	2026-05-10 15:02:40.707478
20240326134652	2026-05-10 15:02:40.732166
20240430103242	2026-05-10 15:02:40.800758
20240613122655	2026-05-10 15:02:40.810469
20240916123034	2026-05-10 15:02:40.852362
20241112135745	2026-05-10 15:02:40.856887
20250113152218	2026-05-10 15:02:40.884998
20250121093745	2026-05-10 15:02:40.904328
20250605100843	2026-05-10 15:02:40.966297
20250804085822	2026-05-10 15:02:40.972139
20251001085546	2026-05-10 15:02:40.975874
202511111404590000	2026-05-10 15:02:40.979036
202512101058490000	2026-05-10 15:02:41.024545
202602181001240000	2026-05-10 15:02:41.027722
\.


--
-- Data for Name: api_key; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.api_key (id, created_at, name, is_admin, tenant_id, is_read_only) FROM stdin;
\.


--
-- Data for Name: application; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.application (id, tenant_id, created_at, updated_at, name, description, mqtt_tls_cert, tags) FROM stdin;
e8e29522-e292-4845-af49-13ff5d4315e4	74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:17:44.571031+00	2026-05-10 15:17:44.571031+00	Zone 1	Zone 1 nodes	\N	{}
dd205732-b347-472a-8e94-7a9adbbb5008	74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:18:01.319277+00	2026-05-10 15:18:01.319277+00	Zone 2	Zone 2 nodes	\N	{}
\.


--
-- Data for Name: application_integration; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.application_integration (application_id, kind, created_at, updated_at, configuration) FROM stdin;
\.


--
-- Data for Name: device; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device (dev_eui, application_id, device_profile_id, created_at, updated_at, last_seen_at, scheduler_run_after, name, description, external_power_source, battery_level, margin, dr, latitude, longitude, altitude, dev_addr, enabled_class, skip_fcnt_check, is_disabled, tags, variables, join_eui, secondary_dev_addr, device_session, app_layer_params, f_cnt_up) FROM stdin;
\\x0000000000000001	e8e29522-e292-4845-af49-13ff5d4315e4	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:26:12.148036+00	2026-05-10 15:26:12.148036+00	\N	\N	node 1	---	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000002	e8e29522-e292-4845-af49-13ff5d4315e4	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:27:38.899458+00	2026-05-10 15:27:38.899458+00	\N	\N	node 2	---	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000003	e8e29522-e292-4845-af49-13ff5d4315e4	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:28:15.532336+00	2026-05-10 15:28:15.532336+00	\N	\N	node 3	---	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000004	e8e29522-e292-4845-af49-13ff5d4315e4	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:28:43.474055+00	2026-05-10 15:28:43.474055+00	\N	\N	node 4	----	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000005	e8e29522-e292-4845-af49-13ff5d4315e4	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:29:13.395356+00	2026-05-10 15:29:13.395356+00	\N	\N	node 5	-----	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000006	dd205732-b347-472a-8e94-7a9adbbb5008	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:29:43.932038+00	2026-05-10 15:29:43.932038+00	\N	\N	node 6	------	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000007	dd205732-b347-472a-8e94-7a9adbbb5008	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:30:07.211621+00	2026-05-10 15:30:07.211621+00	\N	\N	node 7	-------	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000008	dd205732-b347-472a-8e94-7a9adbbb5008	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:31:10.597948+00	2026-05-10 15:31:10.597948+00	\N	\N	node 8	--------	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000009	dd205732-b347-472a-8e94-7a9adbbb5008	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:32:19.907085+00	2026-05-10 15:32:19.907085+00	\N	\N	node 9	---------	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\\x0000000000000010	dd205732-b347-472a-8e94-7a9adbbb5008	ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	2026-05-10 15:34:19.036325+00	2026-05-10 15:34:19.036325+00	\N	\N	node 10	----------	f	\N	\N	\N	\N	\N	\N	\N	A	f	f	{}	{}	\\x0000000000000000	\N	\N	{"ts004_session_cnt": [0, 0, 0, 0]}	0
\.


--
-- Data for Name: device_keys; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_keys (dev_eui, created_at, updated_at, nwk_key, app_key, dev_nonces, join_nonce, gen_app_key) FROM stdin;
\\x0000000000000001	2026-05-10 15:26:31.009515+00	2026-05-10 15:26:31.009515+00	\\x00000000000000000000000000000001	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000002	2026-05-10 15:27:44.266614+00	2026-05-10 15:27:44.266614+00	\\x00000000000000000000000000000002	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000003	2026-05-10 15:28:20.973728+00	2026-05-10 15:28:20.973728+00	\\x00000000000000000000000000000003	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000004	2026-05-10 15:28:48.206707+00	2026-05-10 15:28:48.206707+00	\\x00000000000000000000000000000004	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000005	2026-05-10 15:29:20.165193+00	2026-05-10 15:29:20.165193+00	\\x00000000000000000000000000000005	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000006	2026-05-10 15:29:48.406864+00	2026-05-10 15:29:48.406864+00	\\x00000000000000000000000000000006	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000007	2026-05-10 15:30:15.126812+00	2026-05-10 15:30:15.126812+00	\\x00000000000000000000000000000007	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000008	2026-05-10 15:31:15.783112+00	2026-05-10 15:31:15.783112+00	\\x00000000000000000000000000000008	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000009	2026-05-10 15:32:28.673434+00	2026-05-10 15:32:28.673434+00	\\x00000000000000000000000000000009	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\\x0000000000000010	2026-05-10 15:34:23.915126+00	2026-05-10 15:34:23.915126+00	\\x00000000000000000000000000000010	\\x00000000000000000000000000000000	{}	0	\\x00000000000000000000000000000000
\.


--
-- Data for Name: device_profile; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_profile (id, tenant_id, created_at, updated_at, name, region, mac_version, reg_params_revision, adr_algorithm_id, payload_codec_runtime, uplink_interval, device_status_req_interval, supports_otaa, supports_class_b, supports_class_c, tags, payload_codec_script, flush_queue_on_activate, description, measurements, auto_detect_measurements, region_config_id, allow_roaming, rx1_delay, abp_params, class_b_params, class_c_params, relay_params, app_layer_params, device_id, firmware_version, vendor_profile_id, supported_uplink_data_rates) FROM stdin;
ce14e7e2-fddd-4ef3-bd9e-d5fde6770601	74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:14:02.386084+00	2026-05-10 15:14:02.386084+00	Device_prof_1	EU868	1.0.3	A	default	NONE	3600	1	t	f	f	{}	/**\n * Decode uplink function\n * \n * @param {object} input\n * @param {number[]} input.bytes Byte array containing the uplink payload, e.g. [255, 230, 255, 0]\n * @param {number} input.fPort Uplink fPort.\n * @param {Record<string, string>} input.variables Object containing the configured device variables.\n * \n * @returns {{data: object, errors: string[], warnings: string[]}}\n * An object containing:\n * - data: Object representing the decoded payload.\n * - errors: An array of errors (optional).\n * - warnings: An array of warnings (optional).\n */\nfunction decodeUplink(input) {\n  return {\n    data: {\n      temp: 22.5,\n    }\n  };\n}\n\n/**\n * Encode downlink function.\n * \n * @param {object} input\n * @param {object} input.data Object representing the payload that must be encoded.\n * @param {Record<string, string>} input.variables Object containing the configured device variables.\n * \n * @returns {{bytes: number[], fPort: number, errors: string[], warnings: string[]}}\n * An object containing:\n * - bytes: Byte array containing the downlink payload.\n * - fPort: The downlink LoRaWAN fPort.\n * - errors: An array of errors (optional).\n * - warnings: An array of warnings (optional).\n */\nfunction encodeDownlink(input) {\n  return {\n    fPort: 10,\n    bytes: [225, 230, 255, 0],\n  };\n}\n	t	---	{}	t	\N	f	0	\N	\N	\N	\N	{"ts003_f_port": 202, "ts004_f_port": 201, "ts005_f_port": 200, "ts003_version": null, "ts004_version": null, "ts005_version": null}	\N		0	{}
\.


--
-- Data for Name: device_profile_device; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_profile_device (id, vendor_id, created_at, updated_at, name, description, metadata) FROM stdin;
\.


--
-- Data for Name: device_profile_template; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_profile_template (id, created_at, updated_at, name, description, vendor, firmware, region, mac_version, reg_params_revision, adr_algorithm_id, payload_codec_runtime, payload_codec_script, uplink_interval, device_status_req_interval, flush_queue_on_activate, supports_otaa, supports_class_b, supports_class_c, class_b_timeout, class_b_ping_slot_periodicity, class_b_ping_slot_dr, class_b_ping_slot_freq, class_c_timeout, abp_rx1_delay, abp_rx1_dr_offset, abp_rx2_dr, abp_rx2_freq, tags, measurements, auto_detect_measurements) FROM stdin;
\.


--
-- Data for Name: device_profile_vendor; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_profile_vendor (id, created_at, updated_at, name, vendor_id, ouis, metadata) FROM stdin;
\.


--
-- Data for Name: device_queue_item; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.device_queue_item (id, dev_eui, created_at, f_port, confirmed, data, is_pending, f_cnt_down, timeout_after, is_encrypted, expires_at) FROM stdin;
\.


--
-- Data for Name: fuota_deployment; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.fuota_deployment (id, created_at, updated_at, started_at, completed_at, name, application_id, device_profile_id, multicast_addr, multicast_key, multicast_group_type, multicast_class_c_scheduling_type, multicast_dr, multicast_class_b_ping_slot_periodicity, multicast_frequency, multicast_timeout, multicast_session_start, multicast_session_end, unicast_max_retry_count, fragmentation_fragment_size, fragmentation_redundancy_percentage, fragmentation_session_index, fragmentation_matrix, fragmentation_block_ack_delay, fragmentation_descriptor, request_fragmentation_session_status, payload, on_complete_set_device_tags) FROM stdin;
\.


--
-- Data for Name: fuota_deployment_device; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.fuota_deployment_device (fuota_deployment_id, dev_eui, created_at, completed_at, mc_group_setup_completed_at, mc_session_completed_at, frag_session_setup_completed_at, frag_status_completed_at, error_msg) FROM stdin;
\.


--
-- Data for Name: fuota_deployment_gateway; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.fuota_deployment_gateway (fuota_deployment_id, gateway_id, created_at) FROM stdin;
\.


--
-- Data for Name: fuota_deployment_job; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.fuota_deployment_job (fuota_deployment_id, job, created_at, completed_at, max_retry_count, attempt_count, scheduler_run_after, warning_msg, error_msg) FROM stdin;
\.


--
-- Data for Name: gateway; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.gateway (gateway_id, tenant_id, created_at, updated_at, last_seen_at, name, description, latitude, longitude, altitude, stats_interval_secs, tls_certificate, tags, properties) FROM stdin;
\\xaa00000000000001	74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:10:58.181042+00	2026-05-10 15:10:58.181042+00	\N	Zone_1	node 1 - 5	29.952554831950987	31.096115142882354	0	30	\N	{}	{}
\\xaa00000000000002	74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:11:23.068439+00	2026-05-10 15:11:23.068439+00	\N	Zone_2	node 6-10	29.952163804155532	31.09627297493297	0	30	\N	{}	{}
\.


--
-- Data for Name: multicast_group; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.multicast_group (id, application_id, created_at, updated_at, name, region, mc_addr, mc_nwk_s_key, mc_app_s_key, f_cnt, group_type, dr, frequency, class_b_ping_slot_periodicity, class_c_scheduling_type) FROM stdin;
\.


--
-- Data for Name: multicast_group_device; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.multicast_group_device (multicast_group_id, dev_eui, created_at) FROM stdin;
\.


--
-- Data for Name: multicast_group_gateway; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.multicast_group_gateway (multicast_group_id, gateway_id, created_at) FROM stdin;
\.


--
-- Data for Name: multicast_group_queue_item; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.multicast_group_queue_item (id, created_at, scheduler_run_after, multicast_group_id, gateway_id, f_cnt, f_port, data, emit_at_time_since_gps_epoch, expires_at) FROM stdin;
\.


--
-- Data for Name: relay_device; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.relay_device (relay_dev_eui, dev_eui, created_at) FROM stdin;
\.


--
-- Data for Name: relay_gateway; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.relay_gateway (tenant_id, relay_id, created_at, updated_at, last_seen_at, name, description, stats_interval_secs, region_config_id) FROM stdin;
\.


--
-- Data for Name: tenant; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.tenant (id, created_at, updated_at, name, description, can_have_gateways, max_device_count, max_gateway_count, private_gateways_up, private_gateways_down, tags) FROM stdin;
74d1d70b-388e-4fa5-a4aa-b4fc3a3ce98a	2026-05-10 15:02:40.215546+00	2026-05-10 15:02:40.215546+00	ChirpStack		t	0	0	f	f	{}
\.


--
-- Data for Name: tenant_user; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public.tenant_user (tenant_id, user_id, created_at, updated_at, is_admin, is_device_admin, is_gateway_admin) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: chirpstack
--

COPY public."user" (id, external_id, created_at, updated_at, is_admin, is_active, email, email_verified, password_hash, note) FROM stdin;
a2978b21-94c3-4d9a-8e28-c3f831582968	\N	2026-05-10 15:02:40.215546+00	2026-05-10 15:02:40.215546+00	t	t	admin	f	$pbkdf2-sha512$i=1,l=64$l8zGKtxRESq3PA2kFhHRWA$H3lGMxOt55wjwoc+myeOoABofJY9oDpldJa7fhqdjbh700V6FLPML75UmBOt9J5VFNjAL1AvqCozA1HJM0QVGA	
\.


--
-- Name: __diesel_schema_migrations __diesel_schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.__diesel_schema_migrations
    ADD CONSTRAINT __diesel_schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: api_key api_key_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.api_key
    ADD CONSTRAINT api_key_pkey PRIMARY KEY (id);


--
-- Name: application_integration application_integration_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.application_integration
    ADD CONSTRAINT application_integration_pkey PRIMARY KEY (application_id, kind);


--
-- Name: application application_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.application
    ADD CONSTRAINT application_pkey PRIMARY KEY (id);


--
-- Name: device_keys device_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_keys
    ADD CONSTRAINT device_keys_pkey PRIMARY KEY (dev_eui);


--
-- Name: device device_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_pkey PRIMARY KEY (dev_eui);


--
-- Name: device_profile_device device_profile_device_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile_device
    ADD CONSTRAINT device_profile_device_pkey PRIMARY KEY (id);


--
-- Name: device_profile device_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile
    ADD CONSTRAINT device_profile_pkey PRIMARY KEY (id);


--
-- Name: device_profile_template device_profile_template_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile_template
    ADD CONSTRAINT device_profile_template_pkey PRIMARY KEY (id);


--
-- Name: device_profile_vendor device_profile_vendor_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile_vendor
    ADD CONSTRAINT device_profile_vendor_pkey PRIMARY KEY (id);


--
-- Name: device_queue_item device_queue_item_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_queue_item
    ADD CONSTRAINT device_queue_item_pkey PRIMARY KEY (id);


--
-- Name: fuota_deployment_device fuota_deployment_device_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_device
    ADD CONSTRAINT fuota_deployment_device_pkey PRIMARY KEY (fuota_deployment_id, dev_eui);


--
-- Name: fuota_deployment_gateway fuota_deployment_gateway_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_gateway
    ADD CONSTRAINT fuota_deployment_gateway_pkey PRIMARY KEY (fuota_deployment_id, gateway_id);


--
-- Name: fuota_deployment_job fuota_deployment_job_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_job
    ADD CONSTRAINT fuota_deployment_job_pkey PRIMARY KEY (fuota_deployment_id, job);


--
-- Name: fuota_deployment fuota_deployment_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment
    ADD CONSTRAINT fuota_deployment_pkey PRIMARY KEY (id);


--
-- Name: gateway gateway_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.gateway
    ADD CONSTRAINT gateway_pkey PRIMARY KEY (gateway_id);


--
-- Name: multicast_group_device multicast_group_device_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_device
    ADD CONSTRAINT multicast_group_device_pkey PRIMARY KEY (multicast_group_id, dev_eui);


--
-- Name: multicast_group_gateway multicast_group_gateway_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_gateway
    ADD CONSTRAINT multicast_group_gateway_pkey PRIMARY KEY (multicast_group_id, gateway_id);


--
-- Name: multicast_group multicast_group_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group
    ADD CONSTRAINT multicast_group_pkey PRIMARY KEY (id);


--
-- Name: multicast_group_queue_item multicast_group_queue_item_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_queue_item
    ADD CONSTRAINT multicast_group_queue_item_pkey PRIMARY KEY (id);


--
-- Name: relay_device relay_device_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.relay_device
    ADD CONSTRAINT relay_device_pkey PRIMARY KEY (relay_dev_eui, dev_eui);


--
-- Name: relay_gateway relay_gateway_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.relay_gateway
    ADD CONSTRAINT relay_gateway_pkey PRIMARY KEY (tenant_id, relay_id);


--
-- Name: tenant tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT tenant_pkey PRIMARY KEY (id);


--
-- Name: tenant_user tenant_user_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_pkey PRIMARY KEY (tenant_id, user_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: idx_api_key_tenant_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_api_key_tenant_id ON public.api_key USING btree (tenant_id);


--
-- Name: idx_application_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_application_name_trgm ON public.application USING gin (name public.gin_trgm_ops);


--
-- Name: idx_application_tags; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_application_tags ON public.application USING gin (tags);


--
-- Name: idx_application_tenant_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_application_tenant_id ON public.application USING btree (tenant_id);


--
-- Name: idx_device_application_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_application_id ON public.device USING btree (application_id);


--
-- Name: idx_device_dev_addr; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_dev_addr ON public.device USING btree (dev_addr);


--
-- Name: idx_device_dev_addr_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_dev_addr_trgm ON public.device USING gin (encode(dev_addr, 'hex'::text) public.gin_trgm_ops);


--
-- Name: idx_device_dev_eui_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_dev_eui_trgm ON public.device USING gin (encode(dev_eui, 'hex'::text) public.gin_trgm_ops);


--
-- Name: idx_device_device_profile_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_device_profile_id ON public.device USING btree (device_profile_id);


--
-- Name: idx_device_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_name_trgm ON public.device USING gin (name public.gin_trgm_ops);


--
-- Name: idx_device_profile_device_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_device_id ON public.device_profile USING btree (device_id);


--
-- Name: idx_device_profile_device_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_device_name_trgm ON public.device_profile_device USING gin (name public.gin_trgm_ops);


--
-- Name: idx_device_profile_device_vendor_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_device_vendor_id ON public.device_profile_device USING btree (vendor_id);


--
-- Name: idx_device_profile_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_name_trgm ON public.device_profile USING gin (name public.gin_trgm_ops);


--
-- Name: idx_device_profile_tags; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_tags ON public.device_profile USING gin (tags);


--
-- Name: idx_device_profile_tenant_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_tenant_id ON public.device_profile USING btree (tenant_id);


--
-- Name: idx_device_profile_vendor_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_vendor_name_trgm ON public.device_profile_vendor USING gin (name public.gin_trgm_ops);


--
-- Name: idx_device_profile_vendor_ouis; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_vendor_ouis ON public.device_profile_vendor USING btree (ouis);


--
-- Name: idx_device_profile_vendor_vendor_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_profile_vendor_vendor_id ON public.device_profile_vendor USING btree (vendor_id);


--
-- Name: idx_device_queue_item_created_at; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_queue_item_created_at ON public.device_queue_item USING btree (created_at);


--
-- Name: idx_device_queue_item_dev_eui; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_queue_item_dev_eui ON public.device_queue_item USING btree (dev_eui);


--
-- Name: idx_device_queue_item_timeout_after; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_queue_item_timeout_after ON public.device_queue_item USING btree (timeout_after);


--
-- Name: idx_device_secondary_dev_addr; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_secondary_dev_addr ON public.device USING btree (secondary_dev_addr);


--
-- Name: idx_device_tags; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_device_tags ON public.device USING gin (tags);


--
-- Name: idx_fuota_deployment_job_completed_at; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_fuota_deployment_job_completed_at ON public.fuota_deployment_job USING btree (completed_at);


--
-- Name: idx_fuota_deployment_job_scheduler_run_after; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_fuota_deployment_job_scheduler_run_after ON public.fuota_deployment_job USING btree (scheduler_run_after);


--
-- Name: idx_gateway_id_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_gateway_id_trgm ON public.gateway USING gin (encode(gateway_id, 'hex'::text) public.gin_trgm_ops);


--
-- Name: idx_gateway_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_gateway_name_trgm ON public.gateway USING gin (name public.gin_trgm_ops);


--
-- Name: idx_gateway_tags; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_gateway_tags ON public.gateway USING gin (tags);


--
-- Name: idx_gateway_tenant_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_gateway_tenant_id ON public.gateway USING btree (tenant_id);


--
-- Name: idx_multicast_group_application_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_multicast_group_application_id ON public.multicast_group USING btree (application_id);


--
-- Name: idx_multicast_group_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_multicast_group_name_trgm ON public.multicast_group USING gin (name public.gin_trgm_ops);


--
-- Name: idx_multicast_group_queue_item_multicast_group_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_multicast_group_queue_item_multicast_group_id ON public.multicast_group_queue_item USING btree (multicast_group_id);


--
-- Name: idx_multicast_group_queue_item_scheduler_run_after; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_multicast_group_queue_item_scheduler_run_after ON public.multicast_group_queue_item USING btree (scheduler_run_after);


--
-- Name: idx_tenant_name_trgm; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_tenant_name_trgm ON public.tenant USING gin (name public.gin_trgm_ops);


--
-- Name: idx_tenant_tags; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_tenant_tags ON public.tenant USING gin (tags);


--
-- Name: idx_tenant_user_user_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE INDEX idx_tenant_user_user_id ON public.tenant_user USING btree (user_id);


--
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE UNIQUE INDEX idx_user_email ON public."user" USING btree (email);


--
-- Name: idx_user_external_id; Type: INDEX; Schema: public; Owner: chirpstack
--

CREATE UNIQUE INDEX idx_user_external_id ON public."user" USING btree (external_id);


--
-- Name: api_key api_key_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.api_key
    ADD CONSTRAINT api_key_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: application_integration application_integration_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.application_integration
    ADD CONSTRAINT application_integration_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.application(id) ON DELETE CASCADE;


--
-- Name: application application_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.application
    ADD CONSTRAINT application_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: device device_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.application(id) ON DELETE CASCADE;


--
-- Name: device device_device_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_device_profile_id_fkey FOREIGN KEY (device_profile_id) REFERENCES public.device_profile(id) ON DELETE CASCADE;


--
-- Name: device_keys device_keys_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_keys
    ADD CONSTRAINT device_keys_dev_eui_fkey FOREIGN KEY (dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: device_profile device_profile_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile
    ADD CONSTRAINT device_profile_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.device_profile_device(id) ON DELETE CASCADE;


--
-- Name: device_profile_device device_profile_device_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile_device
    ADD CONSTRAINT device_profile_device_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.device_profile_vendor(id) ON DELETE CASCADE;


--
-- Name: device_profile device_profile_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_profile
    ADD CONSTRAINT device_profile_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: device_queue_item device_queue_item_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.device_queue_item
    ADD CONSTRAINT device_queue_item_dev_eui_fkey FOREIGN KEY (dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: fuota_deployment fuota_deployment_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment
    ADD CONSTRAINT fuota_deployment_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.application(id) ON DELETE CASCADE;


--
-- Name: fuota_deployment_device fuota_deployment_device_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_device
    ADD CONSTRAINT fuota_deployment_device_dev_eui_fkey FOREIGN KEY (dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: fuota_deployment_device fuota_deployment_device_fuota_deployment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_device
    ADD CONSTRAINT fuota_deployment_device_fuota_deployment_id_fkey FOREIGN KEY (fuota_deployment_id) REFERENCES public.fuota_deployment(id) ON DELETE CASCADE;


--
-- Name: fuota_deployment fuota_deployment_device_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment
    ADD CONSTRAINT fuota_deployment_device_profile_id_fkey FOREIGN KEY (device_profile_id) REFERENCES public.device_profile(id) ON DELETE CASCADE;


--
-- Name: fuota_deployment_gateway fuota_deployment_gateway_fuota_deployment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_gateway
    ADD CONSTRAINT fuota_deployment_gateway_fuota_deployment_id_fkey FOREIGN KEY (fuota_deployment_id) REFERENCES public.fuota_deployment(id) ON DELETE CASCADE;


--
-- Name: fuota_deployment_gateway fuota_deployment_gateway_gateway_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_gateway
    ADD CONSTRAINT fuota_deployment_gateway_gateway_id_fkey FOREIGN KEY (gateway_id) REFERENCES public.gateway(gateway_id) ON DELETE CASCADE;


--
-- Name: fuota_deployment_job fuota_deployment_job_fuota_deployment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.fuota_deployment_job
    ADD CONSTRAINT fuota_deployment_job_fuota_deployment_id_fkey FOREIGN KEY (fuota_deployment_id) REFERENCES public.fuota_deployment(id) ON DELETE CASCADE;


--
-- Name: gateway gateway_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.gateway
    ADD CONSTRAINT gateway_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: multicast_group multicast_group_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group
    ADD CONSTRAINT multicast_group_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.application(id) ON DELETE CASCADE;


--
-- Name: multicast_group_device multicast_group_device_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_device
    ADD CONSTRAINT multicast_group_device_dev_eui_fkey FOREIGN KEY (dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: multicast_group_device multicast_group_device_multicast_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_device
    ADD CONSTRAINT multicast_group_device_multicast_group_id_fkey FOREIGN KEY (multicast_group_id) REFERENCES public.multicast_group(id) ON DELETE CASCADE;


--
-- Name: multicast_group_gateway multicast_group_gateway_gateway_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_gateway
    ADD CONSTRAINT multicast_group_gateway_gateway_id_fkey FOREIGN KEY (gateway_id) REFERENCES public.gateway(gateway_id) ON DELETE CASCADE;


--
-- Name: multicast_group_gateway multicast_group_gateway_multicast_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_gateway
    ADD CONSTRAINT multicast_group_gateway_multicast_group_id_fkey FOREIGN KEY (multicast_group_id) REFERENCES public.multicast_group(id) ON DELETE CASCADE;


--
-- Name: multicast_group_queue_item multicast_group_queue_item_gateway_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_queue_item
    ADD CONSTRAINT multicast_group_queue_item_gateway_id_fkey FOREIGN KEY (gateway_id) REFERENCES public.gateway(gateway_id) ON DELETE CASCADE;


--
-- Name: multicast_group_queue_item multicast_group_queue_item_multicast_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.multicast_group_queue_item
    ADD CONSTRAINT multicast_group_queue_item_multicast_group_id_fkey FOREIGN KEY (multicast_group_id) REFERENCES public.multicast_group(id) ON DELETE CASCADE;


--
-- Name: relay_device relay_device_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.relay_device
    ADD CONSTRAINT relay_device_dev_eui_fkey FOREIGN KEY (dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: relay_device relay_device_relay_dev_eui_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.relay_device
    ADD CONSTRAINT relay_device_relay_dev_eui_fkey FOREIGN KEY (relay_dev_eui) REFERENCES public.device(dev_eui) ON DELETE CASCADE;


--
-- Name: relay_gateway relay_gateway_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.relay_gateway
    ADD CONSTRAINT relay_gateway_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: tenant_user tenant_user_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: tenant_user tenant_user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chirpstack
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict aBYoDDSh7oRICMMoHi8r7leEhsFZZWjaQ07gndVqAcs4MszOy8ZLJB6gelUxLRz

