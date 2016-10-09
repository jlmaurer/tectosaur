import time
import numpy as np
from tectosaur.interpolate import barycentric_evalnd, cheb, cheb_wts, from_interval
from tectosaur.standardize import standardize

minlegalA = 0.0939060848748 - 0.01
minlegalB = 0.233648154379 - 0.01
maxlegalB = 0.865565992417 + 0.01
filename, n_A, n_B, n_pr = ('coincidenttable_limits.npy', 8, 8, 8)
filename, n_A, n_B, n_pr = ('testtable.npy', 3, 3, 3)

def coincident_table(kernel, sm, pr, pts, tris):
    Ahats = cheb(-1, 1, n_A)
    Bhats = cheb(-1, 1, n_B)
    prhats = cheb(-1, 1, n_pr)
    Ah,Bh,Nh = np.meshgrid(Ahats, Bhats,prhats)
    interp_pts = np.array([Ah.ravel(),Bh.ravel(), Nh.ravel()]).T

    Awts = cheb_wts(-1,1,n_A)
    Bwts = cheb_wts(-1,1,n_B)
    prwts = cheb_wts(-1,1,n_pr)
    interp_wts = np.outer(Awts,np.outer(Bwts,prwts)).ravel()

    table = np.load(kernel + filename)
    tri_pts = pts[tris]
    out = np.empty((tris.shape[0], 3, 3, 3, 3))
    for i in range(tris.shape[0]):
        start = time.time()
        standard_tri, labels, translation, R, scale = standardize(tri_pts[i,:,:])
        print(standard_tri)
        A, B = standard_tri[2][0:2]
        interp_vals = np.empty(81)

        Ahat = from_interval(minlegalA, 0.5, A)
        Bhat = from_interval(minlegalB, maxlegalB, B)
        prhat = from_interval(0.0, 0.5, pr)
        for j in range(81):
            interp_vals[j] = barycentric_evalnd(
                interp_pts, interp_wts, table[:, j], np.array([[Ahat, Bhat, prhat]])
            )[0]
        interp_vals = interp_vals.reshape((3,3,3,3))

        for sb1 in range(3):
            for sb2 in range(3):
                cb1 = labels[sb1]
                cb2 = labels[sb2]
                correct = R.T.dot(interp_vals[sb1,:,sb2,:]).dot(R) / (sm * scale ** 1)
                out[i,cb1,:,cb2,:] = correct
        T3 = time.time() - start; start = time.time()
        print(T3)
    return out

# def adjacent_table(kernel,
