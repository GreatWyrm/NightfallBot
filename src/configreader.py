host = ""
port = 00000
admin_guild_id = 00000
bot_updates_channel_id = 00000
bot_ping_channel_id = 00000
bot_reports_guild_id = 00000
bot_issue_channel_id = 00000
bot_issue_internal_reason = ""
bot_bug_channel_id = 00000
bot_bug_internal_reason = ""
bot_unban_channel_id = 00000
bot_unban_internal_reason = ""
bot_valid_thread_ids = list()
update_frequency = 0.0
role_id = 00000
role_ping_cooldown_seconds = 00000
role_ping_manual_cooldown_seconds = 00000
min_players_ping_threshold = 00000
embed_colors = list()
def readconfig(bot_config):
    global host
    global port
    global admin_guild_id
    global bot_updates_channel_id
    global bot_ping_channel_id
    global bot_reports_guild_id
    global bot_issue_channel_id
    global bot_issue_internal_reason
    global bot_bug_channel_id
    global bot_bug_internal_reason
    global bot_unban_channel_id
    global bot_unban_internal_reason
    global bot_valid_thread_ids
    global update_frequency
    global role_id
    global role_ping_cooldown_seconds
    global role_ping_manual_cooldown_seconds
    global min_players_ping_threshold
    global embed_colors

    host = str(bot_config['host'])
    port = int(bot_config['port'])
    admin_guild_id = int(bot_config['admin-guild-id'])
    bot_updates_channel_id = int(bot_config['update_channel_id'])
    bot_ping_channel_id = bot_config['ping-channel']
    bot_reports_guild_id = int(bot_config['report-guild'])
    bot_issue_channel_id = int(bot_config['issue-channel'])
    bot_issue_internal_reason = str(bot_config['issue-internal-reason'])
    bot_bug_channel_id = int(bot_config['bug-channel'])
    bot_bug_internal_reason = str(bot_config['bug-internal-reason'])
    bot_unban_channel_id = int(bot_config['unban-channel'])
    bot_unban_internal_reason = str(bot_config['unban-internal-reason'])
    update_frequency = float(bot_config['update_frequency'])
    role_id = int(bot_config['ping-role-id'])
    role_ping_cooldown_seconds = int(bot_config['ping-cooldown-seconds'])
    role_ping_manual_cooldown_seconds = int(bot_config['manual-cooldown-seconds'])
    min_players_ping_threshold = int(bot_config['min-players-threshold'])
    embed_colors = list(bot_config['embed-colors'])

    bot_valid_thread_ids.append(bot_bug_channel_id)
    bot_valid_thread_ids.append(bot_unban_channel_id)
    bot_valid_thread_ids.append(bot_valid_thread_ids)

    if update_frequency < 0.1:
        print("Update Frequency is too low (below 0.1)! Setting to 0.1...")
        update_frequency = 0.1
