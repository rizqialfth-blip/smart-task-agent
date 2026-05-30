import streamlit as st
import google.generativeai as genai
import json
import time
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

# ── Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Task Automation Agent",
    page_icon="🤖",
    layout="wide"
)

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# ── Tools ────────────────────────────────────────────────
def tool_classify_task(task: str) -> dict:
    categories = ["research", "analysis", "summarization", "content", "automation"]
    for cat in categories:
        if cat in task.lower():
            return {"tool": "classify_task", "category": cat, "status": "success"}
    return {"tool": "classify_task", "category": "general", "status": "success"}

def tool_web_search(query: str) -> dict:
    return {
        "tool": "web_search",
        "query": query,
        "result": f"[Simulated] Found relevant information about: {query}",
        "status": "success"
    }

def tool_summarize(text: str) -> dict:
    return {
        "tool": "summarize",
        "summary": f"Key insights extracted from: {text[:80]}...",
        "status": "success"
    }

def tool_save_report(data: dict) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "tool": "save_report",
        "filename": f"report_{timestamp}.json",
        "status": "success"
    }

TOOLS = {
    "classify_task": tool_classify_task,
    "web_search": tool_web_search,
    "summarize": tool_summarize,
    "save_report": tool_save_report,
}

# ── AI Planner ───────────────────────────────────────────
def plan_task(task: str) -> list:
    prompt = f"""
You are an AI task planner. Given this task: "{task}"

Generate exactly 4 execution steps as a JSON array. Each step has:
- "step": step number (1-4)
- "tool": one of [classify_task, web_search, summarize, save_report]
- "description": short description of what this step does
- "input": the input string for this tool

Return ONLY valid JSON array, no markdown, no explanation.

Example:
[
  {{"step": 1, "tool": "classify_task", "description": "Classify the nature of the task", "input": "{task}"}},
  {{"step": 2, "tool": "web_search", "description": "Search for relevant information", "input": "latest trends in {task}"}},
  {{"step": 3, "tool": "summarize", "description": "Summarize findings into key insights", "input": "search results about {task}"}},
  {{"step": 4, "tool": "save_report", "description": "Save structured report to output", "input": "final report"}}
]
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        steps = json.loads(text)
        return steps
    except Exception:
        return [
            {"step": 1, "tool": "classify_task", "description": "Classify the nature of the task", "input": task},
            {"step": 2, "tool": "web_search", "description": "Search for relevant information", "input": task},
            {"step": 3, "tool": "summarize", "description": "Summarize findings into key insights", "input": task},
            {"step": 4, "tool": "save_report", "description": "Save structured report", "input": "final report"},
        ]

def generate_summary(task: str, results: list) -> str:
    prompt = f"""
Task: {task}

Execution results: {json.dumps(results, indent=2)}

Write a professional 3-4 sentence summary of what was accomplished.
Be specific and actionable. Use Indonesian language.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except ResourceExhausted:
        return "⚠️ Limit API tercapai. Tunggu 1 menit lalu coba lagi."
    except Exception as e:
        return f"Task selesai dieksekusi dengan {len(results)} langkah berhasil."

# ── UI ───────────────────────────────────────────────────
st.title("🤖 Smart Task Automation Agent")
st.caption("Ketik task dalam bahasa natural → AI plan otomatis → eksekusi step by step")

st.divider()

# Example tasks
st.markdown("**💡 Contoh task yang bisa dicoba:**")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔍 Research AI trends"):
        st.session_state["example_task"] = "Research the latest trends in AI data annotation"
with col2:
    if st.button("📊 Analyze market data"):
        st.session_state["example_task"] = "Analyze market data for SaaS products in 2024"
with col3:
    if st.button("📝 Summarize findings"):
        st.session_state["example_task"] = "Summarize findings about machine learning in healthcare"

default_task = st.session_state.get("example_task", "")
task_input = st.text_area(
    "Masukkan task kamu:",
    value=default_task,
    height=80,
    placeholder="Contoh: Research the latest trends in AI data annotation and summarize key findings"
)

run_button = st.button("🚀 Jalankan Agent", type="primary", use_container_width=True)

if run_button and task_input.strip():
    st.divider()

    # Session header
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.markdown(f"""
    <div style='background: #0f1117; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin-bottom: 16px; font-family: monospace;'>
        <span style='color: #8b949e;'>Session:</span> <span style='color: #58a6ff;'>{session_id}</span><br>
        <span style='color: #8b949e;'>Task:</span> <span style='color: #e6edf3;'>{task_input}</span>
    </div>
    """, unsafe_allow_html=True)

    # Planning phase
    with st.status("🧠 AI sedang merencanakan langkah eksekusi...", expanded=True) as status:
        try:
            steps = plan_task(task_input)
            status.update(label=f"✅ Plan selesai — {len(steps)} langkah dibuat", state="complete")
        except ResourceExhausted:
            st.error("⚠️ Limit API tercapai. Tunggu 1 menit lalu coba lagi.")
            st.stop()

    # Execution phase
    st.subheader("⚡ Eksekusi")
    results = []

    for step in steps:
        tool_name = step.get("tool", "")
        description = step.get("description", "")
        input_val = step.get("input", "")
        step_num = step.get("step", "?")

        col_status, col_info = st.columns([1, 5])
        with col_status:
            with st.spinner(f"Step {step_num}..."):
                time.sleep(0.6)
                if tool_name in TOOLS:
                    result = TOOLS[tool_name](input_val)
                else:
                    result = {"tool": tool_name, "status": "skipped"}
                results.append(result)

        with col_info:
            st.success(f"**Step {step_num}** — {description}")
            with st.expander(f"🔧 `{tool_name}` output"):
                st.json(result)

    # Final summary
    st.divider()
    st.subheader("📋 Final Summary")

    with st.spinner("Generating final answer..."):
        summary = generate_summary(task_input, results)

    st.info(summary)

    # JSON Report
    report = {
        "session_id": session_id,
        "task": task_input,
        "steps_executed": len(results),
        "results": results,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }

    with st.expander("📄 Lihat Full JSON Report"):
        st.json(report)

    st.download_button(
        label="⬇️ Download JSON Report",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=f"report_{session_id}.json",
        mime="application/json"
    )

elif run_button and not task_input.strip():
    st.warning("⚠️ Masukkan task dulu sebelum menjalankan agent!")

else:
    st.markdown("""
    <div style='text-align: center; padding: 40px; color: #8b949e;'>
        <h3>🤖</h3>
        <p>Masukkan task di atas dan klik <strong>Jalankan Agent</strong></p>
        <p style='font-size: 12px;'>Agent akan otomatis membuat rencana, mengeksekusi setiap langkah, dan menghasilkan laporan terstruktur</p>
    </div>
    """, unsafe_allow_html=True)
