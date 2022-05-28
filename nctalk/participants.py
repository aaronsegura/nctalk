"""Participants API."""

class Participant(object):
    """A conversation participant."""

    def __init__(self, data: dict):
        self.__dict__.update(data)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'Participant({self.actorId}, {self.displayName})'  # type: ignore
