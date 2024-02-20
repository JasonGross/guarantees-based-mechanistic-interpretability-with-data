from typing import Literal, Tuple, Union, overload
from torch import Tensor
from jaxtyping import Float
import torch
import numpy as np
from gbmi.utils.lowrank import LowRankTensor


@torch.no_grad()
def factor_right_contribution(
    m: Float[Tensor, "r c"],  # noqa: F722
    v: Float[Tensor, "c"],  # noqa: F821
    sanity_check: bool = True,
    show: bool = True,
) -> Tuple[Float[LowRankTensor, "r c"], Float[Tensor, "r c"]]:  # noqa: F722
    """Returns the contribution of v to m, and the residual
    Complexity: O(r c)
    """
    v = v / v.norm(dim=-1, keepdim=True)
    assert (
        m.shape[-1] == v.shape[-1]
    ), f"m.shape[-1] must match the shape of v ({m.shape[-1]} != {v.shape[-1]}, m.shape: {m.shape}, v.shape: {v.shape})"
    v_alt = m @ v
    contrib = LowRankTensor(
        v_alt[..., None], v[..., None, :], check=sanity_check, show=show
    )
    if sanity_check:
        assert contrib.check(torch.stack([v * (row @ v) for row in m], dim=0))
    return contrib, m - contrib


@torch.no_grad()
def factor_left_contribution(
    m: Float[Tensor, "r c"],  # noqa: F722
    v: Float[Tensor, "r"],  # noqa: F821
    sanity_check: bool = True,
    show: bool = True,
) -> Tuple[Float[LowRankTensor, "r c"], Float[Tensor, "r c"]]:  # noqa: F722
    """Returns the contribution of v to m, and the residual
    Complexity: O(r c)
    """
    contrib, resid = factor_right_contribution(
        m.T, v, sanity_check=sanity_check, show=show
    )
    return contrib.T, resid.T


@overload
def factor_contribution(
    m: Float[Tensor, "r c"],  # noqa: F722
    v: Float[Tensor, "r"],  # noqa: F821
    *,
    sanity_check: bool = True,
    show: bool = True,
    side: Literal["left"] = "left",
) -> Tuple[Float[LowRankTensor, "r c"], Float[Tensor, "r c"]]:  # noqa: F722
    """Returns the contribution of v to m, and the residual
    Complexity: O(r c)
    """
    ...


@overload
def factor_contribution(
    m: Float[Tensor, "r c"],  # noqa: F722
    v: Float[Tensor, "c"],  # noqa: F821
    *,
    sanity_check: bool = True,
    show: bool = True,
    side: Literal["right"],
) -> Tuple[Float[LowRankTensor, "r c"], Float[Tensor, "r c"]]:  # noqa: F722
    """Returns the contribution of v to m, and the residual
    Complexity: O(r c)
    """
    ...


@torch.no_grad()
def factor_contribution(
    m: Float[Tensor, "r c"],  # noqa: F722
    v: Union[Float[Tensor, "r"], Float[Tensor, "c"]],  # noqa: F821
    *,
    sanity_check: bool = True,
    show: bool = True,
    side: Literal["left", "right"] = "left",
) -> Tuple[Float[LowRankTensor, "r c"], Float[Tensor, "r c"]]:  # noqa: F722
    """Returns the contribution of v to m, and the residual
    Complexity: O(r c)
    """
    if side == "left":
        return factor_left_contribution(m, v, sanity_check=sanity_check)
    elif side == "right":
        return factor_right_contribution(m, v, sanity_check=sanity_check)
    else:
        raise ValueError(f"side must be left or right, not {side}")


