from textwrap import dedent

import streamlit as st

CHART_PRIMARY = "#FF7A00"
CHART_SECONDARY = "#FFB368"
CHART_SUCCESS = "#2E7D32"
CHART_WARNING = "#E08A00"
CHART_DANGER = "#C62828"
CHART_TEXT = "#333333"
CHART_MUTED = "#666666"
CHART_BORDER = "#DDDDDD"
CHART_CATEGORY_COLORS = [
    CHART_PRIMARY,
    CHART_SECONDARY,
    CHART_WARNING,
    CHART_MUTED,
]


def render_page_header(title, caption=None):
    caption_html = (
        f'<p class="playeat-page-caption">{caption}</p>' if caption else ""
    )
    st.markdown(
        dedent(
            f"""
            <div class="playeat-page-heading">
                <h1 class="playeat-page-title">{title}</h1>
                {caption_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_section_title(title, caption=None):
    caption_html = (
        f'<p class="playeat-section-side-caption">{caption}</p>' if caption else ""
    )
    st.markdown(
        dedent(
            f"""
            <div class="playeat-section-heading">
                <h2 class="playeat-section-title">{title}</h2>
                {caption_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_toolbar_row():
    return st.container(
        horizontal=True,
        vertical_alignment="center",
        horizontal_alignment="distribute",
        gap="small",
        wrap=False,
    )


def render_toolbar_actions():
    return st.container(
        horizontal=True,
        vertical_alignment="center",
        horizontal_alignment="right",
        gap="small",
        wrap=False,
        width="content",
    )


def render_status_card(kind, title, message, meta_text=None):
    meta_html = ""
    if meta_text:
        meta_html = f'<p class="playeat-status-meta">{meta_text}</p>'

    st.markdown(
        dedent(
            f"""
            <div class="playeat-status-card">
                <p class="playeat-status-label {kind}">{title}</p>
                <p class="playeat-status-body">{message}</p>
                {meta_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_loading_state(message="조회 중입니다."):
    render_status_card("loading", "Loading", message)


def render_empty_state(message, next_action=None):
    action_text = next_action or "기간이나 필터를 바꾼 뒤 다시 적용해 주세요."
    render_status_card("empty", "Empty", f"{message} {action_text}")


def render_error_state(message, request_id=None, next_action=None):
    action_text = next_action or "잠시 후 다시 조회해 주세요."
    meta_text = None
    if request_id:
        meta_text = f"request_id: {request_id}"
    render_status_card(
        "error",
        "Error",
        f"{message} {action_text}",
        meta_text=meta_text,
    )


def render_sentiment_cards(items):
    columns = st.columns(len(items) or 1)
    for column, item in zip(columns, items):
        with column:
            tone = item.get("tone") or "empty"
            value = item.get("value")
            count_text = item.get("count_text") or ""
            display_value = "데이터 없음" if value in (None, "") else value
            extra = f'<p class="playeat-page-caption">{count_text}</p>' if count_text else ""
            st.markdown(
                dedent(
                    f"""
                    <div class="playeat-sentiment-card {tone}">
                        <p class="label">{item.get("label")}</p>
                        <p class="value">{display_value}</p>
                        {extra}
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )


def render_summary_strip(items):
    item_html = []
    for item in items:
        value = item.get("value")
        display_value = "데이터 없음" if value in (None, "") else value
        item_html.append(
            dedent(
                f"""
                <div class="playeat-summary-item">
                    <p class="label">{item.get("label")}</p>
                    <p class="value">{display_value}</p>
                </div>
                """
            )
        )
    st.markdown(
        f'<div class="playeat-summary-strip">{"".join(item_html)}</div>',
        unsafe_allow_html=True,
    )


def summarize_donut_trend(points):
    ranked = sorted(points, key=lambda point: point["value"], reverse=True)
    top = ranked[0]
    total = sum(point["value"] for point in ranked)
    share = (top["value"] / total) * 100 if total else 0
    return (
        f"최댓값은 {top['label']} {int(top['value'])}건이며 "
        f"전체 {int(total)}건의 {share:.0f}%입니다."
    )


def with_donut_percentages(points):
    total = sum(point["value"] for point in points)
    rows = []
    for point in points:
        value = float(point["value"])
        percent = round((value / total) * 100) if total else 0
        rows.append(
            {
                "label": point["label"],
                "value": value,
                "percent": percent,
                "legend_label": f"{point['label']} {percent}%",
                "percent_label": f"{percent}%",
            }
        )
    return rows


def render_donut_chart(title, points):
    with st.container(border=True):
        valid_points = [
            point
            for point in points
            if point.get("label") and (point.get("value") or 0) > 0
        ]
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            wrap=True,
        ):
            st.subheader(title)
            if valid_points:
                st.caption(summarize_donut_trend(valid_points))
        if not valid_points:
            render_empty_state(
                "표시할 비율이 없습니다.",
                next_action="0% 도넛으로 채우지 않습니다.",
            )
            return

        import pandas as pd
        import altair as alt

        chart_rows = with_donut_percentages(valid_points)
        chart_df = pd.DataFrame(chart_rows)
        color_range = [
            CHART_CATEGORY_COLORS[index % len(CHART_CATEGORY_COLORS)]
            for index in range(len(chart_rows))
        ]
        color_scale = alt.Scale(
            domain=list(chart_df["legend_label"]),
            range=color_range,
        )
        base = alt.Chart(chart_df).encode(
            theta=alt.Theta("value:Q", stack=True),
            color=alt.Color(
                "legend_label:N",
                scale=color_scale,
                legend=alt.Legend(title=None, labelLimit=160),
            ),
            tooltip=[
                alt.Tooltip("label:N", title="항목"),
                alt.Tooltip("value:Q", title="건수"),
                alt.Tooltip("percent:Q", title="비율(%)"),
            ],
        )
        donut = base.mark_arc(innerRadius=48, outerRadius=80)
        labels = base.mark_text(radius=64, size=11).encode(
            text="percent_label:N",
            color=alt.value(CHART_TEXT),
        )
        chart = (donut + labels).properties(height=220).configure_view(strokeWidth=0)
        st.altair_chart(chart)


def render_download_button(label, dataframe, file_name, key, width="stretch"):
    csv_text = dataframe.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label,
        data=csv_text,
        file_name=file_name,
        mime="text/csv",
        icon=":material/download:",
        key=key,
        width=width,
    )
