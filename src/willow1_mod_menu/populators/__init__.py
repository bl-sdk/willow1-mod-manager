from abc import ABC, abstractmethod

from unrealsdk.unreal import UObject

type WillowGFxLobbyTools = UObject


class Populator(ABC):
    @abstractmethod
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        """
        Populates the menu with the appropriate contents.

        Args:
            tools: The lobby tools which may be used to add to the menu.
        """
        raise NotImplementedError
