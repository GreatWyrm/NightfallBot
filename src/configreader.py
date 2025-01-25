class ConfigReader:
    def __init__(self, bot_config):
        self.host = str(bot_config['host'])
        self.port = int(bot_config['port'])
        self.bot_updates_channel_id = int(bot_config['update_channel_id'])
        self.bot_ping_channel_id = bot_config['ping-channel']
        self.bot_reports_guild_id = int(bot_config['report-guild'])
        self.bot_unban_channel_id = int(bot_config['unban-channel'])
        self.bot_unban_internal_reason = str(bot_config['unban-internal-reason'])
        self.update_frequency = float(bot_config['update_frequency'])
        self.role_id = int(bot_config['ping-role-id'])
        self.role_ping_cooldown_seconds = int(bot_config['ping-cooldown-seconds'])
        self.role_ping_manual_cooldown_seconds = int(bot_config['manual-cooldown-seconds'])
        self.min_players_ping_threshold = int(bot_config['min-players-threshold'])
        self.embed_colors = list(bot_config['embed-colors'])

        if self.update_frequency < 0.1:
            print("Update Frequency is too low (below 0.1)! Setting to 0.1...")
            self.update_frequency = 0.1
