-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: reject_source_asset_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reject_source_asset_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'source_asset rows are immutable';
END;
$$;


--
-- Name: reject_video_transcript_fact_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reject_video_transcript_fact_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'video transcript fact rows are immutable';
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acquisition_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acquisition_job (
    id text NOT NULL,
    source_id text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    provider text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claimed_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    finished_at timestamp with time zone,
    artifact_id text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    claim_token text,
    video_preflight_id text,
    request_input jsonb DEFAULT '{}'::jsonb NOT NULL,
    input_fingerprint text,
    CONSTRAINT acquisition_job_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT acquisition_job_claim_token_shape CHECK ((((status = 'running'::text) AND (claim_token IS NOT NULL)) OR ((status <> 'running'::text) AND (claim_token IS NULL)))),
    CONSTRAINT acquisition_job_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text]))),
    CONSTRAINT acquisition_job_terminal_shape CHECK ((((status = 'succeeded'::text) AND (artifact_id IS NOT NULL) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (artifact_id IS NULL) AND (failure_code IS NOT NULL)) OR ((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (artifact_id IS NULL) AND (failure_code IS NULL))))
);


--
-- Name: artifact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.artifact (
    id text NOT NULL,
    snapshot_id text NOT NULL,
    kind text NOT NULL,
    tool text NOT NULL,
    tool_version text,
    body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: block; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.block (
    id text NOT NULL,
    artifact_id text NOT NULL,
    blocker_version text NOT NULL,
    seq integer NOT NULL,
    kind text NOT NULL,
    start_char integer NOT NULL,
    end_char integer NOT NULL,
    body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    image_state text,
    CONSTRAINT block_image_state_check CHECK ((((image_state IS NULL) OR ((kind = 'image'::text) AND (image_state = ANY (ARRAY['enriched'::text, 'unresolved'::text])))) AND ((blocker_version <> '3'::text) OR (kind <> 'image'::text) OR (image_state IS NOT NULL)))),
    CONSTRAINT block_kind_check CHECK ((kind = ANY (ARRAY['paragraph'::text, 'heading'::text, 'code_block'::text, 'list_item'::text, 'image'::text, 'image_summary'::text, 'table'::text, 'blockquote'::text])))
);


--
-- Name: curation_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.curation_event (
    id text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    subject jsonb DEFAULT '{}'::jsonb NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: institution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.institution (
    id text NOT NULL,
    name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT institution_id_check CHECK ((id ~ '^[a-z][a-z0-9-]{1,63}$'::text))
);


--
-- Name: lesson_build; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lesson_build (
    id text NOT NULL,
    request_seq bigint NOT NULL,
    version_id text NOT NULL,
    lesson_id text NOT NULL,
    request_key text NOT NULL,
    requested_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lesson_build_actor_shape CHECK (((btrim(requested_by) <> ''::text) AND (length(requested_by) <= 200))),
    CONSTRAINT lesson_build_id_not_blank CHECK ((btrim(id) <> ''::text)),
    CONSTRAINT lesson_build_request_key_shape CHECK (((btrim(request_key) <> ''::text) AND (length(request_key) <= 200)))
);


--
-- Name: lesson_build_request_seq_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.lesson_build ALTER COLUMN request_seq ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lesson_build_request_seq_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lesson_build_work; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lesson_build_work (
    id text NOT NULL,
    build_id text NOT NULL,
    seq integer NOT NULL,
    source_id text NOT NULL,
    snapshot_id text NOT NULL,
    artifact_id text NOT NULL,
    content_hash text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    stage text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claim_count integer DEFAULT 0 NOT NULL,
    claimed_at timestamp with time zone,
    claim_token text,
    lease_expires_at timestamp with time zone,
    last_launched_stage text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lesson_build_work_claim_count_check CHECK ((claim_count >= 0)),
    CONSTRAINT lesson_build_work_claim_shape CHECK ((((claim_token IS NULL) AND (claimed_at IS NULL) AND (lease_expires_at IS NULL)) OR ((claim_token IS NOT NULL) AND (btrim(claim_token) <> ''::text) AND (claimed_at IS NOT NULL) AND (lease_expires_at > claimed_at)))),
    CONSTRAINT lesson_build_work_content_hash_not_blank CHECK ((btrim(content_hash) <> ''::text)),
    CONSTRAINT lesson_build_work_diagnostics_object CHECK ((jsonb_typeof(diagnostics) = 'object'::text)),
    CONSTRAINT lesson_build_work_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL) AND (btrim(failure_code) <> ''::text)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT lesson_build_work_id_not_blank CHECK ((btrim(id) <> ''::text)),
    CONSTRAINT lesson_build_work_last_launch_not_blank CHECK (((last_launched_stage IS NULL) OR (btrim(last_launched_stage) <> ''::text))),
    CONSTRAINT lesson_build_work_seq_check CHECK ((seq >= 1)),
    CONSTRAINT lesson_build_work_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text])))
);


--
-- Name: passage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage (
    id text NOT NULL,
    artifact_id text NOT NULL,
    blocker_version text NOT NULL,
    first_seq integer NOT NULL,
    last_seq integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT passage_range_ordered CHECK ((first_seq <= last_seq))
);


--
-- Name: passage_cleanup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_cleanup (
    id text NOT NULL,
    cuts_run_id text NOT NULL,
    model text NOT NULL,
    triage_prompt_ref text NOT NULL,
    refine_prompt_ref text NOT NULL,
    status text NOT NULL,
    run_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT passage_cleanup_run_ids_check CHECK ((jsonb_typeof(run_ids) = 'array'::text)),
    CONSTRAINT passage_cleanup_status_check CHECK ((status = ANY (ARRAY['running'::text, 'done'::text, 'failed'::text]))),
    CONSTRAINT passage_cleanup_status_shape CHECK ((((status = 'running'::text) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['done'::text, 'failed'::text])) AND (finished_at IS NOT NULL))))
);


--
-- Name: passage_cleanup_artifact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_cleanup_artifact (
    cleanup_id text NOT NULL,
    source_artifact_id text NOT NULL,
    canonical_artifact_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT passage_cleanup_artifact_check CHECK ((source_artifact_id <> canonical_artifact_id))
);


--
-- Name: passage_cleanup_result; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_cleanup_result (
    cleanup_id text NOT NULL,
    passage_id text NOT NULL,
    passage_revision_id text,
    decision_run_item_id text,
    verdict text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    policy_reason text,
    CONSTRAINT passage_cleanup_result_check CHECK (((decision_run_item_id IS NOT NULL) OR (verdict = 'unknown'::text))),
    CONSTRAINT passage_cleanup_result_policy_reason_check CHECK (((policy_reason IS NULL) OR (policy_reason = ANY (ARRAY['primary_enriched_image_preserved'::text, 'unresolved_image_preserved'::text])))),
    CONSTRAINT passage_cleanup_result_verdict_check CHECK ((verdict = ANY (ARRAY['keep'::text, 'drop'::text, 'unknown'::text])))
);


--
-- Name: passage_origin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_origin (
    passage_id text NOT NULL,
    run_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: passage_revision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_revision (
    id text NOT NULL,
    passage_id text NOT NULL,
    parent_revision_id text,
    refine_run_item_id text NOT NULL,
    iteration integer NOT NULL,
    body text NOT NULL,
    content_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT passage_revision_check CHECK (((parent_revision_id IS NULL) OR (parent_revision_id <> id))),
    CONSTRAINT passage_revision_content_hash_check CHECK ((content_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT passage_revision_iteration_check CHECK ((iteration >= 1))
);


--
-- Name: passage_revision_drop; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_revision_drop (
    revision_id text NOT NULL,
    block_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pdf_document_parse_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_document_parse_call (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    pdf_asset_id text NOT NULL,
    parser_ref text NOT NULL,
    input_sha256 text NOT NULL,
    options jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    provider_attempts integer DEFAULT 0 NOT NULL,
    result jsonb DEFAULT '{}'::jsonb NOT NULL,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pdf_document_parse_call_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT pdf_document_parse_call_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT pdf_document_parse_call_input_sha256_check CHECK ((input_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT pdf_document_parse_call_provider_attempts_check CHECK ((provider_attempts >= 0)),
    CONSTRAINT pdf_document_parse_call_state_shape CHECK ((((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])) AND (finished_at IS NOT NULL)))),
    CONSTRAINT pdf_document_parse_call_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text])))
);


--
-- Name: pdf_figure_localization_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_figure_localization_call (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    pdf_asset_id text NOT NULL,
    batch_ordinal integer NOT NULL,
    page_ids jsonb NOT NULL,
    prompt_ref text NOT NULL,
    input_manifest_hash text NOT NULL,
    status text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    requested_model text,
    response_model text,
    provider text,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    result jsonb DEFAULT '{}'::jsonb NOT NULL,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pdf_figure_localization_call_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT pdf_figure_localization_call_batch_ordinal_check CHECK ((batch_ordinal > 0)),
    CONSTRAINT pdf_figure_localization_call_duration_ms_check CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT pdf_figure_localization_call_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT pdf_figure_localization_call_input_manifest_hash_check CHECK ((input_manifest_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT pdf_figure_localization_call_page_ids_check CHECK ((jsonb_typeof(page_ids) = 'array'::text)),
    CONSTRAINT pdf_figure_localization_call_state_shape CHECK ((((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])) AND (finished_at IS NOT NULL)))),
    CONSTRAINT pdf_figure_localization_call_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text])))
);


