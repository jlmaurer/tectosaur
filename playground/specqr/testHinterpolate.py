data = [0, -0.415393, 1, -0.410053, 2, -0.404832, 3, -0.399726, 4, -0.394732, 5, -0.389846, 6, -0.385065, 7, -0.380387, 8, -0.375807, 9, -0.371324, 10, -0.366934, 11, -0.362635, 12, -0.358425, 13, -0.3543, 14, -0.350259, 15, -0.346298, 16, -0.342417, 17, -0.338612, 18, -0.334882, 19, -0.331224, 20, -0.327637, 21, -0.324119, 22, -0.320668, 23, -0.317283, 24, -0.31396, 25, -0.3107, 26, -0.307499, 27, -0.304359, 28, -0.301275, 29, -0.298247, 30, -0.295273, 31, -0.292353, 32, -0.289484, 33, -0.286666, 34, -0.283898, 35, -0.281178, 36, -0.278503, 37, -0.275875, 38, -0.273292, 39, -0.270752, 40, -0.268255, 41, -0.2658, 42, -0.263386, 43, -0.261011, 44, -0.258675, 45, -0.256377, 46, -0.254116, 47, -0.251892, 48, -0.249703, 49, -0.247548, 50, -0.245428, 51, -0.24334, 52, -0.241285, 53, -0.239262, 54, -0.23727, 55, -0.235308, 56, -0.233376, 57, -0.231473, 58, -0.229599, 59, -0.227752, 60, -0.225933, 61, -0.22414, 62, -0.222374, 63, -0.220633, 64, -0.218918, 65, -0.217227, 66, -0.21556, 67, -0.213916, 68, -0.212297, 69, -0.210699, 70, -0.209124, 71, -0.207571, 72, -0.206039, 73, -0.204528, 74, -0.203038, 75, -0.201568, 76, -0.200118, 77, -0.198687, 78, -0.197275, 79, -0.195882, 80, -0.194507, 81, -0.19315, 82, -0.191811, 83, -0.190489, 84, -0.189184, 85, -0.187896, 86, -0.186624, 87, -0.185369, 88, -0.184129, 89, -0.182905, 90, -0.181696, 91, -0.180502, 92, -0.179322, 93, -0.178158, 94, -0.177007, 95, -0.17587, 96, -0.174748, 97, -0.173638, 98, -0.172542, 99, -0.171459, 100, -0.170388]

import numpy as np
idxs = np.array(data[::2])
vals = np.array(data[1::2])
xs = 1.0 + idxs * 0.01
# import matplotlib.pyplot as plt
# plt.plot(xs, vals)
# plt.show()

import scipy.interpolate
subsetxs = xs[::14]
subsetvals = vals[::14]
vals_test = scipy.interpolate.barycentric_interpolate(subsetxs, subsetvals, xs)
diff = np.abs((vals_test - vals) / vals)
import ipdb; ipdb.set_trace()
