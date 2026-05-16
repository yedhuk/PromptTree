from __future__ import annotations

import base64
import os
from collections import defaultdict
from pathlib import Path

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

import prompttree as pt
from prompttree.models.node import RegistryNode

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="PromptTree",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
        .block-container { padding: 2.5rem 2rem 1rem; }
        .pt-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
        .pt-meta-row { display: flex; flex-wrap: wrap; gap: 1.5rem; margin: 0.5rem 0 1rem; }
        .pt-meta-item { display: flex; flex-direction: column; }
        .pt-meta-label {
            font-size: 0.67rem; text-transform: uppercase; font-weight: 600;
            letter-spacing: 0.08em; color: #9ca3af; margin-bottom: 4px;
        }
        .pt-meta-value {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.8rem; color: #374151;
        }
        div[data-testid="stCodeBlock"] pre {
            white-space: pre-wrap; word-break: break-word; font-size: 0.82rem;
        }
        div[data-testid="stSelectbox"] > div { font-size: 0.88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Engine ────────────────────────────────────────────────────────────────────

STORAGE = os.environ.get("PROMPTTREE_STORAGE", ".prompttree")

MODELS = [
    "gpt-4o",
    "gpt-4-turbo",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "ollama/llama3",
]

NODE_COLORS = {
    "selected": {"bg": "#fef9c3", "border": "#f59e0b", "font": "#78350f"},
    "labeled":  {"bg": "#dcfce7", "border": "#86efac", "font": "#14532d"},
    "plain":    {"bg": "#f1f5f9", "border": "#94a3b8", "font": "#334155"},
}


@st.cache_resource
def get_engine() -> pt.PromptTree:
    return pt.PromptTree(storage=STORAGE)


engine = get_engine()

# ── Session state ─────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, object] = {
    "selected_id": None,
    "show_form": False,
    "form_parent_id": None,   # None = new root prompt
    "form_parent_name": "",   # inherited name when branching
    "form_content": "",       # prompt text shared between inline box and dialog
    "form_parent_content": "",  # original parent content — used to block unchanged saves
    "form_parent_model": "",    # parent model pre-selection
    "form_parent_temp": 0.7,    # parent temperature pre-selection
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Tree layout ───────────────────────────────────────────────────────────────

def _compute_positions(
    nodes: list[RegistryNode],
    h_sep: int = 180,
    v_sep: int = 120,
) -> dict[str, tuple[float, float]]:
    """Reingold-Tilford-style top-down tree layout with manual x/y computation."""
    node_map = {n.id: n for n in nodes}
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []

    for n in nodes:
        if n.parent_id and n.parent_id in node_map:
            children[n.parent_id].append(n.id)
        else:
            roots.append(n.id)

    def subtree_width(nid: str) -> int:
        kids = children[nid]
        return max(1, sum(subtree_width(c) for c in kids))

    positions: dict[str, tuple[float, float]] = {}

    def place(nid: str, x_left: float, depth: int) -> None:
        w = subtree_width(nid)
        x = x_left + (w * h_sep) / 2
        y = depth * v_sep
        positions[nid] = (x, y)
        cursor = x_left
        for child_id in children[nid]:
            cw = subtree_width(child_id)
            place(child_id, cursor, depth + 1)
            cursor += cw * h_sep

    cursor = 0.0
    for root_id in roots:
        w = subtree_width(root_id)
        place(root_id, cursor, 0)
        cursor += w * h_sep + h_sep

    return positions


def _build_graph(
    nodes: list[RegistryNode],
    selected_id: str | None,
) -> tuple[list[Node], list[Edge]]:
    rlabels = {v: k for k, v in engine.get_labels().items()}
    positions = _compute_positions(nodes)
    node_map = {n.id: n for n in nodes}

    ag_nodes: list[Node] = []
    ag_edges: list[Edge] = []

    for node in nodes:
        label = rlabels.get(node.id)
        display = node.display_name or label or node.id[:8]
        is_selected = node.id == selected_id

        if is_selected:
            c = NODE_COLORS["selected"]
        elif label:
            c = NODE_COLORS["labeled"]
        else:
            c = NODE_COLORS["plain"]

        x, y = positions.get(node.id, (0.0, 0.0))

        ag_nodes.append(
            Node(
                id=node.id,
                label=display,
                size=22,
                shape="box",
                color={
                    "background": c["bg"],
                    "border": c["border"],
                    "highlight": {"background": c["bg"], "border": c["border"]},
                },
                font={"size": 14, "color": c["font"],
                      "face": "Inter, system-ui, sans-serif", "bold": False},
                borderWidth=2 if is_selected else 1,
                borderWidthSelected=2,
                shadow={"enabled": True, "color": "rgba(0,0,0,0.06)", "size": 6, "x": 0, "y": 2},
                x=x,
                y=y,
            )
        )
        if node.parent_id and node.parent_id in node_map:
            ag_edges.append(
                Edge(
                    source=node.parent_id,
                    target=node.id,
                    color={"color": "#d1d5db", "opacity": 0.9},
                    arrows="to",
                    width=1,
                    smooth={"type": "cubicBezier", "forceDirection": "vertical"},
                )
            )

    return ag_nodes, ag_edges


# ── Full-screen prompt editor dialog ─────────────────────────────────────────

@st.dialog("Edit Prompt", width="large")
def _prompt_editor_dialog() -> None:
    edited = st.text_area(
        "Prompt",
        value=st.session_state.form_content,
        height=520,
        placeholder="Enter prompt. Use {{ variable }} for dynamic values.",
        label_visibility="collapsed",
    )
    apply_col, close_col = st.columns(2)
    with apply_col:
        if st.button("Apply", type="primary", use_container_width=True):
            st.session_state.form_content = edited
            st.rerun()
    with close_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

_logo_b64 = base64.b64encode((ASSETS / "PromptTree_Transparent.png").read_bytes()).decode()
st.markdown(
    f'<img src="data:image/png;base64,{_logo_b64}" '
    f'style="height:72px; width:auto; display:block; margin-top:0.75rem; margin-bottom:0.5rem;">',
    unsafe_allow_html=True,
)

names = engine.list_names()
hdr_left, hdr_right = st.columns([4, 1])

with hdr_left:
    placeholder = "— no prompts yet —" if not names else "— select a prompt —"
    options = [placeholder] + names
    chosen = st.selectbox(
        "Prompt",
        options,
        label_visibility="collapsed",
        disabled=not names,
    )
    selected_name: str | None = None if (chosen == placeholder) else chosen

with hdr_right:
    if st.button("＋ New prompt", type="primary", use_container_width=True):
        st.session_state.show_form = True
        st.session_state.form_parent_id = None
        st.session_state.form_parent_name = ""
        st.session_state.selected_id = None
        st.rerun()

st.markdown("---")

# ── Main columns ──────────────────────────────────────────────────────────────

col_tree, col_detail = st.columns([3, 2], gap="large")

# ── Left: tree ────────────────────────────────────────────────────────────────

with col_tree:
    if selected_name is None:
        st.caption("Select a prompt from the dropdown, or create a new one.")
    else:
        family_nodes = engine.get_nodes_by_name(selected_name)

        if not family_nodes:
            st.caption(f"No versions found for **{selected_name}**.")
        else:
            ag_nodes, ag_edges = _build_graph(family_nodes, st.session_state.selected_id)

            # Canvas height: scale with tree depth, minimum 420
            max_depth = max(
                sum(1 for n2 in family_nodes if n2.id == n.parent_id or n.parent_id == n2.id)
                for n in family_nodes
            ) if family_nodes else 0
            canvas_h = max(420, len(family_nodes) * 90 + 120)

            config = Config(
                width="100%",
                height=canvas_h,
                directed=True,
                physics=False,
                hierarchical=False,
            )

            clicked = agraph(nodes=ag_nodes, edges=ag_edges, config=config)

            if clicked and clicked != st.session_state.selected_id:
                st.session_state.selected_id = clicked
                st.session_state.show_form = False
                st.rerun()

# ── Right: detail / form ──────────────────────────────────────────────────────

with col_detail:

    # ── Create / Branch form ──────────────────────────────────────────────────
    if st.session_state.show_form:
        parent_id: str | None = st.session_state.form_parent_id
        is_branch = parent_id is not None

        st.markdown(f"#### {'New branch' if is_branch else 'New prompt'}")
        if is_branch and parent_id is not None:
            st.caption(f"Branching from `{parent_id[:14]}…`")

        # Name: editable for root, locked for branch
        if is_branch:
            inherited_name = st.session_state.form_parent_name
            st.text_input("Prompt name", value=inherited_name, disabled=True)
            form_name = inherited_name
        else:
            form_name = st.text_input("Prompt name", placeholder="e.g. P&ID Analyzer")

        display_name_in = st.text_input(
            "Display name",
            placeholder="e.g. v1, v2-improved, baseline…",
        )

        _prompt_label_col, _expand_col = st.columns([6, 1])
        with _prompt_label_col:
            st.markdown("**Prompt**")
        with _expand_col:
            if st.button("⤢ Expand", use_container_width=True, help="Open full-screen editor"):
                _prompt_editor_dialog()

        content = st.text_area(
            "Prompt",
            value=st.session_state.form_content,
            height=180,
            placeholder="Enter prompt. Use {{ variable }} for dynamic values.",
            label_visibility="collapsed",
        )
        st.session_state.form_content = content

        c1, c2 = st.columns(2)
        with c1:
            label_in = st.text_input("Label (optional)", placeholder="prod, dev…")
        with c2:
            _CUSTOM = "Custom…"
            _parent_model = str(st.session_state.form_parent_model)
            _model_options = MODELS + [_CUSTOM]
            if _parent_model and _parent_model not in MODELS:
                _model_options = [_parent_model] + MODELS + [_CUSTOM]
            _default_model_idx = (
                _model_options.index(_parent_model)
                if _parent_model in _model_options else 0
            )
            model_choice = st.selectbox("Model", _model_options, index=_default_model_idx)
            if model_choice == _CUSTOM:
                model_in = st.text_input("Custom model", placeholder="e.g. mistral/mistral-7b")
            else:
                model_in = model_choice

        _default_temp = float(st.session_state.form_parent_temp)
        temp_in = st.slider("Temperature", 0.0, 1.0, _default_temp, step=0.05)

        st.markdown("")
        btn_col, cancel_col = st.columns(2)
        with btn_col:
            _unchanged = is_branch and content.strip() == str(
                st.session_state.form_parent_content
            ).strip()
            can_save = bool(content.strip() and form_name.strip() and not _unchanged)
            if st.button("Save", type="primary", use_container_width=True, disabled=not can_save):
                saved = engine.save(
                    content=content.strip(),
                    name=form_name.strip(),
                    display_name=display_name_in.strip(),
                    model=model_in,
                    temperature=temp_in,
                    parent_id=parent_id,
                    label=label_in.strip() or None,
                )
                st.session_state.selected_id = saved.id
                st.session_state.show_form = False
                st.session_state.form_content = ""
                st.session_state.form_parent_content = ""
                st.session_state.form_parent_model = ""
                st.session_state.form_parent_temp = 0.7
                st.rerun()
        with cancel_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_form = False
                st.session_state.form_content = ""
                st.session_state.form_parent_content = ""
                st.session_state.form_parent_model = ""
                st.session_state.form_parent_temp = 0.7
                st.rerun()

    # ── Node detail ───────────────────────────────────────────────────────────
    elif st.session_state.selected_id:
        node: RegistryNode | None = engine.get_node(st.session_state.selected_id)

        if node is None:
            st.session_state.selected_id = None
            st.rerun()

        assert node is not None
        rlabels = {v: k for k, v in engine.get_labels().items()}
        label = rlabels.get(node.id)
        heading = node.display_name or label or node.id[:14] + "…"

        st.markdown(f"#### {heading}")
        if node.name:
            st.caption(f"Part of **{node.name}**")

        st.markdown(
            f"""
            <div class="pt-meta-row">
              <div class="pt-meta-item">
                <span class="pt-meta-label">ID</span>
                <span class="pt-meta-value">{node.id[:16]}…</span>
              </div>
              <div class="pt-meta-item">
                <span class="pt-meta-label">Model</span>
                <span class="pt-meta-value">{node.metadata.model}</span>
              </div>
              <div class="pt-meta-item">
                <span class="pt-meta-label">Temp</span>
                <span class="pt-meta-value">{node.metadata.temperature}</span>
              </div>
              <div class="pt-meta-item">
                <span class="pt-meta-label">Created</span>
                <span class="pt-meta-value">{node.metadata.created_at:%Y-%m-%d}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if label:
            st.markdown(f"**Label:** `{label}`")
        if node.parent_id:
            st.caption(f"Parent: `{node.parent_id[:16]}…`")
        if node.metadata.tags:
            st.markdown("**Tags:** " + "  ".join(f"`{t}`" for t in node.metadata.tags))
        if node.metadata.encrypted:
            st.warning("Content is encrypted.", icon="🔒")

        st.divider()
        st.markdown("**Prompt**")
        st.code(node.content, language=None, wrap_lines=True)
        st.divider()

        if st.button("＋  Branch from here", type="primary", use_container_width=True):
            st.session_state.show_form = True
            st.session_state.form_parent_id = node.id
            st.session_state.form_parent_name = node.name
            st.session_state.form_content = node.content
            st.session_state.form_parent_content = node.content
            st.session_state.form_parent_model = node.metadata.model
            st.session_state.form_parent_temp = node.metadata.temperature
            st.rerun()

    # ── Empty detail pane ─────────────────────────────────────────────────────
    else:
        st.markdown("#### Details")
        st.caption("Click a node to inspect it, or create a new prompt.")
