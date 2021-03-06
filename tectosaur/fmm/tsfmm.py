import numpy as np

import tectosaur as tct
from tectosaur.util.quadrature import gauss2d_tri, gauss4d_tri
from tectosaur.kernels import kernels
import tectosaur.util.gpu as gpu

from tectosaur.util.cpp import imp
traversal_ext = imp("tectosaur.fmm.traversal_wrapper")

traversal_module = traversal_ext.three.octree

import logging
logger = logging.getLogger(__name__)

# TODO: If I ever want this to be full FMM instead of treecode, I need to:
# -- implement the p2l and l2p operators, pretty much the same way I did the p2m/m2p
#    go from one source tri to one obs tri
# -- implement the m2l operator, go from one source tri to one obs tri
# -- implement the l2l operator

def make_tree(m, max_pts_per_cell):
    tri_pts = m[0][m[1]]
    centers = np.mean(tri_pts, axis = 1)
    pt_dist = tri_pts - centers[:,np.newaxis,:]
    Rs = np.max(np.linalg.norm(pt_dist, axis = 2), axis = 1)
    tree = traversal_module.Tree.build(centers, Rs, max_pts_per_cell)
    return tree

class TSFMM:
    def __init__(self, obs_m, src_m, **kwargs):
        if gpu.ocl_backend:
            kwargs['n_workers_per_block'] = 1

        self.cfg = kwargs
        self.K = kernels[self.cfg['K_name']]
        self.obs_m = obs_m
        self.src_m = src_m
        self.obs_tree = make_tree(self.obs_m, self.cfg['max_pts_per_cell'])
        self.src_tree = make_tree(self.src_m, self.cfg['max_pts_per_cell'])
        self.gpu_data = dict()

        self.setup_interactions()
        self.setup_output_sizes()
        self.params_to_gpu()
        self.tree_to_gpu()
        self.interactions_to_gpu()
        self.load_gpu_module()
        self.setup_arrays()


    def load_gpu_module(self):
        quad = gauss2d_tri(self.cfg['quad_order'])
        self.gpu_module = gpu.load_gpu(
            'fmm/ts_kernels.cl',
            tmpl_args = dict(
                order = self.cfg['order'],
                gpu_float_type = gpu.np_to_c_type(self.cfg['float_type']),
                quad_pts = quad[0],
                quad_wts = quad[1],
                n_workers_per_block = self.cfg['n_workers_per_block'],
                K = self.K
            )
        )

    def setup_interactions(self):
        self.interactions = traversal_module.fmmmm_interactions(
            self.obs_tree, self.src_tree, 1.0, self.cfg['mac'],
            0, True
        )

    def setup_output_sizes(self):
        order = self.cfg['order']
        # n dim = [0, order],
        # m dim = [0, n],
        # multipole_dim moments,
        # 2 = real and imaginary parts
        multipole_dim = self.K.multipole_dim
        self.n_multipoles = (order + 1) * (order + 1) * multipole_dim * 2 * self.src_tree.n_nodes
        # self.n_locals = self.n_surf_dofs * self.obs_tree.n_nodes
        self.n_input = self.src_m[1].shape[0] * 9
        self.n_output = self.obs_m[1].shape[0] * 9

    def float_gpu(self, arr):
        return gpu.to_gpu(arr, self.cfg['float_type'])

    def int_gpu(self, arr):
        return gpu.to_gpu(arr, np.int32)

    def params_to_gpu(self):
        self.gpu_data['params'] = self.float_gpu(np.array(self.cfg['params']))

    def tree_to_gpu(self):
        gd = self.gpu_data

        gd['obs_pts'] = self.float_gpu(self.obs_m[0])
        gd['obs_tris'] = self.int_gpu(self.obs_m[1][self.obs_tree.orig_idxs])
        gd['src_pts'] = self.float_gpu(self.src_m[0])
        gd['src_tris'] = self.int_gpu(self.src_m[1][self.src_tree.orig_idxs])

        self.obs_tree_nodes = self.obs_tree.nodes
        self.src_tree_nodes = self.src_tree.nodes

        for name, tree in [('src', self.src_tree), ('obs', self.obs_tree)]:
            gd[name + '_n_C'] = self.float_gpu(tree.node_centers)
            # gd[name + '_n_R'] = self.float_gpu(tree.node_Rs)

        for name, tree in [('src', self.src_tree_nodes), ('obs', self.obs_tree_nodes)]:
            gd[name + '_n_start'] = self.int_gpu(np.array([n.start for n in tree]))
            gd[name + '_n_end'] = self.int_gpu(np.array([n.end for n in tree]))

    def interactions_to_gpu(self):
        op_names = ['p2p', 'p2m', 'p2l', 'm2p', 'm2m', 'm2l', 'l2p', 'l2l']
        for name in op_names:
            op = getattr(self.interactions, name)
            if type(op) is list:
                for i, op_level in enumerate(op):
                    self.op_to_gpu(name + str(i), op_level)
            else:
                self.op_to_gpu(name, op)

        self.p2p_obs_tri_block_idx()

    def p2p_obs_tri_block_idx(self):
        t = tct.Timer()
        obs_tri_block_idx = -1 * np.ones(self.obs_m[1].shape[0], dtype = np.int)
        p2p_obs_n_idxs = np.array(self.interactions.p2p.obs_n_idxs, copy = False)
        for block_idx in range(p2p_obs_n_idxs.shape[0]):
            n_idx = p2p_obs_n_idxs[block_idx]
            start = self.obs_tree_nodes[n_idx].start
            end = self.obs_tree_nodes[n_idx].end
            assert(np.all(obs_tri_block_idx[start:end] == -1))
            obs_tri_block_idx[start:end] = block_idx
        self.obs_tri_block_idx = obs_tri_block_idx
        self.gpu_data['p2p_obs_tri_block_idx'] = self.int_gpu(self.obs_tri_block_idx)

    def op_to_gpu(self, name, op):
        for data_name in ['obs_n_idxs', 'obs_src_starts', 'src_n_idxs']:
            self.gpu_data[name + '_' + data_name] = self.int_gpu(
                np.array(getattr(op, data_name), copy = False)
            )

    def to_tree(self, input_orig):
        orig_idxs = np.array(self.src_tree.orig_idxs)
        input_orig = input_orig.reshape((-1,9))
        return input_orig[orig_idxs,:].flatten()

    def to_orig(self, output_tree):
        orig_idxs = np.array(self.obs_tree.orig_idxs)
        output_tree = output_tree.reshape((-1, 9))
        output_orig = np.empty_like(output_tree)
        output_orig[orig_idxs,:] = output_tree
        return output_orig.flatten()

    def setup_arrays(self):
        self.gpu_multipoles = gpu.empty_gpu(self.n_multipoles, self.cfg['float_type'])
        self.gpu_out = gpu.empty_gpu(self.n_output, self.cfg['float_type'])
        self.gpu_in = gpu.empty_gpu(self.n_input, self.cfg['float_type'])

    def p2m(self):
        n_obs_n = self.gpu_data['p2m_obs_n_idxs'].shape[0]
        block_size = self.cfg['n_workers_per_block']
        n_blocks = int(np.ceil(n_obs_n / block_size))
        self.gpu_module.p2m(
            self.gpu_multipoles,
            self.gpu_in,
            np.int32(n_obs_n),
            self.gpu_data['p2m_obs_n_idxs'],
            self.gpu_data['src_n_C'],
            self.gpu_data['src_n_start'],
            self.gpu_data['src_n_end'],
            self.gpu_data['src_pts'],
            self.gpu_data['src_tris'],
            grid = (n_blocks,1,1),
            block = (block_size,1,1)
        )

    def m2m(self, level):
        n_obs_n = self.gpu_data['m2m' + str(level) + '_obs_n_idxs'].shape[0]
        block_size = self.cfg['n_workers_per_block']
        n_blocks = int(np.ceil(n_obs_n / block_size))
        self.gpu_module.m2m(
            self.gpu_multipoles,
            np.int32(n_obs_n),
            self.gpu_data['m2m' + str(level) + '_obs_n_idxs'],
            self.gpu_data['m2m' + str(level) + '_obs_src_starts'],
            self.gpu_data['m2m' + str(level) + '_src_n_idxs'],
            self.gpu_data['src_n_C'],
            grid = (n_blocks,1,1),
            block = (block_size,1,1)
        )

    def m2p(self):
        n_obs_n = self.gpu_data['m2p_obs_n_idxs'].shape[0]
        if n_obs_n == 0:
            return
        block_size = self.cfg['n_workers_per_block']
        self.gpu_module.m2p_U(
            self.gpu_out,
            self.gpu_multipoles,
            self.gpu_data['params'],
            np.int32(n_obs_n),
            self.gpu_data['m2p_obs_n_idxs'],
            self.gpu_data['m2p_obs_src_starts'],
            self.gpu_data['m2p_src_n_idxs'],
            self.gpu_data['obs_n_start'],
            self.gpu_data['obs_n_end'],
            self.gpu_data['obs_pts'],
            self.gpu_data['obs_tris'],
            self.gpu_data['src_n_C'],
            grid = (n_obs_n,1,1),
            block = (block_size,1,1)
        )

    def p2p(self):
        n_obs_n = self.gpu_data['p2p_obs_n_idxs'].shape[0]
        if n_obs_n == 0:
            return
        n_obs_tris = self.obs_m[1].shape[0]
        n_blocks = int(np.ceil(n_obs_tris / self.cfg['n_workers_per_block']))
        self.gpu_module.p2p(
            self.gpu_out,
            self.gpu_in,
            np.int32(n_obs_tris),
            self.gpu_data['params'],
            self.gpu_data['p2p_obs_tri_block_idx'],
            self.gpu_data['p2p_obs_src_starts'],
            self.gpu_data['p2p_src_n_idxs'],
            self.gpu_data['obs_n_start'],
            self.gpu_data['obs_n_end'],
            self.gpu_data['obs_pts'],
            self.gpu_data['obs_tris'],
            self.gpu_data['src_n_start'],
            self.gpu_data['src_n_end'],
            self.gpu_data['src_pts'],
            self.gpu_data['src_tris'],
            grid = (n_blocks, 1, 1),
            block = (self.cfg['n_workers_per_block'], 1, 1)
        )

    def dot_helper(self, v):
        self.gpu_in[:] = self.to_tree(v.astype(self.cfg['float_type']))
        self.gpu_out.fill(0)

        self.p2p()
        self.p2m()
        for i in range(1, len(self.interactions.m2m)):
            self.m2m(i)
        self.m2p()

    def dot(self, v):
        self.dot_helper(v)

        return self.to_orig(self.gpu_out.get())

    async def async_dot(self, v):
        t = tct.Timer(output_fnc = logger.debug)
        self.dot_helper(v)
        t.report('launch fmm')
        out_tree = await gpu.async_get(self.gpu_out)
        t.report('get fmm result')
        out = self.to_orig(out_tree)
        t.report('to orig')
        return out

