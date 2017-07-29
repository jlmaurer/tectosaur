import numpy as np
from tectosaur.util.test_decorators import slow, kernel

import tectosaur.fmm.fmm_wrapper as fmm
from tectosaur.farfield import farfield_pts_direct
from test_fmm import run_full, rand_pts, check

# test fmm with elastic kernels more, this is confusing...
# i think there are a variety of issues here.
# -- first, with single precision, nearfield computations get messed up because the 1 / r^2 or 1/r^3 has numerical precision issues
# -- second, i think there is some kind of subtle difference between the results of the autogenerated kernel and the hand written optimized elastic kernels. this difference mostly pops up in
# -- this is a big problem because if the kernels differ sufficiently, then 1) they are wrong and 2) i need to use the same ones everywhere... WHAT IS PROBLEM HERE?
# OKAY: So, the autogenerated kernels were using single precision everywhere which was bad. That's fixed.
# Also, I realized I was doing the mapping from input space into kd-tree space wrong, now that's fixed,
# everything seems to behave nicely and converge as expected.
@slow
def test_self_fmm():
    kernel = 'elasticH'
    tensor_dim = 3
    np.random.seed(10)
    n = 20000
    params = [1.0, 0.25]
    pts = np.random.rand(n, 3)
    ns = np.random.rand(n, 3)
    ns /= np.linalg.norm(ns, axis = 1)[:,np.newaxis]
    input = np.random.rand(n * tensor_dim)

    mac = 3.0
    results = []
    for order in [50, 100, 150]:
        kd = fmm.three.Octree(pts, ns, order)
        orig_idxs = np.array(kd.orig_idxs)
        input_kd = input.reshape((-1,3))[orig_idxs,:].reshape(-1)
        fmm_mat = fmm.three.fmmmmmmm(
            kd, kd, fmm.three.FMMConfig(1.1, mac, order, kernel, params)
        )
        output = fmm.eval_ocl(fmm_mat, input_kd)

        output = output.reshape((-1, 3))
        to_orig = np.empty_like(output)
        orig_idxs = np.array(kd.orig_idxs)
        to_orig[orig_idxs,:] = output
        results.append(to_orig)
        if len(results) > 1:
            check(results[-2].flatten(), results[-1].flatten(), 0)
    results = np.array(results)
    print(results[:,0])

    # orig_idxs = np.array(kd.orig_idxs)
    # input_kd = input.reshape((-1,3))[orig_idxs,:].reshape(-1)
    # correct_kd = farfield_pts_direct(kernel, np.array(kd.pts), np.array(kd.normals), np.array(kd.pts), np.array(kd.normals), input_kd, params).reshape((-1,3))
    # correct2 = np.empty_like(correct_kd)
    # correct2[orig_idxs,:] = correct_kd
    # # check(results[-1,:], correct2, 2)
    # correct2 = correct2.reshape(correct2.size)
    # correct = farfield_pts_direct(kernel, pts, ns, pts, ns, input, params)
    # check(results[-1,:].flatten(), correct, 2)

@slow
def test_build_big():
    pts = np.random.rand(1000000, 3)
    import time
    start = time.time()
    octree = fmm.three.Octree(pts, pts, 1)
    print("octree took: " + str(time.time() - start))

@slow
def test_high_accuracy():
    import time
    start = time.time()
    # check_invr(*run_full(15000, rand_pts, 2.6, 100, "invr", []), accuracy = 6)
    run_full(300000, rand_pts, 2.6, 100, "invr", [])
    print("took: " + str(time.time() - start))

@slow
def test_elasticH():
    params = [1.0, 0.25]
    K = "elasticH"
    obs_pts, obs_ns, src_pts, src_ns, est = run_full(
        10000, ellipse_pts, 2.8, 52, K, params
    )
    # correct_mat = fmm.direct_eval(
    #     K, obs_pts, obs_ns, src_pts, src_ns, params
    # ).reshape((3 * obs_pts.shape[0], 3 * src_pts.shape[0]))
    # correct = correct_mat.dot(np.ones(3 * src_pts.shape[0]))
    # check(est, correct, 3)
