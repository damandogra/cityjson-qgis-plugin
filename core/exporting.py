"""Writes QGIS layers back out as CityJSON."""

import json


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
        # Approach 2 (patch) - start from the original, change only what differs.
            # copy self.citymodel
            # diff self.layers against it
            # apply only the deletions / geometry edits / attribute edits
            # return the patched copy
        raise NotImplementedError

    def get_surviving_ids(self):
        uids = set() # set helps us avoid duplicates
        for layer in self.layers:
            for feature in layer.getFeatures():
                uid = feature["uid"]
                uids.add(uid)

        # a surviving child with a deleted parent is a dangling reference; a deleted child creates no such problem, so it stays deleted.
        for uid in list(uids):
            obj = self.citymodel["CityObjects"][uid]

            if "parents" in obj:
                for parent in obj["parents"]: # iterate through the parents
                    uids.add(parent) # add the parent to the set of surviving ids
                
        return uids


def save_cityjson_model(citymodel: dict, filepath: str) -> None:
    """Save a CityJSON model dictionary to a file."""
    with open(filepath, "w", encoding="utf-8", buffering=8192) as fstream:
        content=(json.dumps(citymodel))
        fstream.write(content)