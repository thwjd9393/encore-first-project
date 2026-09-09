from pathlib import Path

import streamlit as st

from src.common.api_client import patch_json


def load_profile_edit_css():
    """프로필 수정 화면 전용 CSS를 적용한다."""

    css_path = (
        Path(__file__).parent.parent
        / "styles"
        / "profile_edit.css"
    )
    css = css_path.read_text(encoding="utf-8")
    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


def render_html(html):
    """HTML 문자열을 Streamlit 화면에 출력한다."""

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_profile_edit(user):
    """로그인한 사용자의 프로필 수정 화면을 보여준다."""

    load_profile_edit_css()

    render_html(
        '<div class="profile-edit-header">'
        '<h1 class="profile-edit-title">프로필 수정</h1>'
        '<p class="profile-edit-subtitle">'
        '내 정보를 수정하고, 더 나은 맛집 경험을 만들어보세요.'
        '</p>'
        '</div>'
    )

    with st.container(
        key="profile_edit_card",
        border=False,
    ):

        render_html(
            '<h2 class="profile-edit-section-title">'
            '기본 정보'
            '</h2>'
        )

        nickname_label_col, nickname_input_col = st.columns(
            [1.2, 6],
            vertical_alignment="center",
        )

        with nickname_label_col:
            render_html(
                '<div class="profile-edit-field-label">'
                '닉네임 '
                '<span class="profile-edit-required">*</span>'
                '</div>'
            )

        with nickname_input_col:
            with st.container(
                key="profile_nickname_field",
                border=False,
            ):
                nickname = st.text_input(
                    "닉네임",
                    value=user.get("nickname", ""),
                    max_chars=45,
                    key="profile_edit_nickname",
                    label_visibility="collapsed",
                )
                render_html(
                    f'<div class="profile-edit-count">'
                    f'{len(nickname)}/45'
                    f'</div>'
                )

        email_label_col, email_input_col = st.columns(
            [1.2, 6],
            vertical_alignment="top",
        )

        with email_label_col:
            render_html(
                '<div class="profile-edit-field-label">'
                '이메일'
                '</div>'
            )

        with email_input_col:
            st.text_input(
                "이메일",
                value=user.get("email", ""),
                disabled=True,
                key="profile_edit_email",
                label_visibility="collapsed",
            )
            render_html(
                '<p class="profile-edit-help">'
                '이메일은 변경할 수 없습니다.'
                '</p>'
            )

        password_label_col, password_content_col = st.columns(
            [1.2, 6],
            vertical_alignment="center",
        )

        with password_label_col:
            render_html(
                '<div class="profile-edit-field-label">'
                '비밀번호'
                '</div>'
            )

        with password_content_col:
            with st.container(
                key="profile_password_box",
                border=False,
            ):
                password_info_col, password_button_col = st.columns(
                    [4, 1.6],
                    vertical_alignment="center",
                )

                with password_info_col:
                    render_html(
                        '<div class="profile-password-info">'
                        '<div class="profile-password-icon">🔒</div>'
                        '<div class="profile-password-copy">'
                        '<p class="profile-password-title">'
                        '비밀번호를 안전하게 관리하고 계신가요?'
                        '</p>'
                        '<p class="profile-password-description">'
                        '주기적으로 비밀번호를 변경하여 '
                        '계정을 안전하게 보호하세요.'
                        '</p>'
                        '</div>'
                        '</div>'
                    )

                with password_button_col:
                    if st.button(
                        "비밀번호 변경",
                        key="go_password_change",
                        use_container_width=True,
                    ):
                        st.session_state["mypage_view"] = "password"
                        st.rerun()

        render_html(
            '<div class="profile-edit-divider"></div>'
        )

        empty_col, cancel_col, save_col = st.columns(
            [3.8, 1.2, 1.5],
            vertical_alignment="center",
        )

        with cancel_col:
            if st.button(
                "취소",
                key="profile_edit_cancel",
                use_container_width=True,
            ):
                st.session_state["mypage_view"] = "main"
                st.rerun()

        save_busy = st.session_state.get("profile_save_busy", False)
        with save_col:
            if st.button(
                "저장 중…" if save_busy else "저장하기",
                key="profile_edit_save",
                type="primary",
                use_container_width=True,
                disabled=save_busy,
            ):
                cleaned_nickname = nickname.strip()

                if not cleaned_nickname:
                    st.error("닉네임을 입력해주세요.")
                    return

                if len(cleaned_nickname) > 45:
                    st.error("닉네임은 45자 이하로 입력해주세요.")
                    return

                access_token = st.session_state.get("access_token")
                if not access_token:
                    st.error("로그인이 필요합니다.")
                    return

                st.session_state.profile_save_busy = True
                result = patch_json(
                    "/users/me",
                    json_body={"nickname": cleaned_nickname},
                    access_token=access_token,
                )
                st.session_state.profile_save_busy = False

                if result.get("status_code") == 401:
                    st.session_state.clear()
                    st.session_state.page = "login"
                    st.session_state.login_notice = (
                        "로그인이 만료되었습니다. 다시 로그인해 주세요."
                    )
                    st.rerun()

                if result.get("ok"):
                    updated = result.get("data") or {}
                    session_user = st.session_state.get("user") or {}
                    session_user["nickname"] = (
                        updated.get("nickname") or cleaned_nickname
                    )
                    st.session_state.user = session_user
                    st.success("닉네임이 저장되었습니다.")
                    return

                status_code = result.get("status_code")
                message = (result.get("error") or {}).get("message")
                if status_code == 409:
                    st.error(message or "이미 사용 중인 닉네임입니다.")
                elif status_code == 422:
                    st.error(message or "닉네임을 다시 확인해 주세요.")
                else:
                    st.error(message or "닉네임을 저장하지 못했습니다.")


