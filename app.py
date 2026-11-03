"""쇼핑 리스트 앱 (Streamlit) — 3단계: UI 디자인."""
import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒", layout="centered")

DATA_FILE = Path(__file__).parent / "shopping_list.json"
MAX_NAME_LEN = 50
MAX_QTY = 999
FILTERS = ["전체", "미완료", "완료"]

CSS = """
<style>
/* 행 간격 줄이기 */
div[data-testid="stVerticalBlock"] { gap: 0.6rem; }
/* 모바일에서도 한 줄 유지 */
div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; align-items: center; }
div[data-testid="stColumn"] { min-width: 0 !important; }
/* 아이콘 버튼 크기 통일 */
div[data-testid="stColumn"] button { padding: 0.25rem 0.5rem; min-height: 2.2rem; min-width: 2.2rem; white-space: nowrap; }
div[data-testid="stColumn"] button p { white-space: nowrap; }
.empty-state { text-align: center; padding: 2rem 0; color: #6b7a72; }
.empty-state .emoji { font-size: 2.5rem; }
</style>
"""


# ---------------------------------------------------------------- 저장소
def _is_valid_item(item: object) -> bool:
    """아이템 dict가 필수 키와 올바른 타입을 갖췄는지 확인한다."""
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("quantity"), int)
        and isinstance(item.get("checked"), bool)
    )


def load_items() -> list[dict]:
    """JSON 파일에서 아이템 목록을 읽는다. 파일이 없거나 손상되면 빈 리스트를 반환한다."""
    st.session_state["load_error"] = False
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not all(_is_valid_item(i) for i in data):
            raise ValueError("목록 형식이 아닙니다.")
        return data
    except (json.JSONDecodeError, ValueError, OSError):
        st.session_state["load_error"] = True
        return []


def save_items(items: list[dict]) -> None:
    """아이템 목록을 JSON 파일에 UTF-8로 저장한다."""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def init_state() -> None:
    """세션 상태를 처음 한 번만 초기화한다."""
    if "items" not in st.session_state:
        st.session_state["items"] = load_items()
    if "load_error" not in st.session_state:
        st.session_state["load_error"] = False
    if "editing_id" not in st.session_state:
        st.session_state["editing_id"] = None
    if "message" not in st.session_state:
        st.session_state["message"] = None


# ---------------------------------------------------------------- 로직
def _validate_name(name: str) -> str | None:
    """이름을 검증하고 공백을 제거해 반환한다. 유효하지 않으면 None."""
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME_LEN:
        return None
    return name


def _name_error(name: str) -> str:
    """유효하지 않은 이름에 대한 안내 문구를 반환한다."""
    if len((name or "").strip()) > MAX_NAME_LEN:
        return f"아이템 이름은 {MAX_NAME_LEN}자 이하로 입력해 주세요."
    return "아이템 이름을 입력해 주세요."


def _md_escape(text: str) -> str:
    """사용자 입력이 마크다운/LaTeX/이모지 코드로 해석되지 않도록 이스케이프한다."""
    backslash = chr(92)
    special = set(backslash + "`*_{}[]()#+-.!~|<>$:&")
    return "".join(backslash + c if c in special else c for c in text)


def _find(item_id: str) -> dict | None:
    """id로 아이템을 찾는다."""
    for item in st.session_state["items"]:
        if item["id"] == item_id:
            return item
    return None


