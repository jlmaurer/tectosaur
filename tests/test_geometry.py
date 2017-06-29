from tectosaur.util.geometry import *

def test_longest_edge():
    assert(get_longest_edge(get_edge_lens(np.array([[0,0,0],[1,0,0],[0.5,0.5,0]]))) == 0)
    assert(get_longest_edge(get_edge_lens(np.array([[0,0,0],[0.5,0.5,0],[1,0,0]]))) == 2)

def test_xyhat_from_pt_simple():
    P = np.array([0.5,0.5,0.0])
    T = np.array([[0,0,0],[1,0,0],[0,1,0]])
    xyhat = xyhat_from_pt(P.tolist(), T.tolist())
    np.testing.assert_almost_equal(xyhat, [0.5, 0.5])

def test_xyhat_from_pt_harder():
    P = np.array([0,2.0,0.0])
    T = np.array([[0,2,0],[0,3,0],[0,2,1]])
    xyhat = xyhat_from_pt(P.tolist(), T.tolist())
    np.testing.assert_almost_equal(xyhat, [0.0, 0.0])

    P = np.array([0,2.5,0.5])
    T = np.array([[0,2,0],[0,3,0],[0,2,1]])
    xyhat = xyhat_from_pt(P.tolist(), T.tolist())
    np.testing.assert_almost_equal(xyhat, [0.5, 0.5])

    P = np.array([0,3.0,0.5])
    T = np.array([[0,2,0],[0,4,0],[0,2,1]])
    xyhat = xyhat_from_pt(P.tolist(), T.tolist())
    np.testing.assert_almost_equal(xyhat, [0.5, 0.5])

def test_xyhat_from_pt_random():
    for i in range(20):
        xhat = np.random.rand(1)[0]
        yhat = np.random.rand(1)[0] * (1 - xhat)
        T = np.random.rand(3,3)
        P = tri_pt(linear_basis_tri(xhat, yhat), T)
        xhat2, yhat2 = xyhat_from_pt(P.tolist(), T.tolist())
        np.testing.assert_almost_equal(xhat, xhat2)
        np.testing.assert_almost_equal(yhat, yhat2)

def test_vec_angle180():
    np.testing.assert_almost_equal(vec_angle(np.array([1,1]),np.array([-1,-1])), np.pi)

def test_tri_area():
    np.testing.assert_almost_equal(tri_area(np.array([[0,0,0],[1,0,0],[0,1,0]])), 0.5)

def test_which_side_pt():
    tri = np.array([[0,0,0],[1,0,0],[0,1,0]])
    assert(which_side_point(tri, np.array([0,0,-1])) == Side.behind)
    assert(which_side_point(tri, np.array([0,0,1])) == Side.front)
    assert(which_side_point(tri, np.array([0,0,0])) == Side.intersect)

def test_tri_side():
    assert(tri_side([Side.front, Side.front, Side.front]) == Side.front);
    assert(tri_side([Side.intersect, Side.front, Side.front]) == Side.front);
    assert(tri_side([Side.intersect, Side.intersect, Side.front]) == Side.front);
    assert(tri_side([Side.behind, Side.intersect, Side.behind]) == Side.behind);