def report_interactions(fmm_obj):
    def count_interactions(op_name, op):
        obs_surf = False if op_name[2] == 'p' else True
        src_surf = False if op_name[0] == 'p' else True
        return traversal_module.count_interactions(
            op, fmm_obj.obs_tree, fmm_obj.src_tree,
            obs_surf, src_surf, 1
        )

    n_obs_tris = fmm_obj.obs_m[1].shape[0]
    n_src_tris = fmm_obj.src_m[1].shape[0]

    p2p = count_interactions('p2p', fmm_obj.interactions.p2p)
    n_p2p = fmm_obj.interactions.p2p.src_n_idxs.shape[0]
    n_p2m = fmm_obj.interactions.p2m.src_n_idxs.shape[0]
    n_m2m = sum([
        fmm_obj.interactions.m2m[i].src_n_idxs.shape[0]
        for i in range(len(fmm_obj.interactions.m2m))
    ])
    n_m2p = fmm_obj.interactions.m2p.src_n_idxs.shape[0]
    total = n_obs_tris * n_src_tris
    not_p2p = total - p2p

    logger.info('# obs tris: ' + str(n_obs_tris))
    logger.info('# src tris: ' + str(n_src_tris))
    logger.info('total: ' + str(total))
    logger.info('p2p percent: ' + str(p2p / total))
    logger.info('m2p percent: ' + str(not_p2p / total))
    logger.info('# p2p:' + str(n_p2p))
    logger.info('# p2m:' + str(n_p2m))
    logger.info('# m2m:' + str(n_m2m))
    logger.info('# m2p:' + str(n_m2p))
