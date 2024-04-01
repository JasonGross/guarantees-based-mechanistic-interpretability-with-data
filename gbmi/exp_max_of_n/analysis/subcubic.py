from typing import Union, Optional
import torch
from jaxtyping import Float, Integer
from torch import Tensor
from transformer_lens import HookedTransformer
from gbmi.verification_tools.l1h1 import (
    all_EVOU,
    all_PVOU,
)
from gbmi.exp_max_of_n.verification import LargestWrongLogitQuadraticConfig
from gbmi.exp_max_of_n.analysis.quadratic import (
    W_EP_direction_for_tricks,
    find_min_gaps,
)
from gbmi.exp_max_of_n.verification.subcubic import decompose_EQKE_error


@torch.no_grad()
def find_min_gaps_with_EQKE(
    model: HookedTransformer,
    *,
    EVOU: Optional[Float[Tensor, "d_vocab_k d_vocab_out"]] = None,  # noqa: F722
    PVOU: Optional[Float[Tensor, "n_ctx d_vocab_out"]] = None,  # noqa: F722
    W_EP: Optional[Float[Tensor, "d_vocab_q d_model"]] = None,  # noqa: F722
    W_U: Optional[Float[Tensor, "d_model d_vocab_out"]] = None,  # noqa: F722
    sanity_check: bool = True,
    atol: float = 1e-4,
    tricks: LargestWrongLogitQuadraticConfig = LargestWrongLogitQuadraticConfig(),
    use_exact_EQKE: bool = False,
    # svd_EUPU: bool = False,
    attn_scale: Optional[Union[Float[Tensor, ""], float]] = None,  # noqa: F722
    position: Optional[int] = None,
    leave: Optional[bool] = None,
) -> Integer[Tensor, "d_vocab_q d_vocab_max n_ctx_nonmax_copies"]:  # noqa: F722
    if EVOU is None:
        EVOU = all_EVOU(model)
    if PVOU is None:
        PVOU = all_PVOU(model)
    if W_EP is None:
        W_EP = model.W_E + model.W_pos.mean(dim=0, keepdim=True)
    if W_U is None:
        W_U = model.W_U
    if attn_scale is None:
        attn_scale = model.blocks[0].attn.attn_scale
    assert attn_scale is not None

    (
        EQKE_query_key,
        EQKE_pos_err,
        (err_upper_bound, (EQ_err, KE_err)),
    ) = decompose_EQKE_error(model, sanity_check=sanity_check, atol=atol, tricks=tricks)

    err_exact = EQ_err @ KE_err
    cur_EQKE = EQKE_query_key + (err_exact if use_exact_EQKE else 0)
    EQKE_err_upper_bound = torch.tensor(0) if use_exact_EQKE else err_upper_bound

    W_EP_direction = W_EP_direction_for_tricks(W_EP=W_EP, W_U=W_U, tricks=tricks)
    # cur_EUPU_low_rank = EUPU_lowrank if svd_EUPU else None
    # cur_EUPU_high_rank = torch.zeros_like(EUPU) if svd_EUPU else EUPU
    # cur_EUPU_max_err = torch.tensor(0) if not svd_EUPU else EUPU_err_upper_bound

    return find_min_gaps(
        EQKE=cur_EQKE,
        EQKE_err_upper_bound=EQKE_err_upper_bound,
        EQKE_pos_err=EQKE_pos_err,
        EVOU=EVOU,
        PVOU=PVOU,
        tricks=tricks,
        attn_scale=attn_scale,
        position=position,
        leave=leave,
        W_EP=W_EP,
        W_U=W_U,
        W_EP_direction=W_EP_direction,
    )
