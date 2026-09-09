import json
import os
import shutil
import tempfile

from core.loading import CityJSONLoader, load_cityjson_model

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



def test_fixture_writes_and_reads_back():
    temp_dir = tempfile.mkdtemp()   # a throwaway directory somewhere in the container's /tmp

    citymodel = {
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

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(citymodel, f)     # dict → real .json file on disk

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

    citymodel = {
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

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(citymodel, f)     # dict → real .json file on disk

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


    shutil.rmtree(temp_dir)     # delete the directory