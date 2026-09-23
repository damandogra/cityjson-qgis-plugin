import json
import os
import shutil
import tempfile
import pytest

from core.loading import CityJSONLoader, load_cityjson_model
from core.exporting import CityJSONExporter, save_cityjson_model

def _cube_vertices(dx):
    """Eight cube corners, shifted dx along x"""
    return [
        [0 + dx, 0, 0],
        [1000 + dx, 0, 0],
        [1000 + dx, 1000, 0],
        [0 + dx, 1000, 0],
        [0 + dx, 0, 1000],
        [1000 + dx, 0, 1000],
        [1000 + dx, 1000, 1000],
        [0 + dx, 1000, 1000],
    ]

def _cube_geometry(first_vertex):
    """A Multisurface cube whose eight corners start at first_vertex"""
    o = first_vertex
    return {
        "type": "MultiSurface",
        "lod": "1",
        "boundaries": [
            [[o + 0, o + 3, o + 2, o + 1]],  # ground
            [[o + 4, o + 5, o + 6, o + 7]],  # roof
            [[o + 0, o + 1, o + 5, o + 4]],  # wall
            [[o + 1, o + 2, o + 6, o + 5]],  # wall
            [[o + 2, o + 3, o + 7, o + 6]],  # wall
            [[o + 3, o + 0, o + 4, o + 7]],  # wall
        ],
    }

def _two_cubes_citymodel():
    """A CityJSON model with two cubes, one shifted along x"""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "vertices": _cube_vertices(0) + _cube_vertices(1000),  # two cubes, one shifted along x
        "CityObjects": {
            "building1": {
                "type": "Building",
                "attributes": {"function": "residential"},
                "geometry": [_cube_geometry(0)],
            },
            "building2": {
                "type": "Building",
                "attributes": {"function": "commercial"},
                "geometry": [_cube_geometry(8)], # because vuilding 1 already uses 0-7
            },
        },
    }

def _hierarchy_citymodel():
    """A CityJSON model with a hierarchy of two buildings, one parent and one child"""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "vertices": _cube_vertices(0) + _cube_vertices(1000) + _cube_vertices(2000),  # two cubes, one shifted along x
        "CityObjects": {
            "building1": {
                "type": "Building",
                "attributes": {"function": "residential"},
                "geometry": [_cube_geometry(0)],
                "children": ["building2", "building3"],
            },
            "building2": {
                "type": "BuildingPart",
                "attributes": {"function": "commercial"},
                "geometry": [_cube_geometry(8)], # because building 1 already uses 0-7
                "parents": ["building1"],
            },
            "building3": {
                "type": "BuildingPart",
                "attributes": {"function": "commercial"},
                "geometry": [_cube_geometry(16)], # because building 1 already uses 0-7, building2 uses 8-15
                "parents": ["building1"],
            },
        },
    }

def _delete_feature(layers, uid):
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid:
                layer.dataProvider().deleteFeatures([f.id()])
                return
    raise AssertionError(f"{uid} not found in any layer")

def _set_attribute(layers, uid, field_name, value):
    """Simulate the user editing one cell in QGIS."""
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid:
                idx = layer.fields().indexOf(field_name)
                assert idx != -1, f"{field_name} is not a column"
                layer.dataProvider().changeAttributeValues({f.id(): {idx: value}})
                return
    raise AssertionError(f"{uid} not found in any layer")

def test_fixture_writes_and_reads_back():
    temp_dir = tempfile.mkdtemp()   # a throwaway directory somewhere in the container's /tmp

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_two_cubes_citymodel(), f)     # dict → real .json file on disk

    result = load_cityjson_model(file_path)  # file on disk -> dict

    loader = CityJSONLoader(filepath=file_path, citymodel=result)  # build the converter
    for key, obj in result["CityObjects"].items():
        loader.layer_manager.add_object(key, obj)  # each CityObject -> one QGIS row

    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    assert len(layers) == 1

    features = list(layers[0].getFeatures())  # read the rows back out
    assert len(features) == 2  # two buildings in, two rows out

    shutil.rmtree(temp_dir)     # delete the directory

def test_round_trip_after_deleting_one_building():
    temp_dir = tempfile.mkdtemp()   # a throwaway directory somewhere in the container's /tmp

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_two_cubes_citymodel(), f)     # dict → real .json file on disk

    result = load_cityjson_model(file_path)  # file on disk -> dict

    loader = CityJSONLoader(filepath=file_path, citymodel=result)  # build the converter
    for key, obj in result["CityObjects"].items():
        loader.layer_manager.add_object(key, obj)  # each CityObject -> one QGIS row

    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    # module doesnt exist yet
    from core.exporting import CityJSONExporter, save_cityjson_model

    layer = layers[0]


    # find the row for building2
    fid = None
    for f in layer.getFeatures():
        if f["uid"] == "building2":
            fid = f.id()
            break

    assert fid is not None, "building2 not found in the layer"

    # delete that row -- this is the user's edit in QGIS
    layer.dataProvider().deleteFeatures([fid])

    # export what's left, write it out
    exported = CityJSONExporter (layers, citymodel=result).export()
    save_cityjson_model(exported, os.path.join(temp_dir, "output.city.json"))

    # read it back and check
    output = load_cityjson_model(os.path.join(temp_dir, "output.city.json"))

    assert "building2" not in output["CityObjects"]  # building2 should be gone
    assert "building1" in output["CityObjects"]  # building1 should still be there

    assert len(output["vertices"]) == 8   # one cube's worth

    shutil.rmtree(temp_dir)     # delete the directory

