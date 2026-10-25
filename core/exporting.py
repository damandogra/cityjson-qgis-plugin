"""Writes QGIS layers back out as CityJSON."""

import json
import copy
from .utils import createCityJSON
from . import subset
from .layers import _stringify_attribute
from .geometry import GeometryReader, VerticesCache


class CityJSONExporter:
    """Rebuilds a CityJSON model from QGIS layers."""

    def __init__(self, layers, citymodel=None, loaded_lod="All", keep_unloaded=True):
        self.layers = layers
        self.citymodel = citymodel
        self.loaded_lod = loaded_lod # tells the exporter which lod was loaded in qgis
        self.keep_unloaded = keep_unloaded  # what should happen to never loaded things, users decision (keep: default or False : drop)

    def export(self) -> dict: # returns a dictionary representing the CityJSON model
        """
        Export the configured layers as a CityJSON model dictionary.
        1. Create a new CityJSON model with the same version and transform as the original.
        2. Get the surviving IDs from the layers (plus never-loaded objects if keep_unloaded).
        3. For each surviving ID, copy the corresponding CityObject from the original model to the new model.
        4. If keep_unloaded is False, drop geometry entries not at the loaded LoD.
        5. Drop geometry entries whose LoD row was deleted in QGIS.
        6. Rebuild the vertices array from the surviving CityObjects, and update array indices.
        """

        new_cm = createCityJSON()
        new_cm["version"] = self.citymodel["version"] # copy version
        if "transform" in self.citymodel: # copy transform if it exists
            new_cm["transform"] = self.citymodel["transform"]

        surviving_ids = self.get_surviving_ids()
        counts = self._count_rows()
        has_lod_rows = False # assume no lod column
        for _uid, lod in counts:
            if lod is not None:
                has_lod_rows = True
                break


        for uid in self.citymodel["CityObjects"]: # copy the CityObject to the new model, if it exists in the surviving IDs
            if uid in surviving_ids:
                new_cm["CityObjects"][uid] = copy.deepcopy(self.citymodel["CityObjects"][uid]) # copy the CityObject to the new model

        # if the user decides to drop the unloaded lods get rid of them:
        if not self.keep_unloaded: # if keep_unloaded is false then enters in this loop
            reader = GeometryReader(VerticesCache(), self.citymodel.get("geometry-templates"), lod=self.loaded_lod) # builds the lod checker
            
            for obj in new_cm["CityObjects"].values(): # each object
                kept=[]
                for geom in obj.get("geometry", []): # each geometry of this object (g1,g2; g1 = {"type": "MultiSurface", "lod": "1", "boundaries": [...]},  # LoD1 cube)
                    if reader.has_lod([geom], self.loaded_lod): # is this the loaded lod?
                        kept.append(geom)
                if "geometry" in obj: # handles geometry less objects such as CityObjectGroup
                    obj["geometry"] = kept # replace with only the loaded-LoD geometries

        # drop geometry entries whose lod row was deleted in qgis; the object survives if any row survives
        if has_lod_rows:
            reader = GeometryReader(VerticesCache(), self.citymodel.get("geometry-templates"), lod=self.loaded_lod)
            for uid, obj in new_cm["CityObjects"].items(): # each surviving object
                kept = []
                for geom in obj.get("geometry", []): # each geometry of this object
                    was_loaded = reader.has_lod([geom], self.loaded_lod) # was it shown in qgis?
                    lod = str(reader.get_lod(geom)) # e.g. "2"
                    if not was_loaded:
                        kept.append(geom) # never loaded: keep
                    elif (uid, lod) in counts:
                        kept.append(geom) # row still exists: keep
                    # else: row deleted, drop
                if "geometry" in obj:
                    obj["geometry"] = kept


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

    # 
    def _count_rows(self): # _ at the start of function is python convention for this method is only used inside this class
        counts = {} # {(uid, lod): number of rows}.
        for layer in self.layers:
            has_lod = "lod" in layer.fields().names() # checks if lod column exists
            for feature in layer.getFeatures():
                uid = feature["uid"] # uid of this row
                lod = feature["lod"] if has_lod else None
                key = (uid, lod)
                if key in counts: # count rows per (uid, lod); one object can have several rows
                    counts[key] = counts[key] + 1
                else:
                    counts[key] = 1
        return counts

    def get_surviving_ids(self):
        """Ids that survive export: rows in QGIS, never-loaded objects (if kept), and their parents."""
        uids = set() # set helps us avoid duplicates

        # Part 1: collects objects that has row in qgis
        for uid, lod in self._count_rows():
            uids.add(uid)

        # Part 2: add objects that were never loaded
        reader = GeometryReader(VerticesCache(), self.citymodel.get("geometry-templates"), lod=self.loaded_lod)
        for uid, obj in self.citymodel["CityObjects"].items(): # loops over the objects
            if self.keep_unloaded and not reader.has_lod(obj.get("geometry", []), self.loaded_lod): # checks in the original file, if the loaded lod does not exist for the object, adds the uid to surviving
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
                if uid in new_cm["CityObjects"]:       # is the key there? True/False, never crashes
                    obj = new_cm["CityObjects"][uid]   # only runs if it is, so it's safe
                    for i in layer.fields():
                        if i.name().startswith("attribute."): # only consider fields that start with "attribute."
                            old_attribute_value = obj.get("attributes", {}).get(i.name()[10:], None)
                            expected_values_for_old_attribute = _stringify_attribute(old_attribute_value)
                            new_attribute_value = feature[i.name()]
                            if new_attribute_value != expected_values_for_old_attribute:
                                if isinstance(old_attribute_value, (dict, list)):
                                    try:
                                        parsed = json.loads(new_attribute_value)
                                    except (json.JSONDecodeError, TypeError) as exc:
                                        raise ValueError(
                                            f"{uid}: attribute '{i.name()[10:]}' is not valid JSON: {new_attribute_value}"
                                        ) from exc
                                    obj.setdefault("attributes", {})[i.name()[10:]] = parsed
                                else:
                                    obj.setdefault("attributes", {})[i.name()[10:]] = new_attribute_value

def save_cityjson_model(citymodel: dict, filepath: str) -> None:
    """Save a CityJSON model dictionary to a file."""
    with open(filepath, "w", encoding="utf-8", buffering=8192) as fstream:
        content=(json.dumps(citymodel))
        fstream.write(content)