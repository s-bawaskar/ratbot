import db


class Guild(db.Model):
    _table = "guilds"
    _pk = ("guild_id",)


class Channel(db.Model):
    _table = "channels"
    _pk = ("channel_id",)


class Wallet(db.Model):
    _table = "wallets"
    _pk = ("user_id", "guild_id")


class UserRat(db.Model):
    _table = "user_rats"
    _pk = ("user_id", "guild_id", "rat_key")


class Transaction(db.Model):
    _table = "transactions"
    _pk = ("id",)


class Cooldown(db.Model):
    _table = "cooldowns"
    _pk = ("user_id", "guild_id", "command_key")


class UserAchievement(db.Model):
    _table = "user_achievements"
    _pk = ("user_id", "guild_id", "achievement_key")


class FestivalProgress(db.Model):
    _table = "festival_progress"
    _pk = ("user_id", "guild_id")
