import streamlit as st
import pandas as pd
import numpy as np
import os

# ================= 基础配置 =================
st.set_page_config(page_title="十八中附小智慧成绩管理平台", layout="wide", page_icon="🏫")

MAIN = ["语文", "数学", "英语"]
ELEC = ["道德与法治", "科学", "体育", "音乐",  "体育"]
SUBJECTS = MAIN + ELEC
MAX_SCORE =  {s: 100 for s in ELEC}
GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
CLASSES = ["1班", "2班", "3班", "4班", "5班", "6班", "7班", "8班"]
DIRECTOR_PWD = "admin888"   # 主任总密码，可修改
DATA_DIR = "成绩数据"
os.makedirs(DATA_DIR, exist_ok=True)

ACC_FILE, CLS_FILE, PERM_FILE, EXAM_FILE = "accounts.csv", "classes.csv", "perms.csv", "exams.csv"

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
        {f"<p style='margin:0.3rem 0 0;opacity:0.85;font-size:0.9rem;'>{sub}</p >" if sub else ""}
    </div>""", unsafe_allow_html=True)

def card(body, border="#1a3a6b"):
    st.markdown(f"""
    <div style='background:white;padding:1rem 1.2rem;border-radius:12px;
                border:1px solid #e3e8ef;border-left:5px solid {border};
                box-shadow:0 1px 4px rgba(0,0,0,0.06);margin-bottom:0.8rem;'>
        {body}</div>""", unsafe_allow_html=True)

# ================= AI 模块 =================
import requests

AI_KEY = st.secrets.get("ZHIPU_KEY", "")
AI_OK = bool(AI_KEY)

def ai_chat(prompt):
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {AI_KEY}"}
    body = {"model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7}
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def ai_section(title, prompt, placeholder="AI 分析"):
    if not AI_OK:
        st.info("💡 AI 功能未启用：请配置 ZHIPU_KEY 密钥")
        return
    if st.button(f"🤖 {title}", type="primary"):
        with st.spinner("AI 正在分析…"):
            try:
                text = ai_chat(prompt)
                card(f"<p style='white-space:pre-wrap;line-height:1.8;'>{text}</p >",
                     border="#c9a227")
            except Exception as e:
                st.error(f"AI 调用失败：{e}")
    else:
        st.caption(placeholder)

# ================= 数据读写 =================
def _load(f, cols):
    if os.path.exists(f):
        return pd.read_csv(f, dtype=str).fillna("")
    return pd.DataFrame(columns=cols)

def _save(df, f):
    df.to_csv(f, index=False)

def load_accounts():  return _load(ACC_FILE, ["姓名", "密码", "角色", "年级", "班级"])
def save_accounts(df): _save(df, ACC_FILE)
def load_classes():   return _load(CLS_FILE, ["年级", "班级", "班主任"])
def save_classes(df): _save(df, CLS_FILE)
def load_perms():     return _load(PERM_FILE, ["老师", "年级", "班级", "类型", "科目"])
def save_perms(df):   _save(df, PERM_FILE)
def load_exams():     return _load(EXAM_FILE, ["年级", "考试", "参加班级"])
def save_exams(df):   _save(df, EXAM_FILE)

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
        return df[df["姓名"] != ""].copy()
    return pd.DataFrame(columns=["班级", "姓名"] + SUBJECTS)

def list_exams(grade):
    return sorted(f[:-4] for f in os.listdir(grade_dir(grade)) if f.endswith(".csv") and f[:-4] != "")

def total_of(row):
    s = row[SUBJECTS].dropna()
    return s.sum() if len(s) >= 4 else np.nan

# ---------- 业务操作 ----------
def class_roster(grade, cls):
    acc = load_accounts()
    return acc[(acc["角色"] == "学生") & (acc["年级"] == grade) & (acc["班级"] == cls)]

def join_exam(grade, exam, cls):
    """班级参加考试：花名册自动计入成绩表"""
    df = load_exam(grade, exam)
    roster = class_roster(grade, cls)
    new_rows = []
    exist = set(zip(df["班级"], df["姓名"]))
    for _, s in roster.iterrows():
        if (cls, s["姓名"]) not in exist:
            new_rows.append({"班级": cls, "姓名": s["姓名"],
                             **{sub: np.nan for sub in SUBJECTS}})
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df.to_csv(exam_file(grade, exam))
    # 记录参加班级
    exams = load_exams()
    m = (exams["年级"] == grade) & (exams["考试"] == exam)
    if m.any():
        joined = set(filter(None, exams.loc[m, "参加班级"].iloc[0].split("|")))
        joined.add(cls)
        exams.loc[m, "参加班级"] = "|".join(sorted(joined))
        save_exams(exams)

def promote_class(grade, cls):
    """整班升学：初二→初三，初三→高一，高三→毕业（移出）"""
    idx = GRADES.index(grade)
    acc = load_accounts()
    m = (acc["角色"] == "学生") & (acc["年级"] == grade) & (acc["班级"] == cls)
    if idx + 1 < len(GRADES):
        acc.loc[m, "年级"] = GRADES[idx + 1]
        cls_df = load_classes()
        mc = (cls_df["年级"] == grade) & (cls_df["班级"] == cls)
        cls_df.loc[mc, "年级"] = GRADES[idx + 1]
        perm = load_perms()
        mp = (perm["年级"] == grade) & (perm["班级"] == cls)
        perm.loc[mp, "年级"] = GRADES[idx + 1]
        save_classes(cls_df); save_perms(perm)
    else:  # 高三毕业：学生账号保留但标记为已毕业
        acc.loc[m, "年级"] = "已毕业"
    save_accounts(acc)

# ================= 登录 =================
if "logged" not in st.session_state:
    st.session_state.logged = None

if st.session_state.logged is None:
    header("十八中附小智慧成绩管理平台", "请选择身份登录")
    tab_s, tab_t, tab_d = st.tabs(["🎓 学生登录", "👨‍🏫 老师登录", "📋 主任登录"])

    with tab_s:
        s_name = st.text_input("姓名", key="s_name")
        s_pwd = st.text_input("密码", type="password", key="s_pwd")
        if st.button("登录学生端", type="primary"):
            acc = load_accounts()
            hit = acc[(acc["姓名"] == s_name.strip()) & (acc["密码"] == s_pwd)
                      & (acc["角色"] == "学生")]
            if len(hit) > 0:
                u = hit.iloc[0]
                st.session_state.logged = {"name": u["姓名"], "role": "学生",
                                           "grade": u["年级"], "cls": u["班级"]}
                st.rerun()
            else:
                st.error("姓名或密码错误！")

    with tab_t:
        t_name = st.text_input("姓名", key="t_name")
        t_pwd = st.text_input("密码", type="password", key="t_pwd")
        if st.button("登录老师端", type="primary"):
            acc = load_accounts()
            hit = acc[(acc["姓名"] == t_name.strip()) & (acc["密码"] == t_pwd)
                      & (acc["角色"] == "老师")]
            if len(hit) > 0:
                st.session_state.logged = {"name": hit.iloc[0]["姓名"], "role": "老师"}
                st.rerun()
            else:
                st.error("姓名或密码错误！")

    with tab_d:
        d_pwd = st.text_input("主任管理密码", type="password", key="d_pwd")
        if st.button("登录主任端", type="primary"):
            if d_pwd == DIRECTOR_PWD:
                st.session_state.logged = {"name": "主任", "role": "主任"}
                st.rerun()
            else:
                st.error("密码错误！")

    st.caption("💡 忘记密码请联系班主任（学生）或主任（老师）")
    st.stop()

# ================= 已登录 =================
me = st.session_state.logged
st.sidebar.markdown("### 🏫 十八中附小智慧成绩管理平台")
st.sidebar.success(f"{me['role']}：{me['name']}")
if st.sidebar.button("🚪 退出登录"):
    st.session_state.logged = None
    st.rerun()
st.sidebar.divider()
st.sidebar.caption("© 2026 · 智慧校园 · AI 由智谱清言提供")

# ============================================================
# 主任端
# ============================================================
if me["role"] == "主任":
    menu = st.sidebar.radio("功能菜单",
        ["📚 班级管理", "👥 老师与权限", "🗓️ 考试管理", "🔍 成绩对比", "📈 教学质量总览"])

    grade = st.sidebar.selectbox("选择年级", GRADES, key="d_grade")

    # ---------- 班级管理 ----------
    if menu == "📚 班级管理":
        header("班级管理", f"{grade}年级")
        cls_df = load_classes()
        g_cls = cls_df[cls_df["年级"] == grade]

        if len(g_cls) > 0:
            st.markdown("#### 当前班级")
            st.table(g_cls[["班级", "班主任"]].reset_index(drop=True))
        else:
            st.info(f"{grade}年级还没有班级。")

        st.divider()
        st.markdown("#### ➕ 创建班级 / 设置班主任")
        c1, c2, c3 = st.columns(3)
        n_cls = c1.selectbox("班级", CLASSES, key="nc_cls")
        acc = load_accounts()
        teachers = acc[acc["角色"] == "老师"]["姓名"].tolist()
        n_ht = c2.selectbox("班主任（需先在「老师与权限」添加老师）",
                            ["（暂不设置）"] + sorted(set(teachers)), key="nc_ht")
        if c3.button("创建/更新班级", type="primary"):
            m = (cls_df["年级"] == grade) & (cls_df["班级"] == n_cls)
            ht = "" if n_ht.startswith("（") else n_ht
            if m.any():
                cls_df.loc[m, "班主任"] = ht
                st.info(f"已更新 {grade}{n_cls} 的班主任为 {ht or '（无）'}")
            else:
                cls_df = pd.concat([cls_df, pd.DataFrame(
                    [{"年级": grade, "班级": n_cls, "班主任": ht}])], ignore_index=True)
                st.success(f"已创建 {grade}{n_cls}")
            save_classes(cls_df)
            st.rerun()

        st.divider()
        st.markdown("#### 🎓 学生整班升学")
        st.caption("将整班学生、班主任、老师权限一起升入下一学年年级（初三→高一，高三→已毕业）")
        c1, c2 = st.columns(2)
        p_cls = c1.selectbox("要升学的班级",
                             g_cls["班级"].tolist() if len(g_cls) else [], key="p_cls")
        if c2.button("🚀 确认整班升学", type="primary"):
            if p_cls:
                promote_class(grade, p_cls)
                st.success(f"{grade}{p_cls} 已升学！")
                st.rerun()

    # ---------- 老师与权限 ----------
    elif menu == "👥 老师与权限":
        header("老师与权限管理", "总管理员")
        acc = load_accounts()
        perm = load_perms()

        st.markdown("#### 当前老师")
        t_users = acc[acc["角色"] == "老师"]
        if len(t_users) > 0:
            st.table(t_users[["姓名"]].reset_index(drop=True))
        if len(perm) > 0:
            st.markdown("#### 权限分配表")
            st.table(perm.reset_index(drop=True))

        st.divider()
        st.markdown("#### ➕ 添加老师")
        c1, c2 = st.columns(2)
        nt_name = c1.text_input("老师姓名", key="nt_name")
        nt_pwd = c2.text_input("初始密码", key="nt_pwd")
        if st.button("添加老师", type="primary"):
            n = nt_name.replace("\u3000", " ").strip()
            if not n or not nt_pwd:
                st.warning("姓名和密码不能为空！")
            elif (acc["姓名"] == n).any():
                st.warning("已有同名账号！")
            else:
                acc = pd.concat([acc, pd.DataFrame(
                    [{"姓名": n, "密码": nt_pwd, "角色": "老师", "年级": "", "班级": ""}])],
                    ignore_index=True)
                save_accounts(acc)
                st.success(f"已添加老师 {n}")
                st.rerun()

        st.divider()
        st.markdown("#### 🔐 授予老师权限")
        st.caption("「班主任」可管理本班花名册并查看/修改全部科目；「任课老师」只能录入指定科目成绩")
        if len(t_users) == 0:
            st.info("请先添加老师。")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            p_t = c1.selectbox("老师", t_users["姓名"].tolist(), key="p_t")
            p_g = c2.selectbox("年级", GRADES, key="p_g")
            p_c = c3.selectbox("班级", CLASSES, key="p_c")
            p_type = c4.selectbox("权限类型", ["班主任", "任课老师"], key="p_type")
            p_sub = c5.selectbox("科目（任课老师必选）", SUBJECTS, key="p_sub")
            if st.button("授予权限", type="primary"):
                row = {"老师": p_t, "年级": p_g, "班级": p_c,
                       "类型": "班主任" if p_type == "班主任" else "任课",
                       "科目": p_sub if p_type == "任课老师" else ""}
                perm = pd.concat([perm, pd.DataFrame([row])], ignore_index=True)
                perm = perm.drop_duplicates()
                save_perms(perm)
                st.success("权限已授予！")
                st.rerun()

        st.divider()
        st.markdown("#### 🗑️ 删除老师 / 撤销权限")
        c1, c2 = st.columns(2)
        with c1:
            del_t = st.text_input("删除老师（姓名）", key="del_t")
            if st.button("删除老师账号"):
                if (acc["姓名"] == del_t.strip()).any():
                    acc = acc[acc["姓名"] != del_t.strip()]
                    perm = perm[perm["老师"] != del_t.strip()]
                    save_accounts(acc); save_perms(perm)
                    st.success("已删除"); st.rerun()
                else:
                    st.error("未找到该老师！")
        with c2:
            if len(perm) > 0:
                del_p = st.selectbox("撤销哪条权限", perm.index.tolist(),
                    format_func=lambda i: f"{perm.loc[i,'老师']}·{perm.loc[i,'年级']}{perm.loc[i,'班级']}·{perm.loc[i,'类型']}{perm.loc[i,'科目']}",
                    key="del_p")
                if st.button("撤销该权限"):
                    perm = perm.drop(index=del_p)
                    save_perms(perm)
                    st.success("已撤销"); st.rerun()

    # ---------- 考试管理 ----------
    elif menu == "🗓️ 考试管理":
        header("考试管理", f"{grade}年级")
        exams = load_exams()
        g_exams = exams[exams["年级"] == grade]

        st.markdown("#### 已创建的考试")
        if len(g_exams) > 0:
            for _, e in g_exams.iterrows():
                joined = [x for x in e["参加班级"].split("|") if x]
                card(f"<b>📝 {e['考试']}</b>　已参加班级：{('、'.join(joined)) if joined else '暂无'}")
        else:
            st.info(f"{grade}年级还没有考试。")

        st.divider()
        st.markdown("#### 🗑️ 删除考试")
        if len(g_exams) > 0:
            c1, c2 = st.columns([3, 1])
            del_exam = c1.selectbox("选择要删除的考试",
                                    g_exams["考试"].tolist(), key="del_exam")
            with c2:
                st.write("")  # 对齐
                confirm = st.checkbox("我确认删除", key="del_confirm")
            if st.button("删除该考试（连同所有成绩）", type="primary"):
                if not confirm:
                    st.warning("请先勾选「我确认删除」！")
                else:
                    exams = exams[~((exams["年级"] == grade) & (exams["考试"] == del_exam))]
                    save_exams(exams)
                    f = exam_file(grade, del_exam)
                    if os.path.exists(f):
                        os.remove(f)
                    st.success(f"已删除考试【{del_exam}】及其全部成绩")
                    st.rerun()
        else:
            st.caption("暂无考试可删除。")

        st.divider()
        st.markdown("#### ➕ 创建考试（仅主任可创建）")
        n_exam = st.text_input("考试名称（如：2026期中）", key="n_exam")
        if st.button("创建考试", type="primary"):
            n = n_exam.strip()
            if not n:
                st.warning("请填写考试名称！")
            elif ((exams["年级"] == grade) & (exams["考试"] == n)).any():
                st.warning("该考试已存在！")
            else:
                exams = pd.concat([exams, pd.DataFrame(
                    [{"年级": grade, "考试": n, "参加班级": ""}])], ignore_index=True)
                save_exams(exams)
                st.success(f"已创建考试【{n}】，等待各班班主任确认参加")
                st.rerun()
    # ---------- 成绩对比 ----------
    elif menu == "🔍 成绩对比":
        header("两次考试对比分析", f"{grade}年级")
        ex_list = list_exams(grade)
        if len(ex_list) < 2:
            st.info("本年级还不足两次考试，无法对比。")
            st.stop()
        c1, c2 = st.columns(2)
        exam_a = c1.selectbox("基准考试（上次）", ex_list, key="d_cmp_a")
        exam_b = c2.selectbox("对比考试（本次）", [e for e in ex_list if e != exam_a],
                              key="d_cmp_b")

        def diff_txt(d):
            if pd.isna(d):
                return "-"
            arrow = "🔺" if d > 0 else ("🔻" if d < 0 else "➖")
            return f"{d:+.1f} {arrow}"

        da = load_exam(grade, exam_a)
        db = load_exam(grade, exam_b)
        if da.empty or db.empty:
            st.info("所选考试还没有成绩数据。")
            st.stop()
        for d in (da, db):
            d["总分"] = d.apply(total_of, axis=1)

        # ① 各班总分平均分对比
        avg_a = da.groupby("班级")["总分"].mean()
        avg_b = db.groupby("班级")["总分"].mean()
        cls_cmp = pd.DataFrame({"上次均分": avg_a, "本次均分": avg_b})
        cls_cmp["变化"] = cls_cmp["本次均分"] - cls_cmp["上次均分"]
        cls_cmp = cls_cmp.sort_values("变化", ascending=False)
        show = cls_cmp.copy()
        show["变化"] = show["变化"].apply(diff_txt)
        st.markdown(f"#### 🏫 各班总分平均分对比（{exam_a} → {exam_b}）")
        st.table(show.round(1).fillna("-").astype(str))

        # ② 各科各班平均分变化矩阵
        st.markdown("#### 📚 各科平均分变化（行=班级，列=科目）")
        chg = {}
        for s in SUBJECTS:
            chg[s] = (db.groupby("班级")[s].mean() - da.groupby("班级")[s].mean())
        chg_df = pd.DataFrame(chg).dropna(how="all").round(1)
        st.dataframe(chg_df, use_container_width=True)
        st.caption("数值 = 本次平均分 − 上次平均分，正数为进步 🔺，负数为退步 🔻")

        # ③ 年级个人进退步榜
        mm = pd.merge(da[["班级", "姓名", "总分"]], db[["班级", "姓名", "总分"]],
                      on=["班级", "姓名"], suffixes=("_上", "_本"))
        mm["变化"] = mm["总分_本"] - mm["总分_上"]
        mm = mm.dropna(subset=["变化"]).sort_values("变化", ascending=False)
        if len(mm) > 0:
            k1, k2 = st.columns(2)
            with k1:
                st.markdown("#### 🏆 进步榜（前10）")
                top = mm.head(10).copy()
                top["变化"] = top["变化"].apply(diff_txt)
                st.table(top.astype(str))
            with k2:
                st.markdown("#### ⚠️ 退步预警（后10）")
                bot = mm.tail(10).sort_values("变化").copy()
                bot["变化"] = bot["变化"].apply(diff_txt)
                st.table(bot.astype(str))

        # ④ AI 年级对比报告
        stat = (f"上次考试：{exam_a}；本次考试：{exam_b}\n"
                f"各班总分对比：\n{cls_cmp.round(1).to_string()}\n\n"
                f"各科各班平均分变化：\n{chg_df.to_string()}")
        ai_section("生成年级进退步分析报告",
                   f"你是学校教务主任。以下是年级两次考试（{exam_a} → {exam_b}）的对比数据，"
                   f"请写一份300字左右的分析报告：年级整体走势、进步明显的班级与学科、"
                   f"退步需重点关注的班级与学科、下阶段教学工作建议。\n\n{stat}",
                   "AI 将生成年级层面的对比分析报告")

    # ---------- 教学质量总览 ----------
    else:
        header("教学质量总览", f"{grade}年级")
        ex_list = list_exams(grade)
        if not ex_list:
            st.info("本年级还没有考试数据。")
            st.stop()
        exam_v = st.selectbox("选择考试", ex_list)
        df = load_exam(grade, exam_v)
        if df.empty:
            st.info("还没有班级参加该考试。")
            st.stop()
        df["总分"] = df.apply(total_of, axis=1)

        st.markdown("#### 🏆 班级总分排名")
        cls_avg = df.groupby("班级")["总分"].mean().round(1).sort_values(ascending=False)
        rank_df = cls_avg.reset_index()
        rank_df.columns = ["班级", "总分平均分"]
        st.table(rank_df)

        st.markdown("#### 📚 各科班级平均分对比")
        sub_avg = df.groupby("班级")[SUBJECTS].mean().round(1)
        st.bar_chart(sub_avg.T)

        st.markdown("#### 🤖 AI 教学质量报告")
        stat = f"各班总分平均分：\n{rank_df.to_string(index=False)}\n\n各科各班平均分：\n{sub_avg.to_string()}"
        ai_section("生成年级教学质量分析报告",
            f"你是学校教务主任。请根据以下年级考试数据，写一份300字左右的教学质量"
            f"分析报告：总体情况、优势班级与学科、需要关注的班级与学科、改进建议。"
            f"\n\n{stat}", "AI 将生成年级层面的教学质量分析")

# ============================================================
# 老师端
# ============================================================
elif me["role"] == "老师":
    t_name = me["name"]
    perm = load_perms()
    my_perms = perm[perm["老师"] == t_name]

    if len(my_perms) == 0:
        header("老师端", t_name)
        st.warning("你还没有任何班级权限，请联系主任分配（班主任或任课老师）。")
        st.stop()

    is_ht = my_perms[my_perms["类型"] == "班主任"]
    menu = st.sidebar.radio("功能菜单",
                            ["📝 成绩录入", "👥 学生管理", "📈 成绩对比", "🔑 修改密码"])


    # ---------- 修改密码 ----------
    if menu == "🔑 修改密码":
        header("修改密码", t_name)
        old = st.text_input("旧密码", type="password")
        new = st.text_input("新密码", type="password")
        if st.button("确认修改"):
            acc = load_accounts()
            m = (acc["姓名"] == t_name) & (acc["密码"] == old) & (acc["角色"] == "老师")
            if m.any() and new:
                acc.loc[m, "密码"] = new
                save_accounts(acc)
                st.success("修改成功！")
            else:
                st.error("旧密码错误（或新密码为空）！")

    # ---------- 学生管理（仅班主任）----------
    elif menu == "👥 学生管理":
        if len(is_ht) == 0:
            header("学生管理", t_name)
            st.warning("只有班主任才能管理学生，请联系主任授权。")
            st.stop()
        opts = [f"{r['年级']}{r['班级']}" for _, r in is_ht.iterrows()]
        pick = st.sidebar.selectbox("选择你管的班级", opts)
        # 解析
        ht_row = is_ht.iloc[opts.index(pick)]
        grade, cls = ht_row["年级"], ht_row["班级"]
        header("学生管理（花名册）", f"{grade}{cls}")

        roster = class_roster(grade, cls)
        if len(roster) > 0:
            st.markdown(f"#### 当前花名册（{len(roster)} 人）")
            st.table(roster[["姓名", "年级", "班级"]].reset_index(drop=True))
        else:
            st.info("本班还没有学生，请在下方添加。")

        st.divider()
        st.markdown("#### ➕ 添加学生（设置初始密码）")
        c1, c2 = st.columns(2)
        n_name = c1.text_input("学生姓名", key="h_name")
        n_pwd = c2.text_input("初始密码", value="123456", key="h_pwd")
        if st.button("添加学生", type="primary"):
            n = n_name.replace("\u3000", " ").strip()
            acc = load_accounts()
            if not n or not n_pwd:
                st.warning("姓名和密码不能为空！")
            elif ((acc["角色"] == "学生") & (acc["年级"] == grade)
                  & (acc["班级"] == cls) & (acc["姓名"] == n)).any():
                st.warning("本班已有该学生！")
            else:
                acc = pd.concat([acc, pd.DataFrame(
                    [{"姓名": n, "密码": n_pwd, "角色": "学生",
                      "年级": grade, "班级": cls}])], ignore_index=True)
                save_accounts(acc)
                st.success(f"已添加 {n}，初始密码：{n_pwd}")
                st.rerun()

        st.divider()
        st.markdown("#### 📥 批量导入花名册")
        st.caption("支持：① 上传 CSV 文件（含「姓名」列，可有「密码」列）；② 从 Excel 直接复制粘贴名单")
        st.download_button("📄 下载导入模板（CSV）",
                           "姓名,密码\n张三,123456\n李四,123456\n".encode("utf-8-sig"),
                           file_name="花名册导入模板.csv", key="imp_tpl")
        up = st.file_uploader("方式一：上传 CSV 文件", type=["csv"], key="imp_up")
        pasted = st.text_area("方式二：粘贴名单（每行一个姓名；单独设密码用：姓名,密码）",
                              placeholder="张三\n李四\n王五,888888", key="imp_area")
        default_pwd = st.text_input("未单独提供密码的学生，使用此默认密码",
                                    value="123456", key="imp_pwd")
        if st.button("📥 开始导入", type="primary"):
            names = []
            if up is not None:
                try:
                    imp = pd.read_csv(up, dtype=str, encoding="utf-8-sig")
                except UnicodeDecodeError:
                    up.seek(0)
                    imp = pd.read_csv(up, dtype=str, encoding="gbk")
                imp.columns = [str(c).strip() for c in imp.columns]
                if "姓名" not in imp.columns and len(imp.columns) == 1:
                    imp.columns = ["姓名"]
                if "姓名" in imp.columns:
                    pw_list = (imp["密码"].astype(str) if "密码" in imp.columns
                               else pd.Series([""] * len(imp)))
                    for nm, pw in zip(imp["姓名"].astype(str), pw_list):
                        names.append((nm.strip(), "" if pw in ("nan", "None") else pw.strip()))
                else:
                    st.error("CSV 中未找到「姓名」列，请参考模板。")
            for line in (pasted or "").splitlines():
                line = line.strip().replace("\u3000", " ")
                if not line:
                    continue
                if "\t" in line:
                    parts = line.split("\t")
                elif "," in line:
                    parts = line.split(",", 1)
                elif " " in line:
                    parts = line.split(None, 1)
                else:
                    parts = [line]
                names.append((parts[0].strip(),
                              parts[1].strip() if len(parts) > 1 else ""))
            acc = load_accounts()
            added, skipped, seen = [], [], set()
            for nm, pw in names:
                if not nm or nm.lower() == "nan" or nm == "姓名":
                    continue
                if nm in seen:
                    skipped.append(f"{nm}（名单内重复）")
                    continue
                seen.add(nm)
                if ((acc["角色"] == "学生") & (acc["年级"] == grade)
                        & (acc["班级"] == cls) & (acc["姓名"] == nm)).any():
                    skipped.append(f"{nm}（本班已有）")
                    continue
                acc = pd.concat([acc, pd.DataFrame(
                    [{"姓名": nm, "密码": pw or default_pwd, "角色": "学生",
                      "年级": grade, "班级": cls}])], ignore_index=True)
                added.append(nm)
            if added:
                save_accounts(acc)
            st.session_state["imp_result"] = (added, skipped)
            st.rerun()
        if "imp_result" in st.session_state:
            added, skipped = st.session_state.pop("imp_result")
            if added:
                st.success(f"✅ 成功导入 {len(added)} 人：{'、'.join(added)}")
                st.caption("提示：新学生如需计入当前考试，请到「成绩录入」再点一次「✅ 本班参加本次考试」补入。")
            if skipped:
                st.warning(f"⚠️ 跳过 {len(skipped)} 人：{'、'.join(skipped)}")
            if not added and not skipped:
                st.info("未识别到有效姓名，请检查格式。")

        st.markdown("#### 🔑 重置学生密码 / 🗑️ 移除学生")
        c1, c2 = st.columns(2)
        with c1:
            r_name = st.text_input("学生姓名", key="h_rname")
            r_pwd = st.text_input("新密码", key="h_rpwd")
            if st.button("重置密码"):
                acc = load_accounts()
                m = ((acc["角色"] == "学生") & (acc["年级"] == grade)
                     & (acc["班级"] == cls) & (acc["姓名"] == r_name.strip()))
                if m.any() and r_pwd:
                    acc.loc[m, "密码"] = r_pwd
                    save_accounts(acc)
                    st.success("已重置")
                else:
                    st.error("未找到该学生（或新密码为空）！")
        with c2:
            del_name = st.text_input("移除学生（姓名）", key="h_del")
            if st.button("移除该学生"):
                acc = load_accounts()
                m = ((acc["角色"] == "学生") & (acc["年级"] == grade)
                     & (acc["班级"] == cls) & (acc["姓名"] == del_name.strip()))
                if m.any():
                    acc = acc[~m]
                    save_accounts(acc)
                    st.success("已移除（成绩表中记录保留）")
                    st.rerun()
                else:
                    st.error("未找到该学生！")

    # ---------- 成绩对比 ----------
    elif menu == "📈 成绩对比":
        choices = []
        for _, p in my_perms.iterrows():
            if p["类型"] == "班主任":
                choices.append((p["年级"], p["班级"], "全部科目", p))
            else:
                choices.append((p["年级"], p["班级"], p["科目"], p))
        opts = [f"{g}{c} · {s}" for g, c, s, _ in choices]
        pick = st.sidebar.selectbox("选择对比任务", opts, key="cmp_pick")
        grade, cls, subject, p_row = choices[opts.index(pick)]

        header("成绩对比", f"{grade}{cls} · {subject}")
        ex_list = list_exams(grade)
        if len(ex_list) < 2:
            st.info("本年级还不足两次考试，无法对比。")
            st.stop()
        c1, c2 = st.columns(2)
        exam_a = c1.selectbox("基准考试（上次）", ex_list, key=f"cmp_a_{grade}_{cls}")
        exam_b = c2.selectbox("对比考试（本次）", [e for e in ex_list if e != exam_a],
                              key=f"cmp_b_{grade}_{cls}")

        def diff_txt(d):
            if pd.isna(d):
                return "-"
            arrow = "🔺" if d > 0 else ("🔻" if d < 0 else "➖")
            return f"{d:+.0f} {arrow}"

        df_a = load_exam(grade, exam_a)
        df_b = load_exam(grade, exam_b)
        df_a["总分"] = df_a.apply(total_of, axis=1)
        df_b["总分"] = df_b.apply(total_of, axis=1)
        a_cls = df_a[df_a["班级"] == cls].set_index("姓名")
        b_cls = df_b[df_b["班级"] == cls].set_index("姓名")

        common = [n for n in b_cls.index if n in a_cls.index]
        missing = [n for n in b_cls.index if n not in a_cls.index]
        if missing:
            st.warning(f"以下学生在【{exam_a}】中无成绩，未参与对比：{'、'.join(missing)}")
        if not common:
            st.info("两次考试没有共同学生，无法对比。")
            st.stop()

        use_cols = (SUBJECTS if subject == "全部科目" else [subject]) \
                   + (["总分"] if subject == "全部科目" else [])
        rows = []
        for n in common:
            row = {"姓名": n}
            for s in use_cols:
                va = pd.to_numeric(a_cls.loc[n, s], errors="coerce")
                vb = pd.to_numeric(b_cls.loc[n, s], errors="coerce")
                row[f"{s}_上"] = va
                row[f"{s}_本"] = vb
                row[f"{s}_变"] = vb - va if (pd.notna(va) and pd.notna(vb)) else np.nan
            rows.append(row)
        cmp_df = pd.DataFrame(rows).set_index("姓名")

        main_s = "总分" if "总分" in use_cols else subject
        rank = cmp_df.sort_values(f"{main_s}_变", ascending=False)
        show = pd.DataFrame({
            f"上次{main_s}": rank[f"{main_s}_上"],
            f"本次{main_s}": rank[f"{main_s}_本"],
            "变化": rank[f"{main_s}_变"].apply(diff_txt),
        }).fillna("-")
        st.markdown(f"#### 📊 每人「{main_s}」变化（进步→退步排序）")
        st.table(show.astype(str))

        chg = cmp_df[f"{main_s}_变"]
        avg_diff, up_n, down_n = chg.mean(), (chg > 0).sum(), (chg < 0).sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("📈 平均分变化", diff_txt(avg_diff))
        m2.metric("🔺 进步人数", f"{up_n} 人")
        m3.metric("🔻 退步人数", f"{down_n} 人")

        if subject == "全部科目":
            st.divider()
            sub_v = st.selectbox("查看单科变化明细", SUBJECTS, key=f"cmp_s_{grade}_{cls}")
            det = cmp_df.sort_values(f"{sub_v}_变", ascending=False)
            show2 = pd.DataFrame({
                f"上次{sub_v}": det[f"{sub_v}_上"],
                f"本次{sub_v}": det[f"{sub_v}_本"],
                "变化": det[f"{sub_v}_变"].apply(diff_txt),
            }).fillna("-")
            st.markdown(f"#### 📚 「{sub_v}」变化明细")
            st.table(show2.astype(str))

        if p_row["类型"] == "班主任":
            stat = (f"班级：{grade}{cls}；上次考试：{exam_a}；本次考试：{exam_b}\n"
                    f"{main_s}平均分变化：{diff_txt(avg_diff)}；进步 {up_n} 人，退步 {down_n} 人\n"
                    f"每人变化明细：\n{show.to_string()}")
            ai_section("生成两次考试对比分析",
                       f"你是一位班主任。以下是班级两次考试（{exam_a} → {exam_b}）的对比数据，"
                       f"请写一段200字左右的分析：整体进退步情况、值得表扬的进步方面、"
                       f"需要关注的群体（不点名批评单个学生），并给家长和科任老师各1条建议。"
                       f"\n\n{stat}",
                       "AI 将对比两次考试，生成班级进退步分析")


    # ---------- 成绩录入 ----------
    else:
        # 可录入范围 = 班主任的全部科目 + 任课授权
        choices = []
        for _, p in my_perms.iterrows():
            if p["类型"] == "班主任":
                choices.append((p["年级"], p["班级"], "全部科目", p))
            else:
                choices.append((p["年级"], p["班级"], p["科目"], p))
        opts = [f"{g}{c} · {s}" for g, c, s, _ in choices]
        pick = st.sidebar.selectbox("选择录入任务", opts)
        grade, cls, subject, p_row = choices[opts.index(pick)]

        header("成绩录入", f"{grade}{cls} · {subject}")
        exams = load_exams()
        g_exams = exams[(exams["年级"] == grade)]["考试"].tolist()
        if not g_exams:
            st.info("本年级还没有考试，请等待主任创建。")
            st.stop()
        exam = st.selectbox("选择考试（主任已创建）", g_exams)

        # 班主任：选择本班参加考试
        if p_row["类型"] == "班主任":
            exams_df = load_exams()
            m = (exams_df["年级"] == grade) & (exams_df["考试"] == exam)
            joined = set(filter(None, exams_df.loc[m, "参加班级"].iloc[0].split("|")))
            if cls in joined:
                st.success(f"✅ 本班已参加【{exam}】")
            else:
                st.info(f"本班尚未参加【{exam}】。参加后花名册将自动计入该考试。")
                if st.button("✅ 本班参加本次考试", type="primary"):
                    join_exam(grade, exam, cls)
                    st.success("已参加！花名册已计入。")
                    st.rerun()
            st.divider()

        df = load_exam(grade, exam)
        class_df = df[df["班级"] == cls]

        if class_df.empty:
            st.info("本班还没有该考试的成绩记录（班主任需先确认参加考试）。")
            st.stop()

        subj_list = SUBJECTS if subject == "全部科目" else [subject]
        subject = st.selectbox("录入科目", subj_list,
                               index=0, key=f"sub_{grade}_{cls}_{exam}") \
                   if subject == "全部科目" else subject

        st.markdown(f"#### {grade}{cls}「{subject}」成绩（满分 {MAX_SCORE[subject]}）")
        new_scores = {}
        for _, r in class_df.iterrows():
            new_scores[r["姓名"]] = st.number_input(
                r["姓名"], min_value=0, max_value=MAX_SCORE[subject], step=1,
                value=int(r[subject]) if pd.notna(r[subject]) else 0,
                key=f"{grade}_{exam}_{cls}_{subject}_{r['姓名']}")

        if st.button("💾 保存成绩", type="primary") and new_scores:
            for name, score in new_scores.items():
                df.loc[(df["班级"] == cls) & (df["姓名"] == name), subject] = score
            df.to_csv(exam_file(grade, exam))
            st.success(f"【{exam}】{grade}{cls} {subject} 成绩已保存！")

        # 班主任：本班全科总览
        if p_row["类型"] == "班主任":
            st.divider()
            st.markdown("#### 📋 本班全科成绩总览")
            d = class_df.copy()
            d["总分"] = d.apply(total_of, axis=1)
            show_cols = ["姓名"] + SUBJECTS + ["总分"]
            st.table(d[show_cols].astype(str))

            filled = class_df[class_df[subject].notna()]
            if len(filled) > 0:
                stat = (f"班级：{grade}{cls}；科目：{subject}；满分：{MAX_SCORE[subject]}\n"
                        f"参考人数：{len(filled)}；平均分：{filled[subject].mean():.1f}；"
                        f"最高分：{filled[subject].max():.0f}；最低分：{filled[subject].min():.0f}")
                ai_section("生成班情分析（可发家长群）",
                    f"你是一位班主任。请根据以下班级「{subject}」成绩统计，写一段200字左右的"
                    f"班情分析，语气正式得体，适合发到家长群：先总体评价，再指出亮点与不足，"
                    f"最后给家长2-3条配合建议。\n\n{stat}",
                    "点击生成可直接发家长群的班情分析文字")

            st.download_button("📥 下载本班成绩表（CSV）",
                class_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{grade}_{exam}_{cls}.csv")

# ============================================================
# 学生端
# ============================================================
else:
    grade, cls, name = me["grade"], me["cls"], me["name"]
    header("学生端 · 我的成绩", f"{grade}{cls} · {name}")

    if grade == "已毕业":
        st.info("你已毕业，账号归档。")
        st.stop()

    with st.expander("🔑 修改我的密码"):
        old = st.text_input("旧密码", type="password", key="s_cp_old")
        new = st.text_input("新密码", type="password", key="s_cp_new")
        if st.button("确认修改"):
            acc = load_accounts()
            m = ((acc["姓名"] == name) & (acc["密码"] == old)
                 & (acc["角色"] == "学生") & (acc["年级"] == grade) & (acc["班级"] == cls))
            if m.any() and new:
                acc.loc[m, "密码"] = new
                save_accounts(acc)
                st.success("密码修改成功！")
            else:
                st.error("旧密码错误（或新密码为空）！")

    exams = list_exams(grade)
    if not exams:
        st.info("本年级还没有考试数据。")
        st.stop()
    exam = st.selectbox("选择考试", exams)
    df = load_exam(grade, exam)
    d = df.copy()
    d["总分"] = d.apply(total_of, axis=1)
    for s in SUBJECTS + ["总分"]:
        d[s + "班排"] = d[d["班级"] == cls][s].rank(ascending=False, method="min")
        d[s + "年排"] = d[s].rank(ascending=False, method="min")
    rows_found = d[(d["班级"] == cls) & (d["姓名"] == name)]
    if rows_found.empty:
        st.warning("未找到你的成绩记录（本班可能未参加该考试），请联系班主任。")
        st.stop()
    r = rows_found.iloc[0]

    m1, m2 = st.columns(2)
    m1.metric("📊 总分", f"{r['总分']:.0f} 分" if pd.notna(r['总分']) else "科目未录完")
    m2.metric("🏅 年级排名", f"第{r['总分年排']:.0f} 名" if pd.notna(r['总分']) else "-")

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
                st.table(pd.DataFrame(rows2).astype(str))

    st.caption("💡 打印/保存 PDF：按 Ctrl + P")