--
-- Name: pdf_figure_region_outcome; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_figure_region_outcome (
    id text NOT NULL,
    localization_call_id text NOT NULL,
    region_ordinal integer NOT NULL,
    page_id text NOT NULL,
    model_bbox jsonb NOT NULL,
    final_bbox jsonb NOT NULL,
    description text NOT NULL,
    visible_text text DEFAULT ''::text NOT NULL,
    anchor_id text DEFAULT ''::text NOT NULL,
    status text NOT NULL,
    source_asset_id text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pdf_figure_region_asset_shape CHECK ((((status = ANY (ARRAY['placed'::text, 'unanchored'::text])) AND (source_asset_id IS NOT NULL)) OR ((status = ANY (ARRAY['duplicate'::text, 'failed'::text])) AND (source_asset_id IS NULL)))),
    CONSTRAINT pdf_figure_region_outcome_final_bbox_check CHECK ((jsonb_typeof(final_bbox) = 'array'::text)),
    CONSTRAINT pdf_figure_region_outcome_model_bbox_check CHECK ((jsonb_typeof(model_bbox) = 'array'::text)),
    CONSTRAINT pdf_figure_region_outcome_region_ordinal_check CHECK ((region_ordinal > 0)),
    CONSTRAINT pdf_figure_region_outcome_status_check CHECK ((status = ANY (ARRAY['placed'::text, 'unanchored'::text, 'duplicate'::text, 'failed'::text])))
);


--
-- Name: pdf_page_analysis_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_page_analysis_call (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    pdf_asset_id text NOT NULL,
    batch_ordinal integer NOT NULL,
    page_ids jsonb NOT NULL,
    prompt_ref text NOT NULL,
    prompt_sha text NOT NULL,
    requested_model text NOT NULL,
    input_manifest_hash text NOT NULL,
    status text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    response_model text,
    provider text,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pdf_page_analysis_call_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT pdf_page_analysis_call_batch_ordinal_check CHECK ((batch_ordinal > 0)),
    CONSTRAINT pdf_page_analysis_call_duration_ms_check CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT pdf_page_analysis_call_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT pdf_page_analysis_call_input_manifest_hash_check CHECK ((input_manifest_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT pdf_page_analysis_call_page_ids_check CHECK ((jsonb_typeof(page_ids) = 'array'::text)),
    CONSTRAINT pdf_page_analysis_call_prompt_sha_check CHECK ((prompt_sha ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT pdf_page_analysis_call_state_shape CHECK ((((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])) AND (finished_at IS NOT NULL)))),
    CONSTRAINT pdf_page_analysis_call_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text])))
);


--
-- Name: pipeline_lease; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_lease (
    scope_key text NOT NULL,
    stage text NOT NULL,
    token text NOT NULL,
    owner_id text NOT NULL,
    acquired_at timestamp with time zone NOT NULL,
    heartbeat_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT pipeline_lease_expiration_after_heartbeat CHECK ((expires_at > heartbeat_at)),
    CONSTRAINT pipeline_lease_owner_not_blank CHECK ((btrim(owner_id) <> ''::text)),
    CONSTRAINT pipeline_lease_scope_key_not_blank CHECK ((btrim(scope_key) <> ''::text)),
    CONSTRAINT pipeline_lease_stage_not_blank CHECK ((btrim(stage) <> ''::text)),
    CONSTRAINT pipeline_lease_token_not_blank CHECK ((btrim(token) <> ''::text))
);


--
-- Name: run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.run (
    id text NOT NULL,
    stage text NOT NULL,
    model text NOT NULL,
    prompt_ref text NOT NULL,
    prompt_sha text NOT NULL,
    params jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT run_status_check CHECK ((status = ANY (ARRAY['running'::text, 'publishing'::text, 'done'::text, 'failed'::text])))
);


--
-- Name: run_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.run_item (
    id text NOT NULL,
    run_id text NOT NULL,
    artifact_id text,
    response text,
    usage jsonb,
    duration_ms integer,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    passage_id text,
    passage_revision_id text,
    CONSTRAINT run_item_passage_revision_requires_passage CHECK (((passage_revision_id IS NULL) OR (passage_id IS NOT NULL))),
    CONSTRAINT run_item_response_xor_error CHECK (((response IS NULL) <> (error IS NULL)))
);


--
-- Name: source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source (
    id text NOT NULL,
    identity jsonb NOT NULL,
    title text,
    media_type text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_asset (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    ordinal integer NOT NULL,
    kind text NOT NULL,
    filename text NOT NULL,
    mime_type text NOT NULL,
    sha256 text NOT NULL,
    byte_size integer NOT NULL,
    storage_key text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    original_url text,
    CONSTRAINT source_asset_byte_size_check CHECK (((byte_size > 0) AND (byte_size <= 52428800))),
    CONSTRAINT source_asset_filename_check CHECK ((btrim(filename) <> ''::text)),
    CONSTRAINT source_asset_kind_check CHECK ((kind = ANY (ARRAY['pdf'::text, 'ordered_document_pdf'::text, 'pdf_page'::text, 'pdf_figure'::text, 'screenshot'::text, 'image'::text, 'article_image'::text, 'book_page'::text, 'video_frame'::text]))),
    CONSTRAINT source_asset_kind_mime CHECK ((((kind = ANY (ARRAY['pdf'::text, 'ordered_document_pdf'::text])) AND (mime_type = 'application/pdf'::text)) OR ((kind = ANY (ARRAY['pdf_page'::text, 'pdf_figure'::text, 'screenshot'::text, 'image'::text, 'article_image'::text, 'book_page'::text, 'video_frame'::text])) AND (mime_type ~~ 'image/%'::text)))),
    CONSTRAINT source_asset_mime_type_check CHECK ((mime_type = ANY (ARRAY['application/pdf'::text, 'image/png'::text, 'image/jpeg'::text, 'image/webp'::text, 'image/avif'::text, 'image/svg+xml'::text, 'image/gif'::text]))),
    CONSTRAINT source_asset_ordinal_positive CHECK ((ordinal > 0)),
    CONSTRAINT source_asset_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT source_asset_storage_key_check CHECK ((storage_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}$'::text))
);


--
-- Name: source_asset_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_asset_analysis (
    id text NOT NULL,
    source_asset_id text NOT NULL,
    purpose text NOT NULL,
    status text NOT NULL,
    prompt_version text NOT NULL,
    requested_model text,
    response_model text,
    provider text,
    result jsonb DEFAULT '{}'::jsonb NOT NULL,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    analysis_call_id text,
    pdf_page_id text,
    pdf_analysis_call_id text,
    CONSTRAINT source_asset_analysis_duration_ms_check CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT source_asset_analysis_no_inline_image_payload CHECK ((POSITION(('data:image'::text) IN (lower((diagnostics)::text))) = 0)),
    CONSTRAINT source_asset_analysis_purpose_check CHECK ((purpose = ANY (ARRAY['article_image_relevance'::text, 'source_image_analysis'::text, 'video_teaching_beat'::text, 'manual_image_description'::text, 'pdf_page_analysis'::text]))),
    CONSTRAINT source_asset_analysis_shape CHECK ((((status = 'succeeded'::text) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (failure_code IS NOT NULL)))),
    CONSTRAINT source_asset_analysis_status_check CHECK ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])))
);


--
-- Name: source_asset_text; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_asset_text (
    source_asset_id text NOT NULL,
    body text NOT NULL,
    text_sha256 text NOT NULL,
    tool text NOT NULL,
    tool_version text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_asset_text_text_sha256_check CHECK ((text_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT source_asset_text_tool_check CHECK ((btrim(tool) <> ''::text)),
    CONSTRAINT source_asset_text_tool_version_check CHECK ((btrim(tool_version) <> ''::text))
);


--
-- Name: source_cleanup_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_cleanup_job (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    source_artifact_id text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claimed_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    claim_token text,
    cuts_run_id text,
    cleanup_id text,
    canonical_artifact_id text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_cleanup_job_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT source_cleanup_job_state_shape CHECK ((((status = 'queued'::text) AND (claim_token IS NULL) AND (finished_at IS NULL)) OR ((status = 'running'::text) AND (claim_token IS NOT NULL) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])) AND (claim_token IS NULL) AND (finished_at IS NOT NULL)))),
    CONSTRAINT source_cleanup_job_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text]))),
    CONSTRAINT source_cleanup_job_terminal_shape CHECK ((((status = 'succeeded'::text) AND (cleanup_id IS NOT NULL) AND (canonical_artifact_id IS NOT NULL) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (canonical_artifact_id IS NULL) AND (failure_code IS NOT NULL)) OR ((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (canonical_artifact_id IS NULL) AND (failure_code IS NULL))))
);


