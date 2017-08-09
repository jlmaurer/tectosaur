#pragma once

#include <cmath>
#include <functional>
#include <memory>

template <size_t dim>
struct FMMConfig {
    // The MAC needs to < (1.0 / (check_r - 1)) so that farfield
    // approximations aren't used when the check surface intersects the
    // target box. How about we just use that as our MAC, since errors
    // further from the check surface should flatten out! 
    // TODO: Above comment is confusing. Clarify check_r, equiv_r, MAC, etc. Define them.
    // TODO: Several of these configuration parameters will no longer be needed when
    // the C++ layer only does traversal and builds interaction lists.
    double inner_r;
    double outer_r;
    size_t order;
};

struct CompressedInteractionList {
    std::vector<int> obs_n_idxs;//TODO: Make these 64-bit.
    std::vector<int> obs_src_starts;
    std::vector<int> src_n_idxs;
};

template <typename TreeT>
size_t count_interactions(const CompressedInteractionList& list,
    const TreeT& obs_tree, const TreeT& src_tree,
    bool obs_surf, bool src_surf, int n_surf) 
{
    size_t n = 0;
    for (size_t i = 0; i < list.obs_n_idxs.size(); i++) {
        int obs_n_idx = list.obs_n_idxs[i];
        int n_obs = n_surf;
        if (!obs_surf) {
            auto& n = obs_tree.nodes[obs_n_idx];
            n_obs = n.end - n.start;
        }
        for (int j = list.obs_src_starts[i]; j < list.obs_src_starts[i + 1]; j++) {
            int src_n_idx = list.src_n_idxs[j];
            int n_src = n_surf;
            if (!src_surf) {
                auto& n = src_tree.nodes[src_n_idx];
                n_src = n.end - n.start;
            }
            n += n_obs * n_src;
        }
    }
    return n;
}

CompressedInteractionList compress(const std::vector<std::vector<int>>& list);

template <typename TreeT>
struct FMMMat {
    TreeT obs_tree;
    TreeT src_tree;

    FMMConfig<TreeT::dim> cfg;

    CompressedInteractionList p2m;
    std::vector<CompressedInteractionList> m2m;
    std::vector<CompressedInteractionList> u2e;

    CompressedInteractionList l2p;
    std::vector<CompressedInteractionList> l2l;
    std::vector<CompressedInteractionList> d2e;

    CompressedInteractionList p2p;
    CompressedInteractionList p2l;
    CompressedInteractionList m2p;
    CompressedInteractionList m2l;

    FMMMat(TreeT obs_tree, TreeT src_tree, FMMConfig<TreeT::dim> cfg);
};

template <typename TreeT>
FMMMat<TreeT> fmmmmmmm(const TreeT& obs_tree, const TreeT& src_tree,
    const FMMConfig<TreeT::dim>& cfg);
