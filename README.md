# 🐀 RATBOT

A Discord bot game built around Ganesh Chaturthi. Wild "Mushaks" (rats — the vehicle of Ganesha) spawn
in channels you set up; the first person to type `rat` catches them. Catch rats to earn "Modaks"
(the in-server currency), build up a collection, unlock achievements, and take part in daily
festival rituals (Puja, Aarti, Prasad).

## Features

- **Catching** — Mushaks spawn on a random timer per channel; typing the trigger word claims one.
  Catch speed, rarity, and species are all tracked.
- **Economy** — Modaks earned from catches, `/daily` claims, and festival activities.
- **Collection** — species dex, per-user inventory, and collection-completion tracking across nine
  rarity tiers (common → secret).
- **Achievements** — unlockable achievements based on catches, speed, and progress.
- **Leaderboards** — richest, most Mushaks, best collection, most devout, fastest/slowest catch,
  and per-species rankings.
- **Festival mini-game** — `/puja`, `/aarti`, and `/prasad`, each on their own cooldown, for bonus
  Modaks and Festival XP.
- **Per-server data** — all progress (wallet, rats, achievements, festival state) is scoped to the
  guild it was earned in.

## Commands

| Command | Description |
|---|---|
| `/help` | How to play |
| `/contactgod` | Reach the bot owner |
| `/daily` | Claim daily Modaks |
| `/balance` | Check your Modak balance |
| `/profile [user]` | View a profile summary |
| `/inventory` | List your caught Mushaks |
| `/collection` | Collection progress by rarity |
| `/dex` | Browse every known Mushak species |
| `/achievements` | View your unlocked achievements |
| `/leaderboard [category] [rat]` | Server rankings |
| `/puja`, `/aarti`, `/prasad` | Festival rituals (Modaks + XP, own cooldowns) |
| `/festival` | Your festival progress |
| `/setup`, `/unsetup` | (Admin) enable/disable spawns in a channel |
| `/forcespawn [rarity] [rat]` | (Admin) force an immediate spawn |
| `/changetimings <min> <max>` | (Admin) adjust spawn frequency |
| `/ownergive`, `/ownergiverat` | (Owner) grant Modaks or a specific Mushak |

Admin commands require the "Manage Server" permission (or the bot owner). Owner commands are
restricted to a single hardcoded Discord user ID.

## Requirements

- Python 3.11+
- A PostgreSQL database (developed against [Neon](https://neon.tech))
- A Discord bot application/token with the **Message Content** intent enabled

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create the database schema:
   ```
   psql "$DATABASE_URL" -f schema.sql
   ```
3. Create a `.env` file in the project root:
   ```
   DISCORD_TOKEN=your-bot-token
   DATABASE_URL=postgresql://user:password@host/dbname
   ```
4. Set your Discord user ID as the bot owner in [config.py](config.py) (`OWNER_ID`).
5. Run the bot:
   ```
   python bot.py
   ```

On first run the bot syncs slash commands to every guild it's already in; it syncs automatically to
any guild it joins afterward.

## Project layout

- [bot.py](bot.py) — entry point, command sync, error handling
- [cogs/](cogs/) — one cog per feature (catch, wallet, profile, achievements, leaderboard, festival, help, owner)
- [rats.py](rats.py) / [data/rats.json](data/rats.json) — Mushak species definitions and spawn logic
- [achievements_engine.py](achievements_engine.py) / [data/achievements.json](data/achievements.json) — achievement definitions and unlock checks
- [economy.py](economy.py) — wallet/transaction helpers
- [db.py](db.py) / [database.py](database.py) — thin asyncpg wrapper and per-table models
- [permissions.py](permissions.py) — owner/admin permission checks
- [schema.sql](schema.sql) — Postgres schema
- [docs/](docs/) — hosted Privacy Policy and Terms of Service pages (required for Discord bot verification)

## License

MIT — see [LICENSE](LICENSE). [db.py](db.py) additionally carries its own attribution header for
code adapted from another MIT-licensed project (catpg).
