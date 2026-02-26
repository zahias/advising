from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Dict, Iterator, Optional

import streamlit as st


def _perf_enabled() -> bool:
    try:
        return bool(st.query_params.get("perf", "0") == "1")
    except Exception:
        return False


def _perf_store() -> Dict[str, dict]:
    if "_perf" not in st.session_state:
        st.session_state["_perf"] = {"spans": [], "counters": {}}
    return st.session_state["_perf"]


@contextmanager
def perf_span(name: str, meta: Optional[dict] = None) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        elapsed_ms = round((perf_counter() - start) * 1000, 2)
        store = _perf_store()
        store["spans"].append(
            {
                "name": name,
                "elapsed_ms": elapsed_ms,
                "meta": meta or {},
            }
        )
        if _perf_enabled():
            st.caption(f"[perf] {name}: {elapsed_ms} ms")


def record_perf_counter(name: str, value: int = 1) -> None:
    store = _perf_store()
    store["counters"][name] = int(store["counters"].get(name, 0)) + int(value)


def reset_perf() -> None:
    st.session_state["_perf"] = {"spans": [], "counters": {}}

