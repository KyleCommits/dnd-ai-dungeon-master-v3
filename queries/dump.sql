--
-- PostgreSQL database dump
--

\restrict 6PZW2vsBYxGwDLIixpn8hZuoaVySNzk9O9z8mvmL48O0mCCchf9y8ZRk5MfB8ge

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: cleanup_old_sessions(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_old_sessions() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark sessions inactive if no activity for 24 hours
    UPDATE chat_sessions
    SET is_active = false
    WHERE last_activity < NOW() - INTERVAL '24 hours'
    AND is_active = true;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;


ALTER FUNCTION public.cleanup_old_sessions() OWNER TO postgres;

--
-- Name: get_conversation_history(character varying, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_conversation_history(p_session_id character varying, p_limit integer DEFAULT 20) RETURNS TABLE(message_type character varying, content text, msg_timestamp timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.message_type,
        cm.content,
        cm.timestamp
    FROM chat_messages cm
    WHERE cm.session_id = p_session_id
    ORDER BY cm.timestamp DESC
    LIMIT p_limit;
END;
$$;


ALTER FUNCTION public.get_conversation_history(p_session_id character varying, p_limit integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: campaign_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.campaign_state (
    id integer NOT NULL,
    session_id character varying(255),
    current_act integer DEFAULT 1,
    current_scene integer DEFAULT 1,
    location character varying(255),
    plot_flags jsonb DEFAULT '{}'::jsonb,
    npc_relationships jsonb DEFAULT '{}'::jsonb,
    active_plot_threads jsonb DEFAULT '[]'::jsonb,
    player_inventory jsonb DEFAULT '[]'::jsonb,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.campaign_state OWNER TO postgres;

--
-- Name: campaign_state_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.campaign_state_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.campaign_state_id_seq OWNER TO postgres;

--
-- Name: campaign_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.campaign_state_id_seq OWNED BY public.campaign_state.id;


--
-- Name: campaigns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.campaigns (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    file_path character varying(500) NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    last_played timestamp without time zone,
    is_active boolean DEFAULT true
);


ALTER TABLE public.campaigns OWNER TO postgres;

--
-- Name: campaigns_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.campaigns_id_seq OWNER TO postgres;

--
-- Name: campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.campaigns_id_seq OWNED BY public.campaigns.id;


--
-- Name: characters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.characters (
    id integer NOT NULL,
    session_id character varying(255),
    name character varying(255) NOT NULL,
    class character varying(100),
    level integer DEFAULT 1,
    stats jsonb DEFAULT '{}'::jsonb,
    skills jsonb DEFAULT '{}'::jsonb,
    equipment jsonb DEFAULT '[]'::jsonb,
    backstory text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.characters OWNER TO postgres;

--
-- Name: characters_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.characters_id_seq OWNER TO postgres;

--
-- Name: characters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.characters_id_seq OWNED BY public.characters.id;


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    id integer NOT NULL,
    session_id character varying(255),
    message_type character varying(20) NOT NULL,
    content text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now(),
    metadata jsonb
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_messages_id_seq OWNER TO postgres;

--
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_sessions (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    campaign_id integer,
    player_name character varying(255) DEFAULT 'Player'::character varying,
    started_at timestamp without time zone DEFAULT now(),
    last_activity timestamp without time zone DEFAULT now(),
    is_active boolean DEFAULT true
);


ALTER TABLE public.chat_sessions OWNER TO postgres;

--
-- Name: chat_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_sessions_id_seq OWNER TO postgres;

--
-- Name: chat_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_sessions_id_seq OWNED BY public.chat_sessions.id;


--
-- Name: dnd_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dnd_rules (
    id bigint NOT NULL,
    text character varying NOT NULL,
    metadata_ jsonb,
    node_id character varying,
    embedding public.vector(384),
    source_type character varying(50) DEFAULT 'srd'::character varying,
    rule_category character varying(100)
);


ALTER TABLE public.dnd_rules OWNER TO postgres;

--
-- Name: dnd_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dnd_rules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dnd_rules_id_seq OWNER TO postgres;

--
-- Name: dnd_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dnd_rules_id_seq OWNED BY public.dnd_rules.id;


--
-- Name: campaign_state id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaign_state ALTER COLUMN id SET DEFAULT nextval('public.campaign_state_id_seq'::regclass);


--
-- Name: campaigns id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaigns ALTER COLUMN id SET DEFAULT nextval('public.campaigns_id_seq'::regclass);


--
-- Name: characters id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.characters ALTER COLUMN id SET DEFAULT nextval('public.characters_id_seq'::regclass);


--
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- Name: chat_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions ALTER COLUMN id SET DEFAULT nextval('public.chat_sessions_id_seq'::regclass);


--
-- Name: dnd_rules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dnd_rules ALTER COLUMN id SET DEFAULT nextval('public.dnd_rules_id_seq'::regclass);


--
-- Data for Name: campaign_state; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.campaign_state (id, session_id, current_act, current_scene, location, plot_flags, npc_relationships, active_plot_threads, player_inventory, updated_at) FROM stdin;
\.


--
-- Data for Name: campaigns; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.campaigns (id, name, display_name, description, file_path, created_at, last_played, is_active) FROM stdin;
1	crimson_conspiracy.md	The Crimson Conspiracy	A tale of political intrigue in the city	dnd_src_material/custom_campaigns/crimson_conspiracy.md	2025-09-15 16:29:56.434341	\N	t
\.


--
-- Data for Name: characters; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.characters (id, session_id, name, class, level, stats, skills, equipment, backstory, created_at) FROM stdin;
\.


--
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_messages (id, session_id, message_type, content, "timestamp", metadata) FROM stdin;
\.


--
-- Data for Name: chat_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_sessions (id, session_id, campaign_id, player_name, started_at, last_activity, is_active) FROM stdin;
\.


--
-- Data for Name: dnd_rules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dnd_rules (id, text, metadata_, node_id, embedding, source_type, rule_category) FROM stdin;
\.


--
-- Name: campaign_state_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.campaign_state_id_seq', 1, false);


--
-- Name: campaigns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.campaigns_id_seq', 1, true);


--
-- Name: characters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.characters_id_seq', 1, false);


--
-- Name: chat_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_messages_id_seq', 1, false);


--
-- Name: chat_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_sessions_id_seq', 1, false);


--
-- Name: dnd_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dnd_rules_id_seq', 1, false);


--
-- Name: campaign_state campaign_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaign_state
    ADD CONSTRAINT campaign_state_pkey PRIMARY KEY (id);


--
-- Name: campaigns campaigns_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_name_key UNIQUE (name);


--
-- Name: campaigns campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id);


--
-- Name: characters characters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.characters
    ADD CONSTRAINT characters_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_session_id_key UNIQUE (session_id);


--
-- Name: dnd_rules dnd_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dnd_rules
    ADD CONSTRAINT dnd_rules_pkey PRIMARY KEY (id);


--
-- Name: idx_chat_messages_session_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_session_time ON public.chat_messages USING btree (session_id, "timestamp");


--
-- Name: idx_dnd_rules_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dnd_rules_category ON public.dnd_rules USING btree (rule_category);


--
-- Name: idx_dnd_rules_embedding; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dnd_rules_embedding ON public.dnd_rules USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_dnd_rules_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dnd_rules_source ON public.dnd_rules USING btree (source_type);


--
-- Name: campaign_state campaign_state_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campaign_state
    ADD CONSTRAINT campaign_state_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(session_id);


--
-- Name: characters characters_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.characters
    ADD CONSTRAINT characters_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(session_id);


--
-- Name: chat_messages chat_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(session_id);


--
-- Name: chat_sessions chat_sessions_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 6PZW2vsBYxGwDLIixpn8hZuoaVySNzk9O9z8mvmL48O0mCCchf9y8ZRk5MfB8ge

