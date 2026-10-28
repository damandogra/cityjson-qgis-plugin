"""
each face flows through it like this:

 CityJSON file ─┐
                ├→ faces ─→ check_face ─→ report
 QGIS layer ────┘           (planar? degenerate? self-intersecting?)


# Data shapes:
   ring = list of (x, y, z) corners, first corner not repeated
   face = list of rings, outer ring first, then holes

   
# Context

## for multisurface
CityJSON file
└── CityObjects
    └── "building1"
        └── geometry[0]
            └── boundaries           = list of faces
                ├── face 0           = list of rings
                │   ├── ring 0       = outer: list of vertex indices
                │   └── ring 1       = hole (optional)
                └── face 1
                    └── ring 0
   
## a building wigth 2 faces
"boundaries": [
  [ [0, 1, 2, 3], [4, 5, 6, 7] ],     ← face 0: outer ring + hole
  [ [0, 3, 8, 9] ]                    ← face 1: outer ring only
]

**Python**                          **Gives**                               **What it is**
boundaries	                        [[[0,1,2,3],[4,5,6,7]], [[0,3,8,9]]]	all faces
boundaries[0]	                    [[0,1,2,3],[4,5,6,7]]	                a face
boundaries[0][0]	                [0,1,2,3]	                            a ring: the outer one
boundaries[0][0][1]	                1	                                    a vertex index
vertices[1] → scale + translate	    (85001.0, 446000.0, 0.0)	            a corner

"""

import math


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
    # extract the ring from the face
    outer_ring = face[0] # the ring
    nx,ny,nz = newell_normal(outer_ring)
    length_n = math.sqrt(nx*nx + ny*ny + nz*nz)

    # usually a normal's length is around 2x the face area
    # if a face has zero area, theres nothing to fit a plane to
    # ex: all corners on one line
    if length_n < 1e-12:
        return None

    # scale to length 1 (unit vector)
    ux, uy, uz = nx/length_n, ny/length_n, nz/length_n

    cx, cy, cz = centroid(outer_ring)

    max_d = 0
    for ring in face: # outer ring + any holes
        for p in ring: # every corner of that ring
            d = abs(ux*(p[0]-cx) + uy*(p[1]-cy) + uz*(p[2]-cz)) # dot product
            if d > max_d:
                max_d = d # takes the max distance
                
    return max_d

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