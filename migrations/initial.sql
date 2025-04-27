-- migrations/initial.sql
CREATE TABLE IF NOT EXISTS guild_settings (
  guild_id TEXT PRIMARY KEY,
  channel_id TEXT NOT NULL,
  alert_battle BOOLEAN NOT NULL DEFAULT 1,
  alert_application BOOLEAN NOT NULL DEFAULT 1,
  alert_raffle BOOLEAN NOT NULL DEFAULT 1
);