"""
discord.py 1.7.3 monkeypatching
"""

from discord import *
import discord
import datetime
import sys
from typing import *
from discord.ext import commands


async def get_gateway(self, *, encoding="json", v=6, zlib=True):
    try:
        data = await self.request(discord.http.Route("GET", "/gateway"))
    except discord.HTTPException as exc:
        raise GatewayNotFound() from exc
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
    data["pinned"] = data.get("pinned")
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
    message_reference=None,
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
        payload["message_reference"] = {
            key: str(value) for key, value in message_reference.items()
        }
    return self.request(r, json=payload)


def create_message(self, *, channel, data):
    return discord.Message(state=self, channel=channel, data=data)


def _Overwrites_init(self, **kwargs):
    self.id = kwargs.pop("id")
    self.allow = int(kwargs.pop("allow_new", 0))
    self.deny = int(kwargs.pop("deny_new", 0))
    self.type = sys.intern(str(kwargs.pop("type")))

#def _Overwrites_init(self, **data) -> None:
#    self.id: int = int(data['id'])
#    self.allow: int = int(data.get('allow', 0))
#    self.deny: int = int(data.get('deny', 0))
#    self.type: OverwriteType = data['type']



clean_prefix = "!"


def with_state(self, data, *_, **__):
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
    if timestamp:
        return datetime.datetime.fromisoformat(timestamp)
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


def Invite__init__(self, *, state, data):
    self._state = state
    self.max_age = data.get("max_age")
    self.code = data.get("code")
    self.guild = data.get("guild")
    self.revoked = data.get("revoked")
    self.created_at = parse_time(data.get("created_at"))
    self.temporary = data.get("temporary")
    self.uses = data.get("uses")
    self.max_uses = data.get("max_uses")
    self.approximate_presence_count = data.get("approximate_presence_count")
    self.approximate_member_count = data.get("approximate_member_count")

    inviter_data = data.get("inviter")
    self.inviter = (
        None if inviter_data is None else self._state.store_user(inviter_data)
    )
    self.channel = data.get("channel")

def edit_channel_permissions(self, channel_id, target, allow, deny, type, *, reason=None):
    payload = {
        'id': str(target),
        'allow': allow,
        'deny': deny,
        'type': ["role","member"].index(type)
    }
    r = discord.http.Route('PUT', '/channels/{channel_id}/permissions/{target}', channel_id=channel_id, target=target)
    return self.request(r, json=payload, reason=reason)

def TextChannel_update(self, guild, data):
    self.guild = guild
    self.name = data['name']
    self.category_id = utils._get_as_snowflake(data, 'parent_id')
    self.topic = data.get('topic')
    self.position = data.get('position', getattr(self, "position", None))
    self.nsfw = data.get('nsfw', False)
    # Does this need coercion into `int`? No idea yet.
    self.slowmode_delay = data.get('rate_limit_per_user', 0)
    self._type = data.get('type', self._type)
    self.last_message_id = utils._get_as_snowflake(data, 'last_message_id')
    self._fill_overwrites(data)


discord.state.ConnectionState._get_guild = _get_guild
discord.state.ConnectionState.parse_typing_start = parse_typing_start
discord.utils.parse_time = parse_time
commands.HelpCommand.clean_prefix = clean_prefix
discord.state.ConnectionState.create_message = create_message
discord.http.HTTPClient.send_message = send_message
discord.state.ConnectionState.parse_message_create = parse_message_create
discord.http.HTTPClient.get_gateway = get_gateway
discord.utils._get_as_snowflake = _get_as_snowflake
discord.role.RoleTags.__init__ = roleTags
discord.abc._Overwrites.__init__ = _Overwrites_init
discord.invite.Invite.__init__ = Invite__init__
discord.http.HTTPClient.edit_channel_permissions = edit_channel_permissions
discord.channel.TextChannel._update = TextChannel_update
