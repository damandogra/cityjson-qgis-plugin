"""
each face flows through it like this:

 CityJSON file ─┐
                ├→ faces ─→ check_face ─→ report
 QGIS layer ────┘           (planar? degenerate? self-intersecting?)


# Data shapes:
   ring = list of (x, y, z) corners, first corner not repeated
   face = list of rings, outer ring first, then holes

"""



PLANARITY_TOL = 0.01 # val3dity default: https://val3dity.readthedocs.io/main/usage/.

# plain math

def centroid(ring):
    """Average corner of a ring."""
    n = len(ring)
    total_x = 0
    total_y = 0
    total_z = 0
    for p in ring:
        total_x += p[0]
        total_y += p[1]
        total_z += p[2]
    cx, cy, cz = total_x / n, total_y / n, total_z / n
    return (cx, cy, cz)


def newell_normal(ring):
    """
    you give in the ring of corners, it tells which way the face points
    nx,ny,nz is the normal showing the direction of the fitted plane

    """
    # A. centroid
    cx, cy, cz = centroid(ring)

    # B. shift every cornenr by minus the centroid
    shifted_ring = []
    for p in ring:
        x = p[0] - cx
        y = p[1] - cy
        z = p[2] - cz
        shifted_ring.append((x,y,z))

    # C. turns the shifted corners into the normal
    nx = 0
    ny = 0
    nz = 0

    n = len(shifted_ring)
    for p in range(n):
        next_corner = p + 1
        if next_corner == n:
            next_corner = 0
        corner = shifted_ring[p]
        next_cor = shifted_ring[next_corner]

        xi,yi,zi = corner
        xj, yj, zj = next_cor
        nx += (yi * zj) - (zi * yj)
        ny += (zi * xj) - (xi * zj)
        nz += (xi * yj) - (yi * xj)

    return (nx, ny, nz)


def planarity_deviation(face):
    """Face -> how far the worst corner sits off the plane"""

    return

def is_degenerate(face):
    """Face -> True if it has fewer than 3 distinct corners or zero area"""
    return

def is_self_intersecting(face):
    """Face -> True if its edges cross"""
    return
# maths end

def check_face(face, tol=PLANARITY_TOL):
    """Runs, planarity_deviation(), is_degenerate(), is_self_intersecting() and returns one result"""
    return

# following feed faces
def faces_from_cityjson(citymodel):
    """File -> every face as (x,y,z) corners, tagged with object id and LoD"""
    return

def faces_from_layer(layer):
    """edited QGIS layer -> same faces, for the experiment"""
    return



def main():
    """CLI: python scripts/check_geometry.py file.city.json --tol 0.01, prints the report"""
    return


if __name__ == "__main__":
    main()