-- Essays: основные тексты эссе
CREATE TABLE IF NOT EXISTS essays (
    id           SERIAL PRIMARY KEY,
    external_id  VARCHAR(50),
    source       VARCHAR(50)  NOT NULL DEFAULT 'persuade',
    prompt_id    INTEGER,
    essay_text   TEXT         NOT NULL,
    word_count   INTEGER      NOT NULL DEFAULT 0,
    language     VARCHAR(10)  NOT NULL DEFAULT 'en',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_essays_source    ON essays (source);
CREATE INDEX IF NOT EXISTS idx_essays_prompt_id ON essays (prompt_id);


-- Expert scores: оценки экспертов из датасета PERSUADE
CREATE TABLE IF NOT EXISTS expert_scores (
    id               SERIAL PRIMARY KEY,
    essay_id         INTEGER     NOT NULL REFERENCES essays (id) ON DELETE CASCADE,
    score_raw        FLOAT       NOT NULL,
    score_normalized FLOAT       NOT NULL,
    score_arg        INTEGER,
    score_evidence   INTEGER,
    score_logic      INTEGER,
    score_perspective INTEGER,
    score_metacog    INTEGER,
    source           VARCHAR(50) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- LLM scores: оценки от LLM агентов через n8n
CREATE TABLE IF NOT EXISTS llm_scores (
    id                  SERIAL PRIMARY KEY,
    essay_id            INTEGER      NOT NULL REFERENCES essays (id) ON DELETE CASCADE,
    job_id              VARCHAR(100),
    model_name          VARCHAR(100) NOT NULL DEFAULT 'gptoss-120b',
    score_arg           INTEGER,
    score_evidence      INTEGER,
    score_logic         INTEGER,
    score_perspective   INTEGER,
    score_metacog       INTEGER,
    score_composite     FLOAT,
    reasoning           TEXT,
    arg_structure       JSONB,
    detected_fallacies  JSONB,
    processing_time_ms  INTEGER,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- LLM feedback: обратная связь студенту от FeedbackAgent
CREATE TABLE IF NOT EXISTS llm_feedback (
    id                SERIAL PRIMARY KEY,
    essay_id          INTEGER     NOT NULL REFERENCES essays (id)     ON DELETE CASCADE,
    llm_score_id      INTEGER     NOT NULL REFERENCES llm_scores (id) ON DELETE CASCADE,
    feedback_text     TEXT        NOT NULL,
    weakest_dimension VARCHAR(50),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- NLP features: признаки извлечённые Python скриптом
CREATE TABLE IF NOT EXISTS nlp_features (
    id                  SERIAL PRIMARY KEY,
    essay_id            INTEGER     NOT NULL REFERENCES essays (id) ON DELETE CASCADE,
    -- Аргументативная структура
    arg_claim_count     INTEGER     NOT NULL DEFAULT 0,
    arg_evidence_count  INTEGER     NOT NULL DEFAULT 0,
    arg_warrant_count   INTEGER     NOT NULL DEFAULT 0,
    arg_counter_count   INTEGER     NOT NULL DEFAULT 0,
    arg_coverage        FLOAT       NOT NULL DEFAULT 0,
    -- Логические ошибки
    fallacy_total       INTEGER     NOT NULL DEFAULT 0,
    fallacy_authority   INTEGER     NOT NULL DEFAULT 0,
    fallacy_generalize  INTEGER     NOT NULL DEFAULT 0,
    fallacy_dichotomy   INTEGER     NOT NULL DEFAULT 0,
    fallacy_circular    INTEGER     NOT NULL DEFAULT 0,
    -- Дискурсивная связность
    sentence_count      INTEGER     NOT NULL DEFAULT 0,
    avg_sent_length     FLOAT       NOT NULL DEFAULT 0,
    transition_density  FLOAT       NOT NULL DEFAULT 0,
    -- Лексическая сложность
    type_token_ratio    FLOAT       NOT NULL DEFAULT 0,
    subordination_idx   FLOAT       NOT NULL DEFAULT 0,
    -- Метакогниция
    metacognitive_count INTEGER     NOT NULL DEFAULT 0,
    has_counter_arg     BOOLEAN     NOT NULL DEFAULT FALSE,
    -- Интегральный индекс
    aqi                 FLOAT       NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Validation results: итоговые метрики валидации LLM vs эксперт
CREATE TABLE IF NOT EXISTS validation_results (
    id          SERIAL PRIMARY KEY,
    run_id      VARCHAR(100) UNIQUE NOT NULL,
    n_essays    INTEGER      NOT NULL,
    pearson_r   FLOAT,
    spearman_rho FLOAT,
    qwk         FLOAT,
    bias_mean   FLOAT,
    loa_upper   FLOAT,
    loa_lower   FLOAT,
    rf_r2       FLOAT,
    gb_r2       FLOAT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