def render_password_change():
    """비밀번호 변경 화면."""

    load_profile_edit_css()

    render_html(
        '<div class="profile-edit-header">'
        '<h1 class="profile-edit-title">비밀번호 변경</h1>'
        '<p class="profile-edit-subtitle">'
        '현재 비밀번호를 확인한 뒤 새 비밀번호로 변경합니다.'
        '</p>'
        '</div>'
    )

    with st.container(key="password_change_card", border=False):
        current_password = st.text_input(
            "현재 비밀번호",
            type="password",
            key="password_change_current",
        )
        new_password = st.text_input(
            "새 비밀번호",
            type="password",
            key="password_change_new",
        )
        new_password_confirm = st.text_input(
            "새 비밀번호 확인",
            type="password",
            key="password_change_confirm",
        )

        empty_col, cancel_col, save_col = st.columns(
            [3.8, 1.2, 1.5],
            vertical_alignment="center",
        )

        with cancel_col:
            if st.button(
                "취소",
                key="password_change_cancel",
                use_container_width=True,
            ):
                st.session_state["mypage_view"] = "profile"
                st.rerun()

        change_busy = st.session_state.get("password_change_busy", False)
        with save_col:
            if st.button(
                "변경 중…" if change_busy else "변경하기",
                key="password_change_save",
                type="primary",
                use_container_width=True,
                disabled=change_busy,
            ):
                if not current_password:
                    st.error("현재 비밀번호를 입력해주세요.")
                    return
                if not new_password:
                    st.error("새 비밀번호를 입력해주세요.")
                    return
                if len(new_password) < 8:
                    st.error("비밀번호는 8자 이상 입력해주세요.")
                    return
                if len(new_password) > 128:
                    st.error("비밀번호는 128자 이하로 입력해주세요.")
                    return
                if new_password != new_password_confirm:
                    st.error("새 비밀번호가 서로 다릅니다.")
                    return
                if current_password == new_password:
                    st.error("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
                    return

                access_token = st.session_state.get("access_token")
                if not access_token:
                    st.error("로그인이 필요합니다.")
                    return

                st.session_state.password_change_busy = True
                result = patch_json(
                    "/auth/password",
                    json_body={
                        "current_password": current_password,
                        "new_password": new_password,
                    },
                    access_token=access_token,
                )
                st.session_state.password_change_busy = False

                if result.get("ok"):
                    st.session_state.clear()
                    st.session_state.page = "login"
                    st.session_state.login_notice = (
                        "비밀번호가 변경되었습니다. 다시 로그인해 주세요."
                    )
                    st.rerun()

                status_code = result.get("status_code")
                message = (result.get("error") or {}).get("message")
                if status_code == 401:
                    st.error(message or "현재 비밀번호가 올바르지 않습니다.")
                elif status_code == 422:
                    st.error(message or "입력값을 다시 확인해 주세요.")
                else:
                    st.error(message or "비밀번호를 변경하지 못했습니다.")
