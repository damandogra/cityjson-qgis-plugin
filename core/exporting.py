"""Writes QGIS layers back out as CityJSON."""

class CityJSONExporter:
    """Rebuilds a CityJSON model from QGIS layers."""

    def __init__(self, layers, citymodel=None):
        self.layers = layers
        self.citymodel = citymodel

    def export(self) -> dict: # returns a dictionary representing the CityJSON model
        """Export the configured layers as a CityJSON model dictionary."""
        # Approach 1 - ignore the original, rebuild from the table.
            # read self.layers, build vertices + CityObjects from scratch
            # self.citymodel only used for transform / version / metadata
        # Approach 2 (patch) - start from the original, change only what differs."""
            # copy self.citymodel
            # diff self.layers against it
            # apply only the deletions / geometry edits / attribute edits
            # return the patched copy
        raise NotImplementedError


def save_cityjson_model(citymodel: dict, filepath: str) -> None:
    """Save a CityJSON model dictionary to a file."""
    raise NotImplementedError