def test_save_cityjson_model_round_trip():
    """dict → save_cityjson_model → file → load_cityjson_model → dict"""

    temp_dir = tempfile.mkdtemp()   # a throwaway directory somewhere in the container's /tmp
    file_path = os.path.join(temp_dir, "out.city.json")

    save_cityjson_model(_two_cubes_citymodel(), file_path)  # write out a CityJSON model
    loaded_back = load_cityjson_model(file_path)  # read the cityjson model back

    assert loaded_back == _two_cubes_citymodel()  # should be identical to what we wrote out
    shutil.rmtree(temp_dir)     # delete the directory

def test_get_surviving_ids_after_delete(qgis_app):
    cm = _two_cubes_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm) # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers() # collect the finished layer

    # simulate deleting building2
    layer = layers[0]
    fid = None
    for f in layer.getFeatures():
        if f["uid"] == "building2":
            fid = f.id()
            break

    assert fid is not None, "building2 not found in the layer"

    # delete that row -- this is the user's edit in QGIS
    layer.dataProvider().deleteFeatures([fid])

    # get the surviving IDs
    surviving_ids = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()

    assert "building2" not in surviving_ids  # building2 should be gone
    assert "building1" in surviving_ids  # building1 should still be there

def test_get_surviving_ids_after_delete_parent(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm) # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers() # collect the finished layer

    # find building 1
    fid = None
    target_layer = None
    for layer in layers: # iterating each layer to find the one that contains building1
        for f in layer.getFeatures(): # inner: each row in that layer (table)
            if f["uid"] == "building1":
                target_layer = layer
                fid = f.id()
                break
        if fid is not None: # if we found the feature, we can break out of the outer loop as well
            break

    assert fid is not None, "building1 not found in the layer"
    assert target_layer is not None, "building1 not found in any layer"

    # delete building 1's feature from the layer -- this is the user's edit in QGIS
    target_layer.dataProvider().deleteFeatures([fid])

    surviving = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()
    assert surviving == {"building1", "building2", "building3"}

def test_deleting_parent_resurrects_it(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_feature(layers, "building1")

    surviving = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()
    assert surviving == {"building1", "building2", "building3"}

    exported = CityJSONExporter(layers, citymodel=cm).export()
    assert exported["CityObjects"]["building1"]["children"] == ["building2", "building3"]

def test_prune_drops_deleted_children(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_feature(layers, "building2")

    exported = CityJSONExporter(layers, citymodel=cm).export()
    assert exported["CityObjects"]["building1"]["children"] == ["building3"]
    assert "building2" not in exported["CityObjects"]

# Test - changing an attribute in QGIS and exporting it back to CityJSON
def test_attribute_change_round_trip(qgis_app):
    cm = _two_cubes_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm) # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers() # collect the finished layer

    # find building 1
    fid = None
    target_layer = None
    for layer in layers: # iterating each layer to find the one that contains building1
        for f in layer.getFeatures(): # inner: each row in that layer (table)
            f["uid"] = "building1"  # set the uid to building1
            fid = f.id() # get the feature id
            target_layer = layer # remember the layer that contains building1
            break
        if fid is not None: # if we found the feature, we can break out of the outer loop as well
            break

    assert fid is not None, "building1 not found in the layer"
    assert target_layer is not None, "building1 not found in any layer"

    # edit the feature (user does in qgis)
    idx = target_layer.fields().indexOf("attribute.function") # get the index of the attribute.function field
    target_layer.dataProvider().changeAttributeValues({fid: {idx: "mixed"}}) # change the value of attribute.function to mixed

    # Export and check
    
    out = CityJSONExporter(layers, citymodel=cm).export()
    assert out["CityObjects"]["building1"]["attributes"]["function"] == "mixed"
    assert out["CityObjects"]["building2"]["attributes"]["function"] == "commercial"  # unchanged

def test_untouched_int_keeps_its_type(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["height"] = 12
    cm["CityObjects"]["building2"]["attributes"]["height"] = 12.5  # makes the column Double

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    out = CityJSONExporter(layers, citymodel=cm).export()  # no edits

    height = out["CityObjects"]["building1"]["attributes"]["height"]
    assert height == 12
    assert isinstance(height, int)  # not 12.0

def test_missing_attribute_stays_missing(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["height"] = 12  # only building1

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    out = CityJSONExporter(layers, citymodel=cm).export()  # no edits

    assert "height" not in out["CityObjects"]["building2"]["attributes"]


def test_edited_list_comes_back_as_list(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["tags"] = ["a", "b"]

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _set_attribute(layers, "building1", "attribute.tags", '["a", "c"]')

    out = CityJSONExporter(layers, citymodel=cm).export()
    assert out["CityObjects"]["building1"]["attributes"]["tags"] == ["a", "c"]

    def test_broken_json_list_raises_clear_error(qgis_app):
        cm = _two_cubes_citymodel()
        cm["CityObjects"]["building1"]["attributes"]["tags"] = ["a", "b"]

        loader = CityJSONLoader(filepath="dummy", citymodel=cm)
        loader.load()
        layers = loader.layer_manager.get_all_layers()

        _set_attribute(layers, "building1", "attribute.tags", '["a", "c"')  # missing ]

        with pytest.raises(ValueError):
            CityJSONExporter(layers, citymodel=cm).export()