--
-- Name: source_image_analysis_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_image_analysis_call (
    id text NOT NULL,
    markdown_artifact_id text NOT NULL,
    prompt_ref text NOT NULL,
    prompt_sha text NOT NULL,
    requested_model text NOT NULL,
    input_manifest_hash text,
    status text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claimed_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    claim_token text,
    response_model text,
    provider text,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    operation_kind text DEFAULT 'source_image_analysis'::text NOT NULL,
    result jsonb DEFAULT '{}'::jsonb NOT NULL,
    result_hash text,
    CONSTRAINT source_image_analysis_call_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT source_image_analysis_call_duration_ms_check CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT source_image_analysis_call_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT source_image_analysis_call_operation_kind_check CHECK ((operation_kind = ANY (ARRAY['source_image_analysis'::text, 'video_teaching_beats'::text]))),
    CONSTRAINT source_image_analysis_call_result_hash_check CHECK (((result_hash IS NULL) OR (result_hash ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT source_image_analysis_call_state_shape CHECK ((((status = ANY (ARRAY['waiting'::text, 'queued'::text])) AND (claim_token IS NULL) AND (finished_at IS NULL)) OR ((status = 'running'::text) AND (claim_token IS NOT NULL) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text, 'skipped'::text])) AND (claim_token IS NULL) AND (finished_at IS NOT NULL)))),
    CONSTRAINT source_image_analysis_call_status_check CHECK ((status = ANY (ARRAY['waiting'::text, 'queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text, 'skipped'::text])))
);


--
-- Name: source_image_candidate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_image_candidate (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    snapshot_id text NOT NULL,
    markdown_artifact_id text NOT NULL,
    ordinal integer NOT NULL,
    original_url text NOT NULL,
    alt_text text DEFAULT ''::text NOT NULL,
    placement jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text NOT NULL,
    filter_reason text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    asset_id text,
    analysis_id text,
    attempt_count integer DEFAULT 0 NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claimed_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    claim_token text,
    finished_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_image_candidate_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT source_image_candidate_failure_shape CHECK ((((status = 'failed'::text) AND (failure_code IS NOT NULL)) OR ((status <> 'failed'::text) AND (failure_code IS NULL)))),
    CONSTRAINT source_image_candidate_ordinal_check CHECK ((ordinal > 0)),
    CONSTRAINT source_image_candidate_original_url_check CHECK ((btrim(original_url) <> ''::text)),
    CONSTRAINT source_image_candidate_state_shape CHECK ((((status = 'queued'::text) AND (claim_token IS NULL) AND (finished_at IS NULL)) OR ((status = 'running'::text) AND (claim_token IS NOT NULL) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['filtered'::text, 'downloaded'::text, 'useful'::text, 'not_important'::text, 'failed'::text])) AND (claim_token IS NULL) AND (finished_at IS NOT NULL)))),
    CONSTRAINT source_image_candidate_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'filtered'::text, 'running'::text, 'downloaded'::text, 'useful'::text, 'not_important'::text, 'failed'::text])))
);


--
-- Name: source_pdf_page; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_pdf_page (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    pdf_asset_id text NOT NULL,
    page_number integer NOT NULL,
    text_body text NOT NULL,
    text_sha256 text NOT NULL,
    text_layer_status text NOT NULL,
    render_asset_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_pdf_page_page_number_check CHECK ((page_number > 0)),
    CONSTRAINT source_pdf_page_text_layer_status_check CHECK ((text_layer_status = ANY (ARRAY['usable'::text, 'empty'::text]))),
    CONSTRAINT source_pdf_page_text_sha256_check CHECK ((text_sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: source_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_snapshot (
    id text NOT NULL,
    source_id text NOT NULL,
    captured_at timestamp with time zone,
    content_hash text,
    status text NOT NULL,
    failure_note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_snapshot_status_check CHECK ((status = ANY (ARRAY['ok'::text, 'failed'::text]))),
    CONSTRAINT source_snapshot_status_shape CHECK ((((status = 'ok'::text) AND (content_hash IS NOT NULL) AND (failure_note IS NULL)) OR ((status = 'failed'::text) AND (content_hash IS NULL))))
);


--
-- Name: syllabus; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus (
    id text NOT NULL,
    title text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    institution_id text
);


--
-- Name: syllabus_lesson; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_lesson (
    id text NOT NULL,
    version_id text NOT NULL,
    week integer,
    seq integer NOT NULL,
    kind text NOT NULL,
    title text NOT NULL,
    subject text,
    lesson_date date,
    description text,
    fields jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    subjects text[] DEFAULT ARRAY[]::text[] NOT NULL,
    activity_uuid text,
    folder_uuid text,
    week_order integer,
    activity_order integer
);


--
-- Name: syllabus_lesson_review; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_lesson_review (
    lesson_id text NOT NULL,
    is_validated boolean DEFAULT false NOT NULL,
    complexity text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    version_id text NOT NULL,
    CONSTRAINT syllabus_lesson_review_complexity_check CHECK ((complexity = ANY (ARRAY['simple'::text, 'complex'::text])))
);


--
-- Name: syllabus_reconciliation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_reconciliation (
    id text NOT NULL,
    syllabus_id text NOT NULL,
    base_version_id text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    input_format text NOT NULL,
    file_name text NOT NULL,
    file_mime text NOT NULL,
    file_sha text NOT NULL,
    file_body bytea NOT NULL,
    incoming jsonb NOT NULL,
    plan jsonb NOT NULL,
    decisions jsonb,
    created_version_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_at timestamp with time zone,
    CONSTRAINT syllabus_reconciliation_applied_shape CHECK ((((status = 'pending'::text) AND (created_version_id IS NULL) AND (applied_at IS NULL)) OR ((status = 'applied'::text) AND (created_version_id IS NOT NULL) AND (applied_at IS NOT NULL)))),
    CONSTRAINT syllabus_reconciliation_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'applied'::text])))
);


--
-- Name: syllabus_source_reference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_source_reference (
    id text NOT NULL,
    version_id text NOT NULL,
    lesson_id text NOT NULL,
    seq integer NOT NULL,
    title text NOT NULL,
    description text,
    url text,
    media_type text NOT NULL,
    resource_code text,
    scope_kind text,
    scope_value text,
    source_id text,
    fields jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    activity_uuid text,
    folder_uuid text,
    week_order integer,
    activity_order integer,
    parent_activity_uuid text,
    parent_inference text,
    CONSTRAINT syllabus_source_reference_media_type_check CHECK ((media_type = ANY (ARRAY['article'::text, 'video'::text, 'book'::text]))),
    CONSTRAINT syllabus_source_reference_scope_shape CHECK ((((scope_kind IS NULL) AND (scope_value IS NULL)) OR ((scope_kind IS NOT NULL) AND (scope_value IS NOT NULL))))
);


--
-- Name: syllabus_source_review; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_source_review (
    reference_id text NOT NULL,
    is_validated boolean DEFAULT false NOT NULL,
    validated_artifact_id text,
    validated_content_hash text,
    complexity text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT syllabus_source_review_complexity_check CHECK ((complexity = ANY (ARRAY['simple'::text, 'complex'::text]))),
    CONSTRAINT syllabus_source_review_validation_shape CHECK ((((is_validated = true) AND (validated_artifact_id IS NOT NULL) AND (validated_content_hash IS NOT NULL) AND (btrim(validated_content_hash) <> ''::text)) OR ((is_validated = false) AND (validated_artifact_id IS NULL) AND (validated_content_hash IS NULL))))
);


--
-- Name: syllabus_subject; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_subject (
    syllabus_id text NOT NULL,
    lesson_subject_code text NOT NULL,
    graph_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT syllabus_subject_graph_id_check CHECK ((graph_id ~ '^[a-z][a-z0-9_.-]{1,127}$'::text)),
    CONSTRAINT syllabus_subject_lesson_subject_code_check CHECK ((lesson_subject_code = ANY (ARRAY['COM'::text, 'MTF'::text, 'NEG'::text, 'UEX'::text, 'LID'::text])))
);


--
-- Name: syllabus_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabus_version (
    id text NOT NULL,
    syllabus_id text NOT NULL,
    seq integer NOT NULL,
    origin text NOT NULL,
    file_name text,
    file_sha text,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    input_format text,
    file_mime text,
    file_body bytea,
    CONSTRAINT syllabus_version_origin_check CHECK ((origin = ANY (ARRAY['upload'::text, 'curation'::text])))
);


