import streamlit as st
import pandas as pd
import numpy as np
import os

# ================= 基础配置 =================
st.set_page_config(page_title="智慧成绩管理平台", layout="wide", page_icon="🏫")

MAIN = ["语文", "数学", "英语"]
ELEC = ["物理", "化学", "生物", "历史", "地理", "政治"]
SUBJECTS = MAIN + ELEC
MAX_SCORE = {s: 150 for s in MAIN} | {s: 100 for s in ELEC}
GRADES = ["初一", "初二", "初三", "高一", "高二", "高三"]
CLASSES = ["1班", "2班", "3班", "4班"]
ADMIN_PWD = "123456"
DATA_DIR = "成绩数据"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= 通用样式 =================
st.markdown("""
<style>
    .block-container {padding-top:1.5rem; max-width:1250px;}
    [data-testid="stMetric"] {
        background:white; padding:1rem 1.2rem; border-radius:12px;
        border:1px solid #e3e8ef; box-shadow:0 1px 3px rgba(0,0,0,0.06);}
    [data-testid="stMetricValue"] {color:#1a3a6b;}
    .stDataFrame, [data-testid="stTable"] {
        border-radius:10px; overflow:hidden;
        box-shadow:0 1px 4px rgba(0,0,0,0.08);}
    [data-testid="stSidebar"] {background:#f0f4fa;}
</style>""", unsafe_allow_html=True)

