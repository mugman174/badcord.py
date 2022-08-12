"""
discord.py 1.7.3 monkeypatching
"""


import config

from discord import *
import discord, json, datetime, re, sys
from typing import *
from discord.ext import commands


async def get_gateway(self, *, encoding="json", v=6, zlib=True):
    try:
        data = await self.request(discord.http.Route("GET", "/gateway"))
    except discord.HTTPException as exc:
        raise GatewayNotFound() from exc
    data = json.loads(data)
    value = "{0}?encoding={1}&v={2}"
    return value.format(data["url"], encoding, v)


def _get_as_snowflake(data, key):
    try:
        value = data[key]
    except (KeyError, TypeError):
        return {}
    else:
        return value and int(value)


def roleTags(self, data, **kwargs):
    data = data or {}
    self.bot_id = _get_as_snowflake(data, "bot_id")
    self.integration_id = _get_as_snowflake(data, "integration_id")
    self._premium_subscriber = data.get("premium_subscriber", ...)


def guild_sync(self, data):
    try:
        self._large = data["large"]
    except KeyError:
        pass

    empty_tuple = tuple()
    for presence in data.get("presences", []):
        user_id = int(presence["user"]["id"])
        member = self.get_member(user_id)
        if member is not None:
            member._presence_update(presence, empty_tuple)

    if "channels" in data:
        channels = data["channels"]
        for c in channels:
            factory, ch_type = _channel_factory(c["type"])
            if factory:
                try:
                    self._add_channel(factory(guild=self, data=c, state=self._state))
                except TypeError:
                    pass


def parse_message_create(self, data):
    data["edited_timestamp"] = data.get("edited_timestamp")
    channel, _ = self._get_guild_channel(data)
    message = discord.Message(channel=channel, data=data, state=self)
    self.dispatch("message", message)
    if self._messages is not None:
        self._messages.append(message)
    if channel and channel.__class__ is discord.TextChannel:
        channel.last_message_id = message.id


def send_message(
    self,
    channel_id,
    content,
    *,
    tts=False,
    embed=None,
    nonce=None,
    allowed_mentions=None,
    message_reference=None
):
    channel_id = str(channel_id)
    r = discord.http.Route(
        "POST", "/channels/{channel_id}/messages", channel_id=channel_id
    )
    payload = {}

    if content:
        payload["content"] = content

    if tts:
        payload["tts"] = True
    else:
        payload["tts"] = False
    if embed:
        payload["embed"] = embed

    if nonce:
        payload["nonce"] = nonce

    if allowed_mentions:
        payload["allowed_mentions"] = allowed_mentions

    if message_reference:
        message_reference["guild_id"] = str(message_reference["guild_id"])
        message_reference["channel_id"] = str(message_reference["channel_id"])
        message_reference["guild_id"] = str(message_reference["guild_id"])
        payload["message_reference"] = message_reference
    return self.request(r, json=payload)


def create_message(self, *, channel, data):
    data = json.loads(data)
    return discord.Message(state=self, channel=channel, data=data)


def _Overwrites_init(self, **kwargs):
    self.id = kwargs.pop("id")
    self.allow = int(kwargs.pop("allow_new", 0))
    self.deny = int(kwargs.pop("deny_new", 0))
    self.type = sys.intern(str(kwargs.pop("type")))


# def clean_prefix(self):
# 	return "!"
clean_prefix = "!"


def with_state(self, data, *_, **__):  # state, data):
    if not data:
        return
    message_id = utils._get_as_snowflake(data, "message_id")
    channel_id = int(data.pop("channel_id"))
    guild_id = discord.utils._get_as_snowflake(data, "guild_id")
    fail_if_not_exists = data.get("fail_if_not_exists", True)
    return MessageReference(
        message_id=message_id,
        channel_id=channel_id,
        guild_id=guild_id,
        fail_if_not_exists=fail_if_not_exists,
    )


def parse_time(timestamp):
    try:
        if timestamp:
            if timestamp.isnumeral():
                timestamp = str(int(timestamp) / 1000)
            return datetime.datetime(
                *map(
                    int,
                    [
                        i
                        for i in re.split(r"[^\d]", timestamp.replace("+00:00", ""))
                        if i
                    ],
                )
            )
    except Exception:
        pass
    return None


def parse_typing_start(self, data):
    channel, guild = self._get_guild_channel(data)
    if channel is not None:
        member = None
        user_id = utils._get_as_snowflake(data, "user_id")
        if isinstance(channel, DMChannel):
            member = channel.recipient
        elif isinstance(channel, TextChannel) and guild is not None:
            member = guild.get_member(user_id)
            if member is None:
                member_data = data.get("member")
                if member_data:
                    member = Member(data=member_data, state=self, guild=guild)

        elif isinstance(channel, GroupChannel):
            member = utils.find(lambda x: x.id == user_id, channel.recipients)

        if member is not None:
            timestamp = data.get("timestamp") / 1000
            timestamp = datetime.datetime.utcfromtimestamp(timestamp)
            self.dispatch("typing", channel, member, timestamp)


def _get_guild(self, guild_id):
    if not guild_id:
        return
    return self._guilds.get(guild_id)


discord.state.ConnectionState._get_guild = _get_guild
discord.state.ConnectionState.parse_typing_start = parse_typing_start
discord.utils.parse_time = parse_time
discord.message.MessageReference.with_state = with_state
commands.HelpCommand.clean_prefix = clean_prefix
discord.state.ConnectionState.create_message = create_message
discord.http.HTTPClient.send_message = send_message
discord.state.ConnectionState.parse_message_create = parse_message_create
discord.http.HTTPClient.get_gateway = get_gateway
discord.utils._get_as_snowflake = _get_as_snowflake
discord.role.RoleTags.__init__ = roleTags
discord.abc._Overwrites.__init__ = _Overwrites_init
