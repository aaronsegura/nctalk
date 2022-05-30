## Nextcloud Talk Client Module
######

This project is not endorsed or officially recognized in
any way by the NextCloud project.

https://nextcloud-talk.readthedocs.io/en/latest/

Example:

    >>> nct = NextCloudTalk(endpoint=endpoint, user=user, password=password)
    >>> nct.capabilities
    ['audio', 'video', 'chat-v2', 'conversation-v4', 'guest-signaling', 'empty-group-room',
    'guest-display-names', 'multi-room-users', 'favorites', 'last-room-activity', 'no-ping',
    'system-messages', 'delete-messages', 'mention-flag', 'in-call-flags',
    'conversation-call-flags', 'notification-levels', 'invite-groups-and-mails',
    'locked-one-to-one-rooms', 'read-only-rooms', 'listable-rooms', 'chat-read-marker',
    'webinary-lobby', 'start-call-flag', 'chat-replies', 'circles-support', 'force-mute',
    'sip-support', 'chat-read-status', 'phonebook-search', 'raise-hand', 'room-description',
    'rich-object-sharing', 'temp-user-avatar-api', 'geo-location-sharing',
    'voice-message-sharing', 'signaling-v3', 'publishing-permissions', 'clear-history',
    'direct-mention-flag', 'notification-calls', 'conversation-permissions',
    'chat-reference-id']
    >>> conversations = nct.conversation_list()
    >>> for c in conversations:
    ...   print(c.token, c.displayName, c.description)
    ...
    23pw7aud Work Chat None
    jit4tk78 Family Chat None
    6rsa4brg Talk updates ✅ None
    3vkymk5m Test public room None
    >>> message = conversation[0].send(message='hello')
    >>> print(message['id'])
    '4387'

Alternatively, log in with HTTPBasicAuth:

    >>> auth = HTTPBasicAuth('user', 'password')
    >>> nct = NextCloudTalk(endpoint=endpoint, auth=auth)