def header(title, sub=""):
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a3a6b 0%,#2d5aa0 100%);
                color:white;padding:1.1rem 1.8rem;border-radius:12px;
                border-left:8px solid #c9a227;margin-bottom:1.2rem;
                box-shadow:0 2px 8px rgba(0,0,0,0.15);'>
        <h2 style='margin:0;letter-spacing:2px;font-size:1.5rem;'>🏫 {title}</h2>
        {f"<p style='margin:0.3rem 0 0;opacity:0.85;font-size:0.9rem;'>{sub}</p>" if sub else ""}
    </div>""", unsafe_allow_html=True)

def card(body, border="#1a3a6b"):
    st.markdown(f"""
    <div style='background:white;padding:1rem 1.2rem;border-radius:12px;
                border:1px solid #e3e8ef;border-left:5px solid {border};
                box-shadow:0 1px 4px rgba(0,0,0,0.06);margin-bottom:0.8rem;'>
        {body}</div>""", unsafe_allow_html=True)

# ================= AI 模块（智谱清言 · HTTP 直连版）=================
import requests

AI_KEY = st.secrets.get("ZHIPU_KEY", "")
AI_OK = bool(AI_KEY)

def ai_chat(prompt):
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {AI_KEY}"}
    body = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def ai_section(title, prompt, placeholder="AI 分析"):
    """统一的 AI 功能块"""
    if not AI_OK:
        st.info("💡 AI 功能未启用：请安装 zhipuai 并在 .streamlit/secrets.toml 配置密钥")
        return
    if st.button(f"🤖 {title}", type="primary"):
        with st.spinner("AI 正在分析…"):
            try:
                text = ai_chat(prompt)
                card(f"<p style='white-space:pre-wrap;line-height:1.8;'>{text}</p>",
                     border="#c9a227")
            except Exception as e:
                st.error(f"AI 调用失败：{e}")
    else:
        st.caption(placeholder)

# ================= 数据函数 =================
def grade_dir(grade):
    d = os.path.join(DATA_DIR, grade)
    os.makedirs(d, exist_ok=True)
    return d

def exam_file(grade, exam):
    return os.path.join(grade_dir(grade), f"{exam}.csv")

def load_exam(grade, exam):
    f = exam_file(grade, exam)
    if os.path.exists(f):
        df = pd.read_csv(f, index_col=0)
        for c in ("班级", "姓名"):
            df[c] = (df[c].fillna("").astype(str)
                         .str.replace("\u3000", " ", regex=False).str.strip())
        df = df[df["姓名"] != ""].copy()
        return df
    return pd.DataFrame(columns=["班级", "姓名"] + SUBJECTS)

def list_exams(grade):
    return sorted(f[:-4] for f in os.listdir(grade_dir(grade)) if f.endswith(".csv"))

def total_of(row):
    s = row[SUBJECTS].dropna()
    return s.sum() if len(s) >= 4 else np.nan

# ================= 侧边栏 =================
st.sidebar.markdown("### 🏫 智慧成绩管理平台")
page = st.sidebar.radio("选择身份", ["🎓 学生端", "👨‍🏫 老师端", "📋 主任端"])
grade = st.sidebar.selectbox("选择年级", GRADES)
st.sidebar.divider()
st.sidebar.caption("© 2026 · 智慧校园 · AI 由智谱清言提供")

# ================= 老师端 =================
if page == "👨‍🏫 老师端":
    header("老师端 · 成绩录入", f"{grade}年级")
    exam = st.text_input("① 考试名称（如：2026期中）", key="t_exam")
    subject = st.selectbox("② 你教的科目", SUBJECTS)
    cls = st.selectbox("③ 选择班级", CLASSES)

    if exam == "":
        st.warning("请先填写考试名称！")
        st.stop()
    df = load_exam(grade, exam)

    class_df = df[df["班级"] == cls]
    st.markdown(f"#### 给 {grade}{cls} 录入「{subject}」成绩（满分 {MAX_SCORE[subject]}）")
    new_scores = {}
    for _, r in class_df.iterrows():
        new_scores[r["姓名"]] = st.number_input(
            r["姓名"], min_value=0, max_value=MAX_SCORE[subject], step=1,
            value=int(r[subject]) if pd.notna(r[subject]) else 0,
            key=f"{grade}_{exam}_{cls}_{subject}_{r['姓名']}")

    c1, c2 = st.columns(2)
    new_name = c1.text_input("④ 新学生姓名（该班还没有的学生）")
    if c2.button("➕ 添加新学生"):
        name_clean = new_name.replace("\u3000", " ").strip()
        if not name_clean:
            st.warning("姓名不能为空！")
        elif ((df["班级"] == cls) & (df["姓名"] == name_clean)).any():
            st.warning(f"{grade}{cls} 已有学生「{name_clean}」！")
        else:
            row = {"班级": cls, "姓名": name_clean, **{s: np.nan for s in SUBJECTS}}
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_csv(exam_file(grade, exam))
            st.success(f"已添加 {grade}{cls} {name_clean}")
            st.rerun()

    if st.button("💾 保存全班成绩", type="primary") and len(new_scores) > 0:
        for name, score in new_scores.items():
            df.loc[(df["班级"] == cls) & (df["姓名"] == name), subject] = score
        df.to_csv(exam_file(grade, exam))
        st.success(f"【{grade}·{exam}】{cls} 的 {subject} 成绩已保存！")

    # ---- AI：班情分析 ----
    if class_df.shape[0] > 0:
        st.divider()
        st.markdown("#### 🤖 AI 班情分析")
        filled = class_df[class_df[subject].notna()]
        if filled.shape[0] == 0:
            st.info("先保存成绩，AI 才能分析。")
        else:
            stat = (f"班级：{grade}{cls}；科目：{subject}；满分：{MAX_SCORE[subject]}\n"
                    f"参考人数：{len(filled)}；平均分：{filled[subject].mean():.1f}；"
                    f"最高分：{filled[subject].max():.0f}；最低分：{filled[subject].min():.0f}；"
                    f"标准差：{filled[subject].std():.1f}\n"
                    f"分数分布：{filled[subject].value_counts(bins=5).to_string()}")
            ai_section("生成班情分析（可发家长群）",
                f"你是一位班主任。请根据以下班级「{subject}」成绩统计，写一段200字左右的"
                f"班情分析，语气正式得体，适合发到家长群：先总体评价，再指出亮点与不足，"
                f"最后给家长2-3条配合建议。\n\n{stat}",
                "点击生成可直接发家长群的班情分析文字")

        st.download_button("📥 下载本班成绩表（CSV）",
            class_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{grade}_{exam}_{cls}.csv")

# ================= 学生端 =================
elif page == "🎓 学生端":
    header("学生端 · 我的成绩", f"{grade}年级")
    exams = list_exams(grade)
    if not exams:
        st.info("本年级还没有考试数据。")
        st.stop()
    exam = st.selectbox("选择考试", exams)
    df = load_exam(grade, exam)
    cls = st.selectbox("选择你的班级", sorted(df["班级"].unique()))
    name = st.selectbox("选择你的姓名", df[df["班级"] == cls]["姓名"].tolist())

    d = df.copy()
    d["总分"] = d.apply(total_of, axis=1)
    for s in SUBJECTS + ["总分"]:
        d[s + "班排"] = d[d["班级"] == cls][s].rank(ascending=False, method="min")
        d[s + "年排"] = d[s].rank(ascending=False, method="min")
    rows_found = d[(d["班级"] == cls) & (d["姓名"] == name)]
    if rows_found.empty:
        st.warning("未找到该学生的记录，请联系老师核对名单。")
        st.stop()
    r = rows_found.iloc[0]

    m1, m2 = st.columns(2)
    m1.metric("📊 总分", f"{r['总分']:.0f} 分" if pd.notna(r['总分']) else "科目未录完")
    m2.metric("🏅 年级排名",
              f"第{r['总分年排']:.0f} 名" if pd.notna(r['总分']) else "-")

    rows = []
    for s in SUBJECTS:
        if pd.notna(r[s]):
            rows.append({"科目": s, "分数": r[s], "满分": MAX_SCORE[s],
                         "班级排名": f"第{r[s+'班排']:.0f}名",
                         "年级排名": f"第{r[s+'年排']:.0f}名"})
        else:
            rows.append({"科目": s, "分数": "未录入", "满分": MAX_SCORE[s],
                         "班级排名": "-", "年级排名": "-"})
    if pd.notna(r["总分"]):
        rows.append({"科目": "总分", "分数": r["总分"], "满分": "",
                     "班级排名": f"第{r['总分班排']:.0f}名",
                     "年级排名": f"第{r['总分年排']:.0f}名"})
    st.table(pd.DataFrame(rows).astype(str))

    # ---- AI：个性化学习诊断 ----
    st.markdown("#### 🤖 AI 学习诊断")
    valid = [x for x in rows if isinstance(x["分数"], (int, float, np.floating))]
    if not valid:
        st.info("成绩还没录完，AI 暂时无法分析。")
    else:
        score_text = pd.DataFrame(valid).to_string(index=False)
        ai_section("生成我的专属学习建议",
            f"你是一位温和耐心的班主任。请根据以下学生成绩单，用鼓励的语气写一段"
            f"150字左右的个性化分析：指出1-2个优势学科和薄弱学科，各给出1条具体"
            f"可执行的学习建议。不要提具体名次数字，避免攀比焦虑。\n\n{score_text}",
            "AI 老师将为你分析优势与不足，给出专属建议")

    # ---- 历史对比 ----
    other = [e for e in exams if e != exam]
    if other:
        last = other[-1]
        df2 = load_exam(grade, last)
        r2 = df2[(df2["班级"] == cls) & (df2["姓名"] == name)]
        if r2.shape[0] > 0:
            st.subheader(f"📈 与上次考试【{last}】对比")
            rows2 = []
            for s in SUBJECTS:
                if pd.notna(r[s]) and pd.notna(r2.iloc[0][s]):
                    diff = r[s] - r2.iloc[0][s]
                    arrow = "🔺" if diff > 0 else ("🔻" if diff < 0 else "➖")
                    rows2.append({"科目": s, "上次": r2.iloc[0][s], "本次": r[s],
                                  "变化": f"{diff:+.0f} {arrow}"})
            if rows2:
                st.table(pd.DataFrame(rows).astype(str))

    st.caption("💡 打印/保存 PDF：按 Ctrl + P")

# ================= 主任端 =================
else:
    header("主任端 · 教学质量总览", f"{grade}年级")
    pwd = st.text_input("请输入管理员密码", type="password")
    if pwd != ADMIN_PWD:
        if pwd:
            st.error("密码错误！")
        st.stop()

    exams = list_exams(grade)
    if not exams:
        st.info("本年级还没有数据。")
        st.stop()
    exam = st.selectbox("选择考试", exams)
    df = load_exam(grade, exam)
    df["总分"] = df.apply(total_of, axis=1)

    st.markdown("#### 🏆 班级总分排名")
    cls_avg = df.groupby("班级")["总分"].mean().round(1).sort_values(ascending=False)
    rank_df = cls_avg.reset_index()
    rank_df.columns = ["班级", "总分平均分"]
    st.table(rank_df)

    st.markdown("#### 📚 各科班级平均分对比")
    sub_avg = df.groupby("班级")[SUBJECTS].mean().round(1)
    st.bar_chart(sub_avg.T)

    # ---- AI：年级教学质量报告 ----
    st.divider()
    st.markdown("#### 🤖 AI 教学质量报告")
    stat = f"各班总分平均分：\n{rank_df.to_string(index=False)}\n\n各科各班平均分：\n{sub_avg.to_string()}"
    ai_section("生成年级教学质量分析报告",
        f"你是学校教务主任。请根据以下年级考试数据，写一份300字左右的教学质量"
        f"分析报告：总体情况、优势班级与学科、需要关注的班级与学科、改进建议。"
        f"\n\n{stat}",
        "AI 将生成年级层面的教学质量分析")
