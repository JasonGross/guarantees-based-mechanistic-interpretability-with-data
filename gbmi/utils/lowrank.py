from __future__ import annotations
from torch import Tensor
import torch
from jaxtyping import Float
from typing import Union, Optional
import plotly.express as px


def _via_tensor(attr: str):
    def delegate(self: LowRankTensor, *args, **kwargs):
        return getattr(self.totensor(), attr)(*args, **kwargs)

    if hasattr(Tensor, attr):
        reference = getattr(Tensor, attr)
        for docattr in ("__doc__", "__name__"):
            if hasattr(reference, docattr):
                setattr(delegate, docattr, getattr(reference, docattr))
    return delegate


class LowRankTensor:
    def __init__(
        self,
        u: Tensor,
        v: Tensor,
        *,
        check: Union[bool, dict] = False,
        show: bool = True,
        checkparams: Optional[dict] = None,
    ):
        if u.ndim == 1:
            u = u[:, None]
        if v.ndim == 1:
            v = v[None, :]
        assert (
            u.shape[-1] == v.shape[-2]
        ), f"u.shape[-1] must equal v.shape[-2]; u.shape={u.shape}; v.shape={v.shape}"
        self._u = u
        self._v = v
        self._check = bool(check)
        self._checkparams = (
            checkparams
            if checkparams is not None
            else check
            if isinstance(check, dict)
            else {}
        )
        self._show = show

    @property
    def u(self):
        return self._u

    @property
    def v(self):
        return self._v

    def totensor(self) -> Tensor:
        return self.u @ self.v

    def setcheckparams(self, **kwargs):
        self._checkparams = kwargs

    @property
    def T(self):
        return LowRankTensor(self.v.T, self.u.T, check=self._check, show=self._show)

    @torch.no_grad()
    def check(
        self,
        other: Union[Tensor, LowRankTensor],
        show: Optional[bool] = None,
        descr: Optional[str] = None,
        renderer: Optional[str] = None,
        **kwargs,
    ) -> bool:
        if show is None:
            show = self._show
        full_kwargs = dict(self._checkparams)
        full_kwargs.update(kwargs)
        if isinstance(other, LowRankTensor):
            other = other.totensor()
        if torch.allclose(self.totensor(), other, **full_kwargs):
            return True
        descr = "" if descr is None else " " + descr
        if show:
            px.imshow(self.numpy(), title=f"self{descr}").show(renderer=renderer)
            px.imshow(other.numpy(), title=f"other{descr}").show(renderer=renderer)
            px.imshow(
                (self - other).abs().detach().numpy(), title=f"difference{descr}"
            ).show(renderer=renderer)
        return False

    @torch.no_grad()
    def maybe_check(
        self,
        other: Union[Tensor, LowRankTensor],
        show: Optional[bool] = None,
        descr: Optional[str] = None,
        renderer: Optional[str] = None,
        **kwargs,
    ) -> bool:
        return (
            self.check(other, show=show, descr=descr, renderer=renderer, **kwargs)
            if self._check
            else True
        )

    def __matmul__(self, other: Union[Tensor, LowRankTensor]):
        if isinstance(other, LowRankTensor):
            # prefer to keep the dimensions of stored matrices as low as possible
            u, mid, v = self.u, self.v @ other.u, other.v
            if len(mid.shape) <= 1:
                if u.shape[-1] <= v.shape[-2]:
                    v = mid @ v
                else:
                    u = u @ mid
            elif mid.shape[-2] <= mid.shape[-1]:
                v = mid @ v
            else:
                u = u @ mid
        else:
            u, v = self.u, self.v @ other
        result = LowRankTensor(
            u, v, check=self._check, show=self._show, checkparams=self._checkparams
        )
        if self._check:
            assert result.check(self.totensor() @ other, descr="matmul")
        return result

    def __rmatmul__(self, other: Union[Tensor, LowRankTensor]):
        if isinstance(other, LowRankTensor):
            # prefer to keep the dimensions of stored matrices as low as possible
            u, mid, v = other.u, other.v @ self.u, self.v
            if len(mid.shape) <= 1:
                if u.shape[-1] <= v.shape[-2]:
                    v = mid @ v
                else:
                    u = u @ mid
            elif mid.shape[-2] <= mid.shape[-1]:
                v = mid @ v
            else:
                u = u @ mid
        else:
            u, v = other @ self.u, self.v
        result = LowRankTensor(
            u, v, check=self._check, show=self._show, checkparams=self._checkparams
        )
        if self._check:
            assert result.check(other @ self.totensor(), descr="matmul")
        return result

    @torch.no_grad()
    def numpy(self):
        return self.totensor().detach().numpy()

    __add__ = _via_tensor("__add__")
    __radd__ = _via_tensor("__radd__")
    __sub__ = _via_tensor("__sub__")
    __rsub__ = _via_tensor("__rsub__")

    def __repr__(self):
        return f"LowRankTensor(u={self.u!r}, v={self.v!r})"

    def __str__(self):
        return f"LowRankTensor(u={self.u}, v={self.v})"
