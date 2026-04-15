import copy

from models.errors import MessageNotSuccessfulError


class BatchFilenameToEventsMapper:
    FILENAME_NOT_PRESENT_ERROR_MSG = "Filename data was not present"

    def __init__(self):
        self._filename_to_events_map: dict[str, list[dict]] = {}

    def add_event(self, event: dict) -> None:
        filename_key = self._make_key(event)

        if filename_key not in self._filename_to_events_map:
            self._filename_to_events_map[filename_key] = [event]
            return

        self._filename_to_events_map[filename_key].append(event)

    def get_map(self) -> dict[str, list[dict]]:
        return copy.deepcopy(self._filename_to_events_map)

    def _make_key(self, event: dict) -> str:
        file_key = event.get("file_key")
        created_at_string = event.get("created_at_formatted_string")

        if not file_key or not created_at_string:
            raise MessageNotSuccessfulError(self.FILENAME_NOT_PRESENT_ERROR_MSG)

        return f"{file_key}_{created_at_string}"
