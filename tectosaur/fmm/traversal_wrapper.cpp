<% 
from tectosaur.util.build_cfg import fmm_lib_cfg
fmm_lib_cfg(cfg)
%>

#include "include/pybind11_nparray.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "traversal.hpp"
#include "octree.hpp"
#include "kdtree.hpp"

namespace py = pybind11;

template <typename TreeT>
void wrap_fmm(py::module& m) {
    using Node = typename TreeT::Node;
    py::class_<Node>(m, "TreeNode")
        .def_readonly("start", &Node::start)
        .def_readonly("end", &Node::end)
        .def_readonly("bounds", &Node::bounds)
        .def_readonly("is_leaf", &Node::is_leaf)
        .def_readonly("idx", &Node::idx)
        .def_readonly("height", &Node::height)
        .def_readonly("depth", &Node::depth)
        .def_readonly("children", &Node::children);

    py::class_<TreeT>(m, "Tree")
        .def("__init__",
        [] (TreeT& t, NPArrayD np_pts, size_t n_per_cell) {
            check_shape<TreeT::dim>(np_pts);
            new (&t) TreeT(
                as_ptr<std::array<double,TreeT::dim>>(np_pts),
                np_pts.request().shape[0], n_per_cell
            );
        })
        .def("root", &TreeT::root)
        .def_property_readonly("split", [] (const TreeT& t) { return TreeT::split; })
        .def_readonly("nodes", &TreeT::nodes)
        .def_readonly("orig_idxs", &TreeT::orig_idxs)
        .def_readonly("max_height", &TreeT::max_height)
        .def_property_readonly("pts", [] (TreeT& tree) {
            return make_array<double>(
                {tree.pts.size(), TreeT::dim},
                reinterpret_cast<double*>(tree.pts.data())
            );
        })
        .def_property_readonly("node_centers", [] (TreeT& tree) {
            auto out = make_array<double>({tree.nodes.size(), TreeT::dim});
            auto* out_ptr = as_ptr<std::array<double,TreeT::dim>>(out);
            for (size_t i = 0; i < tree.nodes.size(); i++) {
                out_ptr[i] = tree.nodes[i].bounds.center;
            }
            return out;
        })
        .def_property_readonly("node_Rs", [] (TreeT& tree) {
            auto out = make_array<double>({tree.nodes.size()});
            auto* out_ptr = as_ptr<double>(out);
            for (size_t i = 0; i < tree.nodes.size(); i++) {
                out_ptr[i] = tree.nodes[i].bounds.R;
            }
            return out;
        })
        .def_property_readonly("n_nodes", [] (TreeT& o) {
            return o.nodes.size();
        });

    m.def("fmmmm_interactions", &fmmmm_interactions<TreeT>);
    m.def("count_interactions", &count_interactions<TreeT>);
}

template <size_t dim>
void wrap_dim(py::module& m) {
    m.def("in_ball", &in_ball<dim>);

    py::class_<Ball<dim>>(m, "Ball")
        .def(py::init<std::array<double,dim>, double>())
        .def_readonly("center", &Ball<dim>::center)
        .def_readonly("R", &Ball<dim>::R);

    auto octree = m.def_submodule("octree");
    auto kdtree = m.def_submodule("kdtree");

    wrap_fmm<Octree<dim>>(octree);
    wrap_fmm<KDTree<dim>>(kdtree);
}


PYBIND11_PLUGIN(traversal_wrapper) {
    py::module m("traversal_wrapper");
    auto two = m.def_submodule("two");
    auto three = m.def_submodule("three");

    wrap_dim<2>(two);
    wrap_dim<3>(three);

#define NPARRAYPROP(type, name)\
    def_property_readonly(#name, [] (type& op) {\
        return make_array({op.name.size()}, op.name.data());\
    })
    py::class_<CompressedInteractionList>(m, "CompressedInteractionList")
        .NPARRAYPROP(CompressedInteractionList, obs_n_idxs)
        .NPARRAYPROP(CompressedInteractionList, obs_src_starts)
        .NPARRAYPROP(CompressedInteractionList, src_n_idxs);
#undef NPARRAYPROP

#define OP(NAME)\
        def_readonly(#NAME, &Interactions::NAME)
    py::class_<Interactions>(m, "Interactions")
        .OP(u2e).OP(d2e).OP(p2m).OP(m2m).OP(p2l).OP(m2l).OP(l2l).OP(p2p).OP(m2p).OP(l2p);
#undef OP

    return m.ptr();
}