# %%
@torch.no_grad()
def max_row_diffs_per_dim_2(
    A: Float[Tensor, "... a b"], B: Float[Tensor, "... b c"]  # noqa: F722
) -> Float[Tensor, "... a"]:  # noqa: F722
    r"""Computes the maximum difference between elements in the same row of the product of A and B

    Complexity: O(ab + bc)

    $$\begin{align*}
    &\max_{r,i,j} (AB)_{r,i} - (AB)_{r,j} \\
    &= \max_{r,i,j} \sum_k \left(A_{r,k} B_{k,i} - A_{r,k} B_{k,j}\right) \\
    &= \max_{r,i,j} \sum_k A_{r,k} \left(B_{k,i} - B_{k,j}\right) \\
    &\le \max_r \sum_k \max_{i,j} A_{r,k} \left(B_{k,i} - B_{k,j}\right) \\
    &= \max_r \sum_k A_{r,k}\begin{cases} \max_{i,j}  \left(B_{k,i} - B_{k,j}\right) & \text{if }A_{r,j} \ge 0 \\ \min_{i,j} \left(B_{k,i} - B_{k,j}\right) & \text{if }A_{r,j} <0 \end{cases} \\
    &= \max_r \sum_k A_{r,k}\begin{cases} \max_{i,j}  \left(B_{k,i} - B_{k,j}\right) & \text{if }A_{r,j} \ge 0 \\ -\max_{i,j} \left(B_{k,i} - B_{k,j}\right) & \text{if }A_{r,j} <0 \end{cases} \\
    &= \max_r \sum_k \left|A_{r,k}\max_{i,j}  \left(B_{k,i} - B_{k,j}\right)\right| \\
    &= \max_r \sum_k \left|A_{r,k}\right|\left|\max_{i,j}  \left(B_{k,i} - B_{k,j}\right)\right| \\
    \end{align*}$$

    Postconditions:
        \forall r, i, j:
            -return_r <= (AB)_{r,i} - (AB)_{r,j} <= return_r
    """
    max_B_diffs = B.max(dim=-1).values - B.min(dim=-1).values
    return A.abs() @ max_B_diffs.abs()


# %%
@torch.no_grad()
def max_row_diffs_per_dim(*m: Tensor) -> Tensor:
    r"""Computes the maximum difference between elements in the same row of the product of the passed matrices by considering all points to break the product at

    Complexity: O(  \sum_{0 ≤ i < j < len(m) - 1} m[0].shape[-2] * m[i].shape[-1] * m[j].shape[-1]
    Complexity:   + \sum_{0 < i < j ≤ len(m) - 1} m[i].shape[-2] * m[j].shape[-2] * m[-1].shape[-1]
    Complexity:   + \sum_{0 ≤ i < len(m) - 1} m[0].shape[-2] * m[i].shape[-1] + m[i+1].shape[-2] * m[-1].shape[-1])

    Preconditions:
        \forall i: m[i].shape[-1] == m[i + 1].shape[-2]
    Postconditions:
        Define
            M := \prod_i m[i]
        \forall r, i, j:
            -return_r <= M_{r,i} - M_{r,j} <= return_r
    """
    partial_products_l = [m[0]]
    partial_products_r = [m[-1]]
    for ml, mr in zip(m[1:-1], reversed(m[1:-1])):
        partial_products_l.append(partial_products_l[-1] @ ml)
        partial_products_r.append(mr @ partial_products_r[-1])
    max_row_diffs = [
        max_row_diffs_per_dim_2(l, r)
        for l, r in zip(partial_products_l, reversed(partial_products_r))
    ]
    # all estimates in max_row_diffs are valid, so we can reduce over them
    max_row_diffs_stacked = torch.stack(max_row_diffs, dim=-1)
    return max_row_diffs_stacked.min(dim=-1).values


# %%
@torch.no_grad()
def bound_max_row_diff_by_SVD(
    *matrices: Tensor,
) -> Tuple[Float[Tensor, ""], Tuple[Tensor, ...]]:  # noqa: F722
    r"""
    Let M denote the product of the elements of `matrices` (under matrix multiplication)

    Complexity: max_{a, b s.t. \exists m\in matrices, m.shape = (a, b)} O(a b min(a, b))

    We compute an upper bound on the difference between elements in the same row of the product of the matrices:
    Since $\sigma_1(M) = \sup_x \| M x \| / \|x\|$, considering vectors with one 1, one -1, and zero elsewhere, the maximum difference between elements in a row is $\sqrt{2} \sigma_1(M)$.
    This is the value we return, computing an upper bound on the first singular value by multiplying the first singular values of each matrix.

    Preconditions:
        the matrices in `matrices` can be multiplied
    Postconditions:
        forall r.
          max_{i,j} M_{r, i} - M_{r, j} <= return[0]
        return[1] == matrices
    """
    # take the product of the first singular values in each matrix to get a bound on the singular value of the product
    prod_max_singular = torch.tensor(
        [torch.linalg.matrix_norm(m, ord=2) for m in matrices]
    ).prod()
    # since \sigma_1(M) = \sup_x \| M x \| / \|x\|, considering vectorswith one 1, one -1, and zero elsewhere, the maximum difference between elements in a row is sqrt(2) * \sigma_1(M)
    return (
        prod_max_singular * np.sqrt(2),
        matrices,
    )
