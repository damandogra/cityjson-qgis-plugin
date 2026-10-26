import pytest
from scripts import check_geometry

def test_flat_square_points_up():
    square = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
    assert check_geometry.newell_normal(square) == pytest.approx((0, 0, 2))