--
-- Name: video_caption_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_caption_evidence (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    snapshot_id text NOT NULL,
    preflight_id text NOT NULL,
    language text NOT NULL,
    origin text DEFAULT 'publisher_uploaded'::text NOT NULL,
    source_url text NOT NULL,
    vtt_sha256 text NOT NULL,
    vtt_body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    vtt_bytes bytea,
    CONSTRAINT video_caption_evidence_bytes_shape CHECK (((vtt_bytes IS NULL) OR (octet_length(vtt_bytes) > 0))),
    CONSTRAINT video_caption_evidence_language_check CHECK ((btrim(language) <> ''::text)),
    CONSTRAINT video_caption_evidence_origin_check CHECK ((origin = 'publisher_uploaded'::text)),
    CONSTRAINT video_caption_evidence_source_url_check CHECK ((source_url ~ '^https://www\.youtube\.com/watch\?v='::text)),
    CONSTRAINT video_caption_evidence_vtt_body_check CHECK ((btrim(vtt_body) <> ''::text)),
    CONSTRAINT video_caption_evidence_vtt_sha256_check CHECK ((vtt_sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: video_preflight; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_preflight (
    id text NOT NULL,
    source_id text NOT NULL,
    probe_version text NOT NULL,
    input_fingerprint text NOT NULL,
    status text NOT NULL,
    title text,
    channel text,
    duration_seconds double precision,
    uploaded_caption_languages jsonb DEFAULT '[]'::jsonb NOT NULL,
    selected_caption_language text,
    route text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_preflight_caption_shape CHECK ((((route = 'uploaded_caption'::text) AND (selected_caption_language IS NOT NULL)) OR ((route IS DISTINCT FROM 'uploaded_caption'::text) AND (selected_caption_language IS NULL)))),
    CONSTRAINT video_preflight_duration_seconds_check CHECK (((duration_seconds IS NULL) OR (duration_seconds >= (0)::double precision))),
    CONSTRAINT video_preflight_input_fingerprint_check CHECK ((input_fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT video_preflight_route_check CHECK ((route = ANY (ARRAY['uploaded_caption'::text, 'automatic_stt'::text, 'visual_only'::text, 'approval_required'::text]))),
    CONSTRAINT video_preflight_status_check CHECK ((status = ANY (ARRAY['succeeded'::text, 'failed'::text]))),
    CONSTRAINT video_preflight_terminal_shape CHECK ((((status = 'succeeded'::text) AND (route IS NOT NULL) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (route IS NULL) AND (failure_code IS NOT NULL))))
);


--
-- Name: video_stt_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_stt_attempt (
    id text NOT NULL,
    chunk_id text NOT NULL,
    attempt_no integer NOT NULL,
    requested_model text NOT NULL,
    operation_version text NOT NULL,
    status text NOT NULL,
    response_model text,
    provider text,
    generation_id text,
    language text,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer NOT NULL,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_stt_attempt_attempt_no_check CHECK ((attempt_no > 0)),
    CONSTRAINT video_stt_attempt_duration_ms_check CHECK ((duration_ms >= 0)),
    CONSTRAINT video_stt_attempt_result_shape CHECK ((((status = 'succeeded'::text) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (failure_code IS NOT NULL)))),
    CONSTRAINT video_stt_attempt_status_check CHECK ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])))
);


--
-- Name: video_stt_chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_stt_chunk (
    id text NOT NULL,
    source_id text NOT NULL,
    audio_sha256 text NOT NULL,
    chunk_sha256 text NOT NULL,
    window_start_ms bigint NOT NULL,
    window_end_ms bigint NOT NULL,
    requested_model text NOT NULL,
    fallback_model text,
    language text,
    operation_version text NOT NULL,
    model_route_hash text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    available_at timestamp with time zone DEFAULT now() NOT NULL,
    claimed_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    claim_token text,
    text text,
    segments jsonb DEFAULT '[]'::jsonb NOT NULL,
    response_language text,
    response_model text,
    provider text,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    generation_id text,
    failure_code text,
    diagnostics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_stt_chunk_attempt_count_check CHECK ((attempt_count >= 0)),
    CONSTRAINT video_stt_chunk_audio_sha256_check CHECK ((audio_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT video_stt_chunk_check CHECK ((window_end_ms > window_start_ms)),
    CONSTRAINT video_stt_chunk_chunk_sha256_check CHECK ((chunk_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT video_stt_chunk_duration_ms_check CHECK (((duration_ms IS NULL) OR (duration_ms >= 0))),
    CONSTRAINT video_stt_chunk_model_route_hash_check CHECK ((model_route_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT video_stt_chunk_result_shape CHECK ((((status = 'succeeded'::text) AND (text IS NOT NULL) AND (btrim(text) <> ''::text) AND (failure_code IS NULL)) OR ((status = 'failed'::text) AND (text IS NULL) AND (failure_code IS NOT NULL)) OR ((status = ANY (ARRAY['queued'::text, 'running'::text])) AND (text IS NULL) AND (failure_code IS NULL)))),
    CONSTRAINT video_stt_chunk_state_shape CHECK ((((status = 'queued'::text) AND (claim_token IS NULL) AND (finished_at IS NULL)) OR ((status = 'running'::text) AND (claim_token IS NOT NULL) AND (finished_at IS NULL)) OR ((status = ANY (ARRAY['succeeded'::text, 'failed'::text])) AND (claim_token IS NULL) AND (finished_at IS NOT NULL)))),
    CONSTRAINT video_stt_chunk_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text]))),
    CONSTRAINT video_stt_chunk_window_start_ms_check CHECK ((window_start_ms >= 0))
);


--
-- Name: video_stt_job_chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_stt_job_chunk (
    acquisition_job_id text NOT NULL,
    chunk_id text NOT NULL,
    ordinal integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_stt_job_chunk_ordinal_check CHECK ((ordinal > 0))
);


--
-- Name: video_transcript; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_transcript (
    id text NOT NULL,
    acquisition_job_id text NOT NULL,
    source_id text NOT NULL,
    snapshot_id text NOT NULL,
    route text NOT NULL,
    language text,
    grouping_version text NOT NULL,
    segment_count integer NOT NULL,
    content_hash text NOT NULL,
    markdown_artifact_id text NOT NULL,
    visual_analysis text DEFAULT 'deferred'::text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_transcript_content_hash_check CHECK ((content_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT video_transcript_route_check CHECK ((route = ANY (ARRAY['uploaded_caption'::text, 'openrouter_stt'::text]))),
    CONSTRAINT video_transcript_segment_count_check CHECK ((segment_count > 0)),
    CONSTRAINT video_transcript_visual_analysis_check CHECK ((visual_analysis = ANY (ARRAY['deferred'::text, 'pending'::text, 'complete'::text])))
);


--
-- Name: video_transcript_segment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_transcript_segment (
    transcript_id text NOT NULL,
    seq integer NOT NULL,
    start_ms bigint NOT NULL,
    end_ms bigint NOT NULL,
    text text NOT NULL,
    source_kind text NOT NULL,
    source_ref text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT video_transcript_segment_check CHECK ((end_ms >= start_ms)),
    CONSTRAINT video_transcript_segment_seq_check CHECK ((seq > 0)),
    CONSTRAINT video_transcript_segment_source_kind_check CHECK ((source_kind = ANY (ARRAY['caption_cue'::text, 'stt_segment'::text, 'stt_chunk'::text]))),
    CONSTRAINT video_transcript_segment_source_ref_check CHECK ((btrim(source_ref) <> ''::text)),
    CONSTRAINT video_transcript_segment_start_ms_check CHECK ((start_ms >= 0)),
    CONSTRAINT video_transcript_segment_text_check CHECK ((btrim(text) <> ''::text))
);


--
-- Name: acquisition_job acquisition_job_id_source_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_job
    ADD CONSTRAINT acquisition_job_id_source_unique UNIQUE (id, source_id);


--
-- Name: acquisition_job acquisition_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_job
    ADD CONSTRAINT acquisition_job_pkey PRIMARY KEY (id);


--
-- Name: artifact artifact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.artifact
    ADD CONSTRAINT artifact_pkey PRIMARY KEY (id);


--
-- Name: block block_artifact_id_blocker_version_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.block
    ADD CONSTRAINT block_artifact_id_blocker_version_seq_key UNIQUE (artifact_id, blocker_version, seq);


--
-- Name: block block_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.block
    ADD CONSTRAINT block_pkey PRIMARY KEY (id);


--
-- Name: curation_event curation_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curation_event
    ADD CONSTRAINT curation_event_pkey PRIMARY KEY (id);


--
-- Name: institution institution_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.institution
    ADD CONSTRAINT institution_pkey PRIMARY KEY (id);


--
-- Name: lesson_build lesson_build_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build
    ADD CONSTRAINT lesson_build_pkey PRIMARY KEY (id);


--
-- Name: lesson_build lesson_build_request_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build
    ADD CONSTRAINT lesson_build_request_seq_key UNIQUE (request_seq);


--
-- Name: lesson_build lesson_build_version_id_lesson_id_request_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build
    ADD CONSTRAINT lesson_build_version_id_lesson_id_request_key_key UNIQUE (version_id, lesson_id, request_key);


--
-- Name: lesson_build_work lesson_build_work_build_id_artifact_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_build_id_artifact_id_key UNIQUE (build_id, artifact_id);


--
-- Name: lesson_build_work lesson_build_work_build_id_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_build_id_seq_key UNIQUE (build_id, seq);


--
-- Name: lesson_build_work lesson_build_work_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_pkey PRIMARY KEY (id);


--
-- Name: passage passage_artifact_id_blocker_version_first_seq_last_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_artifact_id_blocker_version_first_seq_last_seq_key UNIQUE (artifact_id, blocker_version, first_seq, last_seq);


--
-- Name: passage_cleanup_artifact passage_cleanup_artifact_canonical_artifact_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_artifact
    ADD CONSTRAINT passage_cleanup_artifact_canonical_artifact_id_key UNIQUE (canonical_artifact_id);


--
-- Name: passage_cleanup_artifact passage_cleanup_artifact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_artifact
    ADD CONSTRAINT passage_cleanup_artifact_pkey PRIMARY KEY (cleanup_id, source_artifact_id);


--
-- Name: passage_cleanup passage_cleanup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup
    ADD CONSTRAINT passage_cleanup_pkey PRIMARY KEY (id);


--
-- Name: passage_cleanup_result passage_cleanup_result_decision_run_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_decision_run_item_id_key UNIQUE (decision_run_item_id);


--
-- Name: passage_cleanup_result passage_cleanup_result_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_pkey PRIMARY KEY (cleanup_id, passage_id);


--
-- Name: passage_origin passage_origin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_origin
    ADD CONSTRAINT passage_origin_pkey PRIMARY KEY (passage_id, run_id);


--
-- Name: passage passage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_pkey PRIMARY KEY (id);


--
-- Name: passage_revision_drop passage_revision_drop_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision_drop
    ADD CONSTRAINT passage_revision_drop_pkey PRIMARY KEY (revision_id, block_id);


--
-- Name: passage_revision passage_revision_id_passage_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_id_passage_id_key UNIQUE (id, passage_id);


--
-- Name: passage_revision passage_revision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_pkey PRIMARY KEY (id);


--
-- Name: passage_revision passage_revision_refine_run_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_refine_run_item_id_key UNIQUE (refine_run_item_id);


--
-- Name: pdf_document_parse_call pdf_document_parse_call_acquisition_job_id_pdf_asset_id_par_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_document_parse_call
    ADD CONSTRAINT pdf_document_parse_call_acquisition_job_id_pdf_asset_id_par_key UNIQUE (acquisition_job_id, pdf_asset_id, parser_ref);


--
-- Name: pdf_document_parse_call pdf_document_parse_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_document_parse_call
    ADD CONSTRAINT pdf_document_parse_call_pkey PRIMARY KEY (id);


--
-- Name: pdf_figure_localization_call pdf_figure_localization_call_acquisition_job_id_pdf_asset_i_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_localization_call
    ADD CONSTRAINT pdf_figure_localization_call_acquisition_job_id_pdf_asset_i_key UNIQUE (acquisition_job_id, pdf_asset_id, batch_ordinal, prompt_ref);


--
-- Name: pdf_figure_localization_call pdf_figure_localization_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_localization_call
    ADD CONSTRAINT pdf_figure_localization_call_pkey PRIMARY KEY (id);


--
-- Name: pdf_figure_region_outcome pdf_figure_region_outcome_localization_call_id_region_ordin_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_region_outcome
    ADD CONSTRAINT pdf_figure_region_outcome_localization_call_id_region_ordin_key UNIQUE (localization_call_id, region_ordinal);


--
-- Name: pdf_figure_region_outcome pdf_figure_region_outcome_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_region_outcome
    ADD CONSTRAINT pdf_figure_region_outcome_pkey PRIMARY KEY (id);


--
-- Name: pdf_page_analysis_call pdf_page_analysis_call_acquisition_job_id_batch_ordinal_pro_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_page_analysis_call
    ADD CONSTRAINT pdf_page_analysis_call_acquisition_job_id_batch_ordinal_pro_key UNIQUE (acquisition_job_id, batch_ordinal, prompt_ref);


--
-- Name: pdf_page_analysis_call pdf_page_analysis_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_page_analysis_call
    ADD CONSTRAINT pdf_page_analysis_call_pkey PRIMARY KEY (id);


--
-- Name: pipeline_lease pipeline_lease_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_lease
    ADD CONSTRAINT pipeline_lease_pkey PRIMARY KEY (scope_key, stage);


--
-- Name: run_item run_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run_item
    ADD CONSTRAINT run_item_pkey PRIMARY KEY (id);


--
-- Name: run run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run
    ADD CONSTRAINT run_pkey PRIMARY KEY (id);


--
-- Name: source_asset source_asset_acquisition_job_id_ordinal_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset
    ADD CONSTRAINT source_asset_acquisition_job_id_ordinal_key UNIQUE (acquisition_job_id, ordinal);


--
-- Name: source_asset_analysis source_asset_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_pkey PRIMARY KEY (id);


--
-- Name: source_asset source_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset
    ADD CONSTRAINT source_asset_pkey PRIMARY KEY (id);


--
-- Name: source_asset_text source_asset_text_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_text
    ADD CONSTRAINT source_asset_text_pkey PRIMARY KEY (source_asset_id);


--
-- Name: source_cleanup_job source_cleanup_job_acquisition_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_acquisition_job_id_key UNIQUE (acquisition_job_id);


--
-- Name: source_cleanup_job source_cleanup_job_canonical_artifact_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_canonical_artifact_id_key UNIQUE (canonical_artifact_id);


--
-- Name: source_cleanup_job source_cleanup_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_pkey PRIMARY KEY (id);


--
-- Name: source_cleanup_job source_cleanup_job_source_artifact_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_source_artifact_id_key UNIQUE (source_artifact_id);


--
-- Name: source_image_analysis_call source_image_analysis_call_markdown_artifact_id_prompt_ref_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_analysis_call
    ADD CONSTRAINT source_image_analysis_call_markdown_artifact_id_prompt_ref_key UNIQUE (markdown_artifact_id, prompt_ref);


--
-- Name: source_image_analysis_call source_image_analysis_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_analysis_call
    ADD CONSTRAINT source_image_analysis_call_pkey PRIMARY KEY (id);


--
-- Name: source_image_candidate source_image_candidate_acquisition_job_id_ordinal_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_acquisition_job_id_ordinal_key UNIQUE (acquisition_job_id, ordinal);


--
-- Name: source_image_candidate source_image_candidate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_pkey PRIMARY KEY (id);


--
-- Name: source_pdf_page source_pdf_page_acquisition_job_id_page_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_acquisition_job_id_page_number_key UNIQUE (acquisition_job_id, page_number);


--
-- Name: source_pdf_page source_pdf_page_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_pkey PRIMARY KEY (id);


--
-- Name: source_pdf_page source_pdf_page_render_asset_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_render_asset_id_key UNIQUE (render_asset_id);


--
-- Name: source source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source
    ADD CONSTRAINT source_pkey PRIMARY KEY (id);


--
-- Name: source_snapshot source_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_snapshot
    ADD CONSTRAINT source_snapshot_pkey PRIMARY KEY (id);


--
-- Name: syllabus syllabus_id_institution_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus
    ADD CONSTRAINT syllabus_id_institution_key UNIQUE (id, institution_id);


--
-- Name: syllabus_lesson syllabus_lesson_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_lesson
    ADD CONSTRAINT syllabus_lesson_pkey PRIMARY KEY (version_id, id);


--
-- Name: syllabus_lesson_review syllabus_lesson_review_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_lesson_review
    ADD CONSTRAINT syllabus_lesson_review_pkey PRIMARY KEY (version_id, lesson_id);


--
-- Name: syllabus_lesson syllabus_lesson_version_id_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_lesson
    ADD CONSTRAINT syllabus_lesson_version_id_id_key UNIQUE (version_id, id);


--
-- Name: syllabus syllabus_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus
    ADD CONSTRAINT syllabus_pkey PRIMARY KEY (id);


--
-- Name: syllabus_reconciliation syllabus_reconciliation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_reconciliation
    ADD CONSTRAINT syllabus_reconciliation_pkey PRIMARY KEY (id);


--
-- Name: syllabus_reconciliation syllabus_reconciliation_syllabus_id_base_version_id_file_sh_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_reconciliation
    ADD CONSTRAINT syllabus_reconciliation_syllabus_id_base_version_id_file_sh_key UNIQUE (syllabus_id, base_version_id, file_sha);


--
-- Name: syllabus_source_reference syllabus_source_reference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_reference
    ADD CONSTRAINT syllabus_source_reference_pkey PRIMARY KEY (id);


--
-- Name: syllabus_source_review syllabus_source_review_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_review
    ADD CONSTRAINT syllabus_source_review_pkey PRIMARY KEY (reference_id);


--
-- Name: syllabus_subject syllabus_subject_graph_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_subject
    ADD CONSTRAINT syllabus_subject_graph_id_key UNIQUE (graph_id);


--
-- Name: syllabus_subject syllabus_subject_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_subject
    ADD CONSTRAINT syllabus_subject_pkey PRIMARY KEY (syllabus_id, lesson_subject_code);


--
-- Name: syllabus_version syllabus_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_version
    ADD CONSTRAINT syllabus_version_pkey PRIMARY KEY (id);


--
-- Name: syllabus_version syllabus_version_syllabus_id_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_version
    ADD CONSTRAINT syllabus_version_syllabus_id_seq_key UNIQUE (syllabus_id, seq);


--
-- Name: video_caption_evidence video_caption_evidence_acquisition_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_acquisition_job_id_key UNIQUE (acquisition_job_id);


--
-- Name: video_caption_evidence video_caption_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_pkey PRIMARY KEY (id);


--
-- Name: video_caption_evidence video_caption_evidence_snapshot_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_snapshot_id_key UNIQUE (snapshot_id);


--
-- Name: video_preflight video_preflight_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_preflight
    ADD CONSTRAINT video_preflight_pkey PRIMARY KEY (id);


--
-- Name: video_stt_attempt video_stt_attempt_chunk_id_attempt_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_attempt
    ADD CONSTRAINT video_stt_attempt_chunk_id_attempt_no_key UNIQUE (chunk_id, attempt_no);


--
-- Name: video_stt_attempt video_stt_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_attempt
    ADD CONSTRAINT video_stt_attempt_pkey PRIMARY KEY (id);


--
-- Name: video_stt_chunk video_stt_chunk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_chunk
    ADD CONSTRAINT video_stt_chunk_pkey PRIMARY KEY (id);


--
-- Name: video_stt_chunk video_stt_chunk_source_id_audio_sha256_chunk_sha256_window__key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_chunk
    ADD CONSTRAINT video_stt_chunk_source_id_audio_sha256_chunk_sha256_window__key UNIQUE (source_id, audio_sha256, chunk_sha256, window_start_ms, window_end_ms, model_route_hash, operation_version);


--
-- Name: video_stt_job_chunk video_stt_job_chunk_acquisition_job_id_chunk_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_job_chunk
    ADD CONSTRAINT video_stt_job_chunk_acquisition_job_id_chunk_id_key UNIQUE (acquisition_job_id, chunk_id);


--
-- Name: video_stt_job_chunk video_stt_job_chunk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_job_chunk
    ADD CONSTRAINT video_stt_job_chunk_pkey PRIMARY KEY (acquisition_job_id, ordinal);


--
-- Name: video_transcript video_transcript_acquisition_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_acquisition_job_id_key UNIQUE (acquisition_job_id);


--
-- Name: video_transcript video_transcript_markdown_artifact_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_markdown_artifact_id_key UNIQUE (markdown_artifact_id);


--
-- Name: video_transcript video_transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_pkey PRIMARY KEY (id);


--
-- Name: video_transcript_segment video_transcript_segment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript_segment
    ADD CONSTRAINT video_transcript_segment_pkey PRIMARY KEY (transcript_id, seq);


--
-- Name: video_transcript video_transcript_snapshot_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_snapshot_id_key UNIQUE (snapshot_id);


--
-- Name: acquisition_job_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX acquisition_job_claim_idx ON public.acquisition_job USING btree (available_at, created_at) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: acquisition_job_one_active_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX acquisition_job_one_active_source_idx ON public.acquisition_job USING btree (source_id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: acquisition_job_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX acquisition_job_source_idx ON public.acquisition_job USING btree (source_id, created_at DESC);


--
-- Name: artifact_snapshot_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX artifact_snapshot_idx ON public.artifact USING btree (snapshot_id);


--
-- Name: block_artifact_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX block_artifact_idx ON public.block USING btree (artifact_id);


--
-- Name: lesson_build_lesson_latest_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lesson_build_lesson_latest_idx ON public.lesson_build USING btree (version_id, lesson_id, request_seq DESC);


--
-- Name: lesson_build_work_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lesson_build_work_claim_idx ON public.lesson_build_work USING btree (available_at, created_at, id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: lesson_build_work_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lesson_build_work_status_idx ON public.lesson_build_work USING btree (status, created_at, id);


--
-- Name: passage_artifact_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX passage_artifact_idx ON public.passage USING btree (artifact_id);


--
-- Name: passage_cleanup_result_revision_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX passage_cleanup_result_revision_idx ON public.passage_cleanup_result USING btree (passage_revision_id);


--
-- Name: passage_origin_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX passage_origin_run_idx ON public.passage_origin USING btree (run_id);


--
-- Name: passage_revision_parent_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX passage_revision_parent_idx ON public.passage_revision USING btree (parent_revision_id);


--
-- Name: passage_revision_passage_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX passage_revision_passage_idx ON public.passage_revision USING btree (passage_id);


--
-- Name: pdf_document_parse_call_job_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pdf_document_parse_call_job_idx ON public.pdf_document_parse_call USING btree (acquisition_job_id, created_at, id);


--
-- Name: pdf_figure_localization_call_job_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pdf_figure_localization_call_job_idx ON public.pdf_figure_localization_call USING btree (acquisition_job_id, batch_ordinal, id);


--
-- Name: pdf_figure_region_outcome_asset_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pdf_figure_region_outcome_asset_idx ON public.pdf_figure_region_outcome USING btree (source_asset_id) WHERE (source_asset_id IS NOT NULL);


--
-- Name: pdf_figure_region_outcome_call_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pdf_figure_region_outcome_call_idx ON public.pdf_figure_region_outcome USING btree (localization_call_id, region_ordinal);


--
-- Name: run_item_artifact_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX run_item_artifact_idx ON public.run_item USING btree (artifact_id);


--
-- Name: run_item_passage_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX run_item_passage_idx ON public.run_item USING btree (passage_id);


--
-- Name: run_item_passage_revision_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX run_item_passage_revision_idx ON public.run_item USING btree (passage_revision_id);


--
-- Name: run_item_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX run_item_run_idx ON public.run_item USING btree (run_id);


--
-- Name: source_asset_analysis_asset_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_asset_analysis_asset_idx ON public.source_asset_analysis USING btree (source_asset_id, created_at, id);


--
-- Name: source_asset_analysis_call_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_asset_analysis_call_idx ON public.source_asset_analysis USING btree (analysis_call_id, source_asset_id);


--
-- Name: source_asset_analysis_pdf_page_call_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX source_asset_analysis_pdf_page_call_idx ON public.source_asset_analysis USING btree (pdf_page_id, pdf_analysis_call_id) WHERE (pdf_page_id IS NOT NULL);


--
-- Name: source_asset_job_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_asset_job_idx ON public.source_asset USING btree (acquisition_job_id, ordinal);


--
-- Name: source_asset_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_asset_source_idx ON public.source_asset USING btree (source_id, created_at DESC);


--
-- Name: source_cleanup_job_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_cleanup_job_claim_idx ON public.source_cleanup_job USING btree (available_at, created_at, id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: source_cleanup_job_one_active_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX source_cleanup_job_one_active_source_idx ON public.source_cleanup_job USING btree (source_id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: source_cleanup_job_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_cleanup_job_source_idx ON public.source_cleanup_job USING btree (source_id, created_at DESC);


--
-- Name: source_image_analysis_call_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_image_analysis_call_claim_idx ON public.source_image_analysis_call USING btree (available_at, created_at, id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: source_image_candidate_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_image_candidate_claim_idx ON public.source_image_candidate USING btree (available_at, created_at, id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text]));


--
-- Name: source_image_candidate_markdown_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_image_candidate_markdown_idx ON public.source_image_candidate USING btree (markdown_artifact_id, ordinal);


--
-- Name: source_image_candidate_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_image_candidate_source_idx ON public.source_image_candidate USING btree (source_id, created_at, ordinal);


--
-- Name: source_pdf_page_job_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_pdf_page_job_idx ON public.source_pdf_page USING btree (acquisition_job_id, page_number);


--
-- Name: source_snapshot_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX source_snapshot_source_idx ON public.source_snapshot USING btree (source_id);


--
-- Name: syllabus_lesson_adalove_activity_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX syllabus_lesson_adalove_activity_idx ON public.syllabus_lesson USING btree (version_id, activity_uuid) WHERE (activity_uuid IS NOT NULL);


--
-- Name: syllabus_lesson_identity_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_lesson_identity_idx ON public.syllabus_lesson USING btree (id, version_id);


--
-- Name: syllabus_lesson_version_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_lesson_version_idx ON public.syllabus_lesson USING btree (version_id, week, seq, id);


--
-- Name: syllabus_lesson_visible_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_lesson_visible_idx ON public.syllabus_lesson USING btree (version_id, week, seq, id) WHERE (NOT is_hidden);


--
-- Name: syllabus_reconciliation_applied_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_reconciliation_applied_idx ON public.syllabus_reconciliation USING btree (syllabus_id, applied_at DESC, id) WHERE (status = 'applied'::text);


--
-- Name: syllabus_reconciliation_syllabus_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_reconciliation_syllabus_idx ON public.syllabus_reconciliation USING btree (syllabus_id, created_at DESC, id);


--
-- Name: syllabus_source_reference_adalove_activity_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_source_reference_adalove_activity_idx ON public.syllabus_source_reference USING btree (version_id, activity_uuid, seq, id) WHERE (activity_uuid IS NOT NULL);


--
-- Name: syllabus_source_reference_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_source_reference_source_idx ON public.syllabus_source_reference USING btree (source_id);


--
-- Name: syllabus_source_reference_version_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_source_reference_version_idx ON public.syllabus_source_reference USING btree (version_id, lesson_id, seq, id);


--
-- Name: syllabus_source_reference_visible_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_source_reference_visible_idx ON public.syllabus_source_reference USING btree (version_id, lesson_id, seq, id) WHERE (NOT is_hidden);


--
-- Name: syllabus_version_syllabus_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX syllabus_version_syllabus_idx ON public.syllabus_version USING btree (syllabus_id, seq DESC);


--
-- Name: video_preflight_source_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX video_preflight_source_idx ON public.video_preflight USING btree (source_id, created_at DESC, id DESC);


--
-- Name: video_stt_chunk_claim_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX video_stt_chunk_claim_idx ON public.video_stt_chunk USING btree (available_at, created_at, id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text, 'failed'::text]));


--
-- Name: source_asset source_asset_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER source_asset_immutable BEFORE DELETE OR UPDATE ON public.source_asset FOR EACH ROW EXECUTE FUNCTION public.reject_source_asset_mutation();


--
-- Name: source_asset_text source_asset_text_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER source_asset_text_immutable BEFORE DELETE OR UPDATE ON public.source_asset_text FOR EACH ROW EXECUTE FUNCTION public.reject_source_asset_mutation();


--
-- Name: source_pdf_page source_pdf_page_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER source_pdf_page_immutable BEFORE DELETE OR UPDATE ON public.source_pdf_page FOR EACH ROW EXECUTE FUNCTION public.reject_source_asset_mutation();


--
-- Name: video_caption_evidence video_caption_evidence_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER video_caption_evidence_immutable BEFORE DELETE OR UPDATE ON public.video_caption_evidence FOR EACH ROW EXECUTE FUNCTION public.reject_video_transcript_fact_mutation();


--
-- Name: video_preflight video_preflight_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER video_preflight_immutable BEFORE DELETE OR UPDATE ON public.video_preflight FOR EACH ROW EXECUTE FUNCTION public.reject_video_transcript_fact_mutation();


--
-- Name: video_stt_attempt video_stt_attempt_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER video_stt_attempt_immutable BEFORE DELETE OR UPDATE ON public.video_stt_attempt FOR EACH ROW EXECUTE FUNCTION public.reject_video_transcript_fact_mutation();


--
-- Name: video_transcript video_transcript_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER video_transcript_immutable BEFORE DELETE OR UPDATE ON public.video_transcript FOR EACH ROW EXECUTE FUNCTION public.reject_video_transcript_fact_mutation();


--
-- Name: video_transcript_segment video_transcript_segment_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER video_transcript_segment_immutable BEFORE DELETE OR UPDATE ON public.video_transcript_segment FOR EACH ROW EXECUTE FUNCTION public.reject_video_transcript_fact_mutation();


--
-- Name: acquisition_job acquisition_job_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_job
    ADD CONSTRAINT acquisition_job_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES public.artifact(id);


--
-- Name: acquisition_job acquisition_job_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_job
    ADD CONSTRAINT acquisition_job_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: acquisition_job acquisition_job_video_preflight_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisition_job
    ADD CONSTRAINT acquisition_job_video_preflight_id_fkey FOREIGN KEY (video_preflight_id) REFERENCES public.video_preflight(id);


--
-- Name: artifact artifact_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.artifact
    ADD CONSTRAINT artifact_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES public.source_snapshot(id);


--
-- Name: block block_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.block
    ADD CONSTRAINT block_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES public.artifact(id);


--
-- Name: lesson_build lesson_build_version_id_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build
    ADD CONSTRAINT lesson_build_version_id_lesson_id_fkey FOREIGN KEY (version_id, lesson_id) REFERENCES public.syllabus_lesson(version_id, id);


--
-- Name: lesson_build_work lesson_build_work_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES public.artifact(id);


--
-- Name: lesson_build_work lesson_build_work_build_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_build_id_fkey FOREIGN KEY (build_id) REFERENCES public.lesson_build(id);


--
-- Name: lesson_build_work lesson_build_work_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES public.source_snapshot(id);


--
-- Name: lesson_build_work lesson_build_work_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_build_work
    ADD CONSTRAINT lesson_build_work_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: passage passage_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES public.artifact(id);


--
-- Name: passage_cleanup_artifact passage_cleanup_artifact_canonical_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_artifact
    ADD CONSTRAINT passage_cleanup_artifact_canonical_artifact_id_fkey FOREIGN KEY (canonical_artifact_id) REFERENCES public.artifact(id);


--
-- Name: passage_cleanup_artifact passage_cleanup_artifact_cleanup_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_artifact
    ADD CONSTRAINT passage_cleanup_artifact_cleanup_id_fkey FOREIGN KEY (cleanup_id) REFERENCES public.passage_cleanup(id);


--
-- Name: passage_cleanup_artifact passage_cleanup_artifact_source_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_artifact
    ADD CONSTRAINT passage_cleanup_artifact_source_artifact_id_fkey FOREIGN KEY (source_artifact_id) REFERENCES public.artifact(id);


--
-- Name: passage_cleanup passage_cleanup_cuts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup
    ADD CONSTRAINT passage_cleanup_cuts_run_id_fkey FOREIGN KEY (cuts_run_id) REFERENCES public.run(id);


--
-- Name: passage_cleanup_result passage_cleanup_result_cleanup_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_cleanup_id_fkey FOREIGN KEY (cleanup_id) REFERENCES public.passage_cleanup(id);


--
-- Name: passage_cleanup_result passage_cleanup_result_decision_run_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_decision_run_item_id_fkey FOREIGN KEY (decision_run_item_id) REFERENCES public.run_item(id);


--
-- Name: passage_cleanup_result passage_cleanup_result_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_passage_id_fkey FOREIGN KEY (passage_id) REFERENCES public.passage(id);


--
-- Name: passage_cleanup_result passage_cleanup_result_passage_revision_id_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_cleanup_result
    ADD CONSTRAINT passage_cleanup_result_passage_revision_id_passage_id_fkey FOREIGN KEY (passage_revision_id, passage_id) REFERENCES public.passage_revision(id, passage_id);


--
-- Name: passage_origin passage_origin_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_origin
    ADD CONSTRAINT passage_origin_passage_id_fkey FOREIGN KEY (passage_id) REFERENCES public.passage(id);


--
-- Name: passage_origin passage_origin_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_origin
    ADD CONSTRAINT passage_origin_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.run(id);


--
-- Name: passage_revision_drop passage_revision_drop_block_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision_drop
    ADD CONSTRAINT passage_revision_drop_block_id_fkey FOREIGN KEY (block_id) REFERENCES public.block(id);


--
-- Name: passage_revision_drop passage_revision_drop_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision_drop
    ADD CONSTRAINT passage_revision_drop_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.passage_revision(id);


--
-- Name: passage_revision passage_revision_parent_revision_id_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_parent_revision_id_passage_id_fkey FOREIGN KEY (parent_revision_id, passage_id) REFERENCES public.passage_revision(id, passage_id);


--
-- Name: passage_revision passage_revision_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_passage_id_fkey FOREIGN KEY (passage_id) REFERENCES public.passage(id);


--
-- Name: passage_revision passage_revision_refine_run_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_revision
    ADD CONSTRAINT passage_revision_refine_run_item_id_fkey FOREIGN KEY (refine_run_item_id) REFERENCES public.run_item(id);


--
-- Name: pdf_document_parse_call pdf_document_parse_call_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_document_parse_call
    ADD CONSTRAINT pdf_document_parse_call_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: pdf_document_parse_call pdf_document_parse_call_pdf_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_document_parse_call
    ADD CONSTRAINT pdf_document_parse_call_pdf_asset_id_fkey FOREIGN KEY (pdf_asset_id) REFERENCES public.source_asset(id);


--
-- Name: pdf_figure_localization_call pdf_figure_localization_call_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_localization_call
    ADD CONSTRAINT pdf_figure_localization_call_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: pdf_figure_localization_call pdf_figure_localization_call_pdf_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_localization_call
    ADD CONSTRAINT pdf_figure_localization_call_pdf_asset_id_fkey FOREIGN KEY (pdf_asset_id) REFERENCES public.source_asset(id);


--
-- Name: pdf_figure_region_outcome pdf_figure_region_outcome_localization_call_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_region_outcome
    ADD CONSTRAINT pdf_figure_region_outcome_localization_call_id_fkey FOREIGN KEY (localization_call_id) REFERENCES public.pdf_figure_localization_call(id);


--
-- Name: pdf_figure_region_outcome pdf_figure_region_outcome_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_region_outcome
    ADD CONSTRAINT pdf_figure_region_outcome_page_id_fkey FOREIGN KEY (page_id) REFERENCES public.source_pdf_page(id);


--
-- Name: pdf_figure_region_outcome pdf_figure_region_outcome_source_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_figure_region_outcome
    ADD CONSTRAINT pdf_figure_region_outcome_source_asset_id_fkey FOREIGN KEY (source_asset_id) REFERENCES public.source_asset(id);


--
-- Name: pdf_page_analysis_call pdf_page_analysis_call_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_page_analysis_call
    ADD CONSTRAINT pdf_page_analysis_call_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: pdf_page_analysis_call pdf_page_analysis_call_pdf_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_page_analysis_call
    ADD CONSTRAINT pdf_page_analysis_call_pdf_asset_id_fkey FOREIGN KEY (pdf_asset_id) REFERENCES public.source_asset(id);


--
-- Name: run_item run_item_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run_item
    ADD CONSTRAINT run_item_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES public.artifact(id);


--
-- Name: run_item run_item_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run_item
    ADD CONSTRAINT run_item_passage_id_fkey FOREIGN KEY (passage_id) REFERENCES public.passage(id);


--
-- Name: run_item run_item_passage_revision_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run_item
    ADD CONSTRAINT run_item_passage_revision_fk FOREIGN KEY (passage_revision_id, passage_id) REFERENCES public.passage_revision(id, passage_id);


--
-- Name: run_item run_item_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.run_item
    ADD CONSTRAINT run_item_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.run(id);


--
-- Name: source_asset source_asset_acquisition_job_id_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset
    ADD CONSTRAINT source_asset_acquisition_job_id_source_id_fkey FOREIGN KEY (acquisition_job_id, source_id) REFERENCES public.acquisition_job(id, source_id);


--
-- Name: source_asset_analysis source_asset_analysis_analysis_call_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_analysis_call_id_fkey FOREIGN KEY (analysis_call_id) REFERENCES public.source_image_analysis_call(id);


--
-- Name: source_asset_analysis source_asset_analysis_pdf_analysis_call_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_pdf_analysis_call_id_fkey FOREIGN KEY (pdf_analysis_call_id) REFERENCES public.pdf_page_analysis_call(id);


--
-- Name: source_asset_analysis source_asset_analysis_pdf_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_pdf_page_id_fkey FOREIGN KEY (pdf_page_id) REFERENCES public.source_pdf_page(id);


--
-- Name: source_asset_analysis source_asset_analysis_source_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_source_asset_id_fkey FOREIGN KEY (source_asset_id) REFERENCES public.source_asset(id);


--
-- Name: source_asset_text source_asset_text_source_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_asset_text
    ADD CONSTRAINT source_asset_text_source_asset_id_fkey FOREIGN KEY (source_asset_id) REFERENCES public.source_asset(id);


--
-- Name: source_cleanup_job source_cleanup_job_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: source_cleanup_job source_cleanup_job_canonical_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_canonical_artifact_id_fkey FOREIGN KEY (canonical_artifact_id) REFERENCES public.artifact(id);


--
-- Name: source_cleanup_job source_cleanup_job_cleanup_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_cleanup_id_fkey FOREIGN KEY (cleanup_id) REFERENCES public.passage_cleanup(id);


--
-- Name: source_cleanup_job source_cleanup_job_cuts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_cuts_run_id_fkey FOREIGN KEY (cuts_run_id) REFERENCES public.run(id);


--
-- Name: source_cleanup_job source_cleanup_job_source_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_source_artifact_id_fkey FOREIGN KEY (source_artifact_id) REFERENCES public.artifact(id);


--
-- Name: source_cleanup_job source_cleanup_job_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_cleanup_job
    ADD CONSTRAINT source_cleanup_job_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: source_image_analysis_call source_image_analysis_call_markdown_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_analysis_call
    ADD CONSTRAINT source_image_analysis_call_markdown_artifact_id_fkey FOREIGN KEY (markdown_artifact_id) REFERENCES public.artifact(id);


--
-- Name: source_image_candidate source_image_candidate_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: source_image_candidate source_image_candidate_analysis_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_analysis_fk FOREIGN KEY (analysis_id) REFERENCES public.source_asset_analysis(id);


--
-- Name: source_image_candidate source_image_candidate_asset_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_asset_fk FOREIGN KEY (asset_id) REFERENCES public.source_asset(id);


--
-- Name: source_image_candidate source_image_candidate_markdown_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_markdown_artifact_id_fkey FOREIGN KEY (markdown_artifact_id) REFERENCES public.artifact(id);


--
-- Name: source_image_candidate source_image_candidate_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES public.source_snapshot(id);


--
-- Name: source_image_candidate source_image_candidate_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_image_candidate
    ADD CONSTRAINT source_image_candidate_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: source_pdf_page source_pdf_page_acquisition_job_id_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_acquisition_job_id_source_id_fkey FOREIGN KEY (acquisition_job_id, source_id) REFERENCES public.acquisition_job(id, source_id);


--
-- Name: source_pdf_page source_pdf_page_pdf_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_pdf_asset_id_fkey FOREIGN KEY (pdf_asset_id) REFERENCES public.source_asset(id);


--
-- Name: source_pdf_page source_pdf_page_render_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_pdf_page
    ADD CONSTRAINT source_pdf_page_render_asset_id_fkey FOREIGN KEY (render_asset_id) REFERENCES public.source_asset(id);


--
-- Name: source_snapshot source_snapshot_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_snapshot
    ADD CONSTRAINT source_snapshot_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: syllabus syllabus_institution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus
    ADD CONSTRAINT syllabus_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES public.institution(id);


--
-- Name: syllabus_lesson_review syllabus_lesson_review_version_id_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_lesson_review
    ADD CONSTRAINT syllabus_lesson_review_version_id_lesson_id_fkey FOREIGN KEY (version_id, lesson_id) REFERENCES public.syllabus_lesson(version_id, id);


--
-- Name: syllabus_lesson syllabus_lesson_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_lesson
    ADD CONSTRAINT syllabus_lesson_version_id_fkey FOREIGN KEY (version_id) REFERENCES public.syllabus_version(id);


--
-- Name: syllabus_reconciliation syllabus_reconciliation_base_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_reconciliation
    ADD CONSTRAINT syllabus_reconciliation_base_version_id_fkey FOREIGN KEY (base_version_id) REFERENCES public.syllabus_version(id);


--
-- Name: syllabus_reconciliation syllabus_reconciliation_created_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_reconciliation
    ADD CONSTRAINT syllabus_reconciliation_created_version_id_fkey FOREIGN KEY (created_version_id) REFERENCES public.syllabus_version(id);


--
-- Name: syllabus_reconciliation syllabus_reconciliation_syllabus_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_reconciliation
    ADD CONSTRAINT syllabus_reconciliation_syllabus_id_fkey FOREIGN KEY (syllabus_id) REFERENCES public.syllabus(id);


--
-- Name: syllabus_source_reference syllabus_source_reference_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_reference
    ADD CONSTRAINT syllabus_source_reference_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: syllabus_source_reference syllabus_source_reference_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_reference
    ADD CONSTRAINT syllabus_source_reference_version_id_fkey FOREIGN KEY (version_id) REFERENCES public.syllabus_version(id);


--
-- Name: syllabus_source_reference syllabus_source_reference_version_id_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_reference
    ADD CONSTRAINT syllabus_source_reference_version_id_lesson_id_fkey FOREIGN KEY (version_id, lesson_id) REFERENCES public.syllabus_lesson(version_id, id);


--
-- Name: syllabus_source_review syllabus_source_review_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_review
    ADD CONSTRAINT syllabus_source_review_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES public.syllabus_source_reference(id);


--
-- Name: syllabus_source_review syllabus_source_review_validated_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_source_review
    ADD CONSTRAINT syllabus_source_review_validated_artifact_id_fkey FOREIGN KEY (validated_artifact_id) REFERENCES public.artifact(id);


--
-- Name: syllabus_subject syllabus_subject_syllabus_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_subject
    ADD CONSTRAINT syllabus_subject_syllabus_id_fkey FOREIGN KEY (syllabus_id) REFERENCES public.syllabus(id);


--
-- Name: syllabus_version syllabus_version_syllabus_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabus_version
    ADD CONSTRAINT syllabus_version_syllabus_id_fkey FOREIGN KEY (syllabus_id) REFERENCES public.syllabus(id);


--
-- Name: video_caption_evidence video_caption_evidence_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: video_caption_evidence video_caption_evidence_preflight_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_preflight_id_fkey FOREIGN KEY (preflight_id) REFERENCES public.video_preflight(id);


--
-- Name: video_caption_evidence video_caption_evidence_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES public.source_snapshot(id);


--
-- Name: video_caption_evidence video_caption_evidence_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: video_preflight video_preflight_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_preflight
    ADD CONSTRAINT video_preflight_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: video_stt_attempt video_stt_attempt_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_attempt
    ADD CONSTRAINT video_stt_attempt_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.video_stt_chunk(id);


--
-- Name: video_stt_chunk video_stt_chunk_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_chunk
    ADD CONSTRAINT video_stt_chunk_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);


--
-- Name: video_stt_job_chunk video_stt_job_chunk_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_job_chunk
    ADD CONSTRAINT video_stt_job_chunk_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: video_stt_job_chunk video_stt_job_chunk_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stt_job_chunk
    ADD CONSTRAINT video_stt_job_chunk_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.video_stt_chunk(id);


--
-- Name: video_transcript video_transcript_acquisition_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_acquisition_job_id_fkey FOREIGN KEY (acquisition_job_id) REFERENCES public.acquisition_job(id);


--
-- Name: video_transcript video_transcript_markdown_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_markdown_artifact_id_fkey FOREIGN KEY (markdown_artifact_id) REFERENCES public.artifact(id);


--
-- Name: video_transcript_segment video_transcript_segment_transcript_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript_segment
    ADD CONSTRAINT video_transcript_segment_transcript_id_fkey FOREIGN KEY (transcript_id) REFERENCES public.video_transcript(id);


--
-- Name: video_transcript video_transcript_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES public.source_snapshot(id);


--
-- Name: video_transcript video_transcript_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_transcript
    ADD CONSTRAINT video_transcript_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id);
