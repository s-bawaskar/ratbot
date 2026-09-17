-- RATBOT database schema
-- Static content (rat species, achievement definitions) lives in data/*.json, not here.
-- These tables only hold player state.

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name TEXT,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT true,
    spawn_min_s INT NOT NULL DEFAULT 600,
    spawn_max_s INT NOT NULL DEFAULT 3600,
    next_spawn_at TIMESTAMPTZ,
    current_spawn_msg_id BIGINT,
    current_rat_key TEXT,
    current_spawn_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS wallets (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    modaks BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS user_rats (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    rat_key TEXT NOT NULL,
    count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, rat_key)
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    delta BIGINT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cooldowns (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    command_key TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, guild_id, command_key)
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, guild_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS festival_progress (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    pujas_done INT NOT NULL DEFAULT 0,
    aartis_done INT NOT NULL DEFAULT 0,
    prasad_collected INT NOT NULL DEFAULT 0,
    festival_xp INT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS catches (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    rat_key TEXT NOT NULL,
    catch_seconds REAL NOT NULL,
    caught_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_channels_due_spawn ON channels (next_spawn_at) WHERE enabled AND current_spawn_msg_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_catches_guild_speed ON catches (guild_id, catch_seconds);
CREATE INDEX IF NOT EXISTS idx_wallets_guild_modaks ON wallets (guild_id, modaks DESC);
CREATE INDEX IF NOT EXISTS idx_user_rats_guild_user ON user_rats (guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_festival_guild_xp ON festival_progress (guild_id, festival_xp DESC);
