import pytest
from scripts import check_geometry

def test_flat_square_points_up():
    square = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
    assert check_geometry.newell_normal(square) == pytest.approx((0, 0, 2))

def test_flat_square_is_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_lifted_corner_is_not_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0.05), (0, 1, 0)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0.0125, abs=1e-4)

# --- newell_normal ---

def test_rd_square_points_up():
    ring = [(85000, 446000, 0), (85001, 446000, 0), (85001, 446001, 0), (85000, 446001, 0)]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, 0, 2))


def test_wall_points_sideways():
    ring = [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, -2, 0))


def test_concave_l_shape():
    ring = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, 0, 6))


# --- planarity_deviation ---

def test_wall_is_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_rd_square_is_planar():
    face = [[(85000, 446000, 0), (85001, 446000, 0), (85001, 446001, 0), (85000, 446001, 0)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_hole_off_plane_is_not_planar():
    outer = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    hole = [(1, 1, 0.05), (1, 3, 0.05), (3, 3, 0.05), (3, 1, 0.05)]
    assert check_geometry.planarity_deviation([outer, hole]) == pytest.approx(0.05, abs=1e-4)


def test_collinear_face_returns_none():
    face = [[(0, 0, 0), (1, 0, 0), (2, 0, 0)]]
    assert check_geometry.planarity_deviation(face) is None