def add_item(name: str, quantity: int) -> None:
    """검증 후 새 아이템을 추가한다."""
    clean = _validate_name(name)
    if clean is None:
        st.session_state["message"] = _name_error(name)
        return
    st.session_state["items"].append(
        {
            "id": str(uuid.uuid4()),
            "name": clean,
            "quantity": min(MAX_QTY, max(1, int(quantity))),
            "checked": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_items(st.session_state["items"])


def update_item(item_id: str, name: str, quantity: int) -> None:
    """아이템의 이름과 수량을 수정한다."""
    clean = _validate_name(name)
    if clean is None:
        st.session_state["message"] = _name_error(name)
        return
    item = _find(item_id)
    if item is not None:
        item["name"] = clean
        item["quantity"] = min(MAX_QTY, max(1, int(quantity)))
        save_items(st.session_state["items"])
    _end_edit(item_id)


def delete_item(item_id: str) -> None:
    """id로 아이템을 삭제한다."""
    item = _find(item_id)
    if item is None:
        return
    st.session_state["items"] = [i for i in st.session_state["items"] if i["id"] != item_id]
    save_items(st.session_state["items"])
    if st.session_state["editing_id"] == item_id:
        _end_edit(item_id)
    st.toast(f"'{item['name']}'을(를) 삭제했습니다")


def toggle_item(item_id: str) -> None:
    """아이템의 체크 상태를 전환한다."""
    item = _find(item_id)
    if item is not None:
        item["checked"] = not item["checked"]
        save_items(st.session_state["items"])


def clear_checked() -> None:
    """체크된 아이템을 모두 삭제한다."""
    removed = [i for i in st.session_state["items"] if i["checked"]]
    st.session_state["items"] = [i for i in st.session_state["items"] if not i["checked"]]
    save_items(st.session_state["items"])
    editing = st.session_state["editing_id"]
    if editing and any(i["id"] == editing for i in removed):
        _end_edit(editing)
    if removed:
        st.toast(f"{len(removed)}개 항목을 삭제했습니다")


# ---------------------------------------------------------------- 편집 모드
def start_edit(item_id: str) -> None:
    """해당 아이템을 편집 모드로 전환한다 (한 번에 하나만)."""
    item = _find(item_id)
    if item is None:
        return
    prev = st.session_state["editing_id"]
    if prev and prev != item_id:
        _end_edit(prev)
    st.session_state["editing_id"] = item_id
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = item["quantity"]


def _end_edit(item_id: str) -> None:
    """편집 모드를 종료하고 편집용 위젯 상태를 정리한다."""
    st.session_state["editing_id"] = None
    st.session_state.pop(f"edit_name_{item_id}", None)
    st.session_state.pop(f"edit_qty_{item_id}", None)


def cancel_edit(item_id: str) -> None:
    """편집을 취소한다."""
    _end_edit(item_id)


def save_edit(item_id: str) -> None:
    """편집 입력값으로 아이템을 저장한다."""
    update_item(
        item_id,
        st.session_state.get(f"edit_name_{item_id}", ""),
        st.session_state.get(f"edit_qty_{item_id}", 1),
    )


def submit_add() -> None:
    """추가 폼 제출 콜백."""
    add_item(st.session_state.get("add_name", ""), st.session_state.get("add_qty", 1))


# ---------------------------------------------------------------- 화면
def render_summary(items: list[dict]) -> None:
    """전체/완료 개수와 진행률을 표시한다."""
    total = len(items)
    done = sum(1 for i in items if i["checked"])
    percent = round(done / total * 100) if total else 0
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:baseline'>"
        f"<span>전체 <b>{total}</b>개 · 완료 <b>{done}</b>개</span><b>{percent}%</b></div>",
        unsafe_allow_html=True,
    )
    st.progress(done / total if total else 0.0)


def render_row(item: dict) -> None:
    """아이템 한 줄(일반 모드 또는 편집 모드)을 그린다."""
    iid = item["id"]
    if st.session_state["editing_id"] == iid:
        with st.container(border=True):
            st.caption("✏️ 수정 중")
            c_name, c_qty, c_save, c_cancel = st.columns([4, 2, 1.8, 1.8])
            c_name.text_input("이름", key=f"edit_name_{iid}", max_chars=MAX_NAME_LEN,
                              label_visibility="collapsed")
            c_qty.number_input("수량", min_value=1, max_value=MAX_QTY, step=1, key=f"edit_qty_{iid}",
                               label_visibility="collapsed")
            c_save.button("저장", key=f"save_{iid}", on_click=save_edit, args=(iid,),
                          type="primary", help="변경 사항 저장")
            c_cancel.button("취소", key=f"cancel_{iid}", on_click=cancel_edit, args=(iid,),
                            help="수정 취소")
        return

    c_chk, c_name, c_qty, c_edit, c_del = st.columns([0.7, 4, 1.1, 1.1, 1.1])
    c_chk.checkbox("완료", value=item["checked"], key=f"chk_{iid}",
                   on_change=toggle_item, args=(iid,), label_visibility="collapsed")
    safe_name = _md_escape(item["name"])
    c_name.markdown(f":gray[~~{safe_name}~~]" if item["checked"] else safe_name)
    c_qty.markdown(f":gray[x{item['quantity']}]")
    c_edit.button("✏️", key=f"edit_{iid}", on_click=start_edit, args=(iid,), help="수정")
    c_del.button("🗑️", key=f"del_{iid}", on_click=delete_item, args=(iid,), help="삭제")


def main() -> None:
    """앱 진입점."""
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🛒 쇼핑 리스트")

    if st.session_state["load_error"]:
        st.warning("저장된 데이터 파일이 손상되어 빈 리스트로 시작했습니다.")
    if st.session_state["message"]:
        st.warning(st.session_state["message"])
        st.session_state["message"] = None

    items = st.session_state["items"]
    render_summary(items)

    with st.form("add_form", clear_on_submit=True):
        c_name, c_qty, c_btn = st.columns([4, 2.2, 1.8])
        c_name.text_input("이름", key="add_name", max_chars=MAX_NAME_LEN,
                          placeholder="살 물건 (예: 우유)", label_visibility="collapsed")
        c_qty.number_input("수량", min_value=1, max_value=MAX_QTY, value=1, step=1, key="add_qty",
                           label_visibility="collapsed")
        c_btn.form_submit_button("추가", on_click=submit_add, type="primary")
        st.caption(f"수량은 1~{MAX_QTY}까지 입력할 수 있어요.")

    mode = st.radio("보기", FILTERS, horizontal=True, key="filter", label_visibility="collapsed")
    if mode == "미완료":
        visible = [i for i in items if not i["checked"]]
    elif mode == "완료":
        visible = [i for i in items if i["checked"]]
    else:
        visible = list(items)

    with st.container(border=True):
        if not items:
            st.markdown(
                "<div class='empty-state'><div class='emoji'>🧺</div>"
                "리스트가 비어 있어요.<br>살 물건을 추가해 보세요!</div>",
                unsafe_allow_html=True,
            )
        elif not visible:
            st.markdown(
                "<div class='empty-state'><div class='emoji'>🔍</div>해당하는 항목이 없어요.</div>",
                unsafe_allow_html=True,
            )
        for item in visible:
            render_row(item)

    _, c_clear = st.columns([2, 3])
    c_clear.button("체크된 항목 모두 지우기", on_click=clear_checked, use_container_width=True,
                   disabled=not any(i["checked"] for i in items))


if __name__ == "__main__":
    main()
