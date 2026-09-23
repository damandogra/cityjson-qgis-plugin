"""Writes QGIS layers back out as CityJSON."""

import json
import copy
from .utils import createCityJSON
from . import subset
from .layers import _stringify_attribute


class CityJSONExporter:
    """Rebuilds a CityJSON model from QGIS layers."""

    def __init__(self, layers, citymodel=None):
        self.layers = layers
        self.citymodel = citymodel

    def export(self) -> dict: # returns a dictionary representing the CityJSON model
        """
        Export the configured layers as a CityJSON model dictionary.
        1. Create a new CityJSON model with the same version and transform as the original.
        2. get the surviving IDs from the layers.
        3. For each surviving ID, copy the corresponding CityObject from the original model to the new model.
        4. Rebuild the vertices array from the surviving CityObjects, and update array indices.
        """
        new_cm = createCityJSON()
        new_cm["version"] = self.citymodel["version"] # copy version
        if "transform" in self.citymodel: # copy transform if it exists
            new_cm["transform"] = self.citymodel["transform"]

        surviving_ids = self.get_surviving_ids()
        for uid in self.citymodel["CityObjects"]: # copy the CityObject to the new model, if it exists in the surviving IDs
            if uid in surviving_ids:
                new_cm["CityObjects"][uid] = copy.deepcopy(self.citymodel["CityObjects"][uid]) # copy the CityObject to the new model

        # apply the attribute edits to the copied model, so that the new model has the same attributes as the original model, except for the edits made in QGIS
        self.apply_attribute_edits(new_cm)


        # rebuild the vertices array from the surviving CityObjects, and update array indices
        subset.process_geometry(self.citymodel, new_cm)
        if "appearance" in self.citymodel: # copy appearance if it exists
            subset.process_appearance(self.citymodel, new_cm)
        if "metadata" in self.citymodel: # copy metadata if it exists
            new_cm["metadata"] = self.citymodel["metadata"]
        if "geometry-templates" in self.citymodel: # copy geometry-templates if it exists
            subset.process_templates(self.citymodel, new_cm)
        # prune dangling children from the new model
        self.prune_dangling_children(new_cm, surviving_ids)
        return new_cm

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

    def prune_dangling_children(self, citymodel, surviving_ids):
        """Remove any CityObjects children from the parent parts"""
        for obj in citymodel["CityObjects"].values():
            if "children" in obj:
                obj["children"] = [child for child in obj["children"] if child in surviving_ids]
                if not obj["children"]:
                    del obj["children"]

    def apply_attribute_edits(self, new_cm):
        """Apply the attribute edits from the QGIS layers to the new CityJSON model."""
        for layer in self.layers:
            for feature in layer.getFeatures():
                uid = feature["uid"]
                obj = new_cm["CityObjects"][uid]
                if uid in new_cm["CityObjects"]:
                    for i in layer.fields():
                        if i.name().startswith("attribute."): # only consider fields that start with "attribute."
                            old_attribute_value = obj.get("attributes", {}).get(i.name()[10:], None) # [i.name()[10:]] cuts of the first 10 characters
                            expected_values_for_old_attribute = _stringify_attribute(old_attribute_value) # get the expected values for the old attribute value
                            new_attribute_value = feature[i.name()]
                            if new_attribute_value != expected_values_for_old_attribute:
                                if isinstance(old_attribute_value, (dict, list)):
                                    try:
                                        parsed = json.loads(new_attribute_value) # parse the new attribute value as JSON
                                    except (json.JSONDecodeError, TypeError) as exc:
                                        raise ValueError(
                                            f"{uid}: attribute '{i.name()[10:]}' is not valid JSON: {new_attribute_value}"
                                        ) from exc
                                    obj.setdefault("attributes", {})[i.name()[10:]] = parsed # [i.name()[10:]] cuts of the first 10 characters
                                else:
                                    obj.setdefault("attributes", {})[i.name()[10:]] = new_attribute_value # [i.name()[10:]] cuts of the first 10 characters


def save_cityjson_model(citymodel: dict, filepath: str) -> None:
    """Save a CityJSON model dictionary to a file."""
    with open(filepath, "w", encoding="utf-8", buffering=8192) as fstream:
        content=(json.dumps(citymodel))
        fstream.write(content)