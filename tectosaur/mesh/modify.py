import numpy as np
import cppimport

fast_modify = cppimport.imp('tectosaur.mesh.fast_modify')

# TODO: The current implementation of this works well for checking equality of pts
# but doesn't work well with larger thresholds because two points can be arbitrarily
# close but on opposite sides of a bucket boundary. This can be avoided probabalistically
# by choosing two thresholds that are close but not equal.
def remove_duplicate_pts(m, threshold = None):
    dim = m[0].shape[1]
    if threshold is None:
        default_threshold_factor = 1e-13
        threshold = np.max(np.max(m[0], axis = 0) - np.min(m[0], axis = 0)) * default_threshold_factor
    return getattr(fast_modify, 'remove_duplicate_pts' + str(dim))(m[0], m[1], threshold)

def concat_two(m1, m2):
    return remove_duplicate_pts(concat_two_no_remove_duplicates(m1, m2))

def concat_two_no_remove_duplicates(m1, m2):
    return np.vstack((m1[0], m2[0])), np.vstack((m1[1], m2[1] + m1[0].shape[0]))

def concat(*ms):
    m_full = ms[0]
    for m in ms[1:]:
        m_full = concat_two(m_full, m)
    return m_full

def flip_normals(m):
    return (m[0], np.array([[m[1][i,0],m[1][i,2],m[1][i,1]] for i in range(m[1].shape[0])]))
