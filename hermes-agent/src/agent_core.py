"""헤르메스 에이전트의 두뇌: Claude API 호출 + 도구 실행 루프 + 메모리/스킬 연결."""

import subprocess

from anthropic import Anthropic

from . import config, memory, skills

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

TOOLS = [
    {
        "name": "remember_preference",
        "description": "사용자의 업무 스타일, 선호 서식, 반복되는 지시사항 등을 영구 기억할 때 사용한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "기억할 항목의 짧은 이름 (예: report_format)"},
                "value": {"type": "string", "description": "기억할 내용"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "save_skill",
        "description": (
            "복잡한 작업을 성공적으로 완수했을 때, 그 과정을 마크다운 스킬 문서로 저장해 "
            "다음에 비슷한 요청이 오면 재사용할 수 있도록 한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "스킬의 제목"},
                "summary": {"type": "string", "description": "스킬이 무엇을 하는지 한두 문장 요약"},
                "steps_markdown": {"type": "string", "description": "재현 가능한 단계별 절차 (마크다운)"},
            },
            "required": ["title", "summary", "steps_markdown"],
        },
    },
    {
        "name": "read_skill",
        "description": "저장된 스킬 문서의 전체 내용을 읽어온다.",
        "input_schema": {
            "type": "object",
            "properties": {"file": {"type": "string", "description": "skills 디렉터리 내 파일명"}},
            "required": ["file"],
        },
    },
    {
        "name": "run_shell",
        "description": (
            "서버(자신이 실행 중인 VPS)에서 셸 명령을 실행한다. 파일 확인, 백업, 상태 점검 등 "
            "사용자가 명시적으로 요청한 작업에만 사용하고, 파괴적인 명령은 실행 전 반드시 사용자에게 확인한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "실행할 셸 명령"}},
            "required": ["command"],
        },
    },
]


def _system_prompt(user_id: int) -> str:
    prefs = memory.get_preferences(user_id)
    prefs_text = (
        "\n".join(f"- {k}: {v}" for k, v in prefs.items()) if prefs else "(아직 저장된 선호 정보 없음)"
    )

    skill_list = skills.list_skills()
    skills_text = (
        "\n".join(f"- {s['file']}: {s['title']} — {s['summary']}" for s in skill_list)
        if skill_list
        else "(아직 저장된 스킬 없음)"
    )

    return (
        "너는 '헤르메스 에이전트'라는 이름의 24시간 무인 개인 비서다. "
        "텔레그램을 통해 사용자와 대화하며, 사용자의 업무를 돕는다.\n\n"
        f"## 사용자의 저장된 선호/스타일\n{prefs_text}\n\n"
        f"## 사용 가능한 저장된 스킬 목록\n{skills_text}\n"
        "비슷한 작업이 요청되면 read_skill로 해당 스킬을 먼저 확인하고 따라간다.\n\n"
        "사용자가 선호하는 서식이나 반복적인 지시를 발견하면 remember_preference로 저장하라. "
        "여러 단계를 거쳐 복잡한 작업을 성공적으로 끝냈다면 save_skill로 문서화하라."
    )


def _execute_tool(user_id: int, name: str, tool_input: dict) -> str:
    if name == "remember_preference":
        memory.set_preference(user_id, tool_input["key"], tool_input["value"])
        return f"저장 완료: {tool_input['key']} = {tool_input['value']}"

    if name == "save_skill":
        path = skills.save_skill(
            tool_input["title"], tool_input["summary"], tool_input["steps_markdown"]
        )
        return f"스킬 저장 완료: {path}"

    if name == "read_skill":
        try:
            return skills.read_skill(tool_input["file"])
        except FileNotFoundError:
            return f"스킬 파일을 찾을 수 없음: {tool_input['file']}"

    if name == "run_shell":
        result = subprocess.run(
            tool_input["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return output[-4000:] if output else "(출력 없음)"

    return f"알 수 없는 도구: {name}"


def run_turn(user_id: int, user_text: str, history_limit: int = 20) -> str:
    """사용자 메시지 한 건을 처리하고 최종 응답 텍스트를 반환한다. 도구 호출은 루프 안에서 자동 처리."""
    memory.add_message(user_id, "user", user_text)
    messages = memory.recent_messages(user_id, limit=history_limit)

    final_text = ""
    for _ in range(8):  # 도구 호출 무한루프 방지
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2048,
            system=_system_prompt(user_id),
            tools=TOOLS,
            messages=messages,
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        final_text = "\n".join(text_blocks).strip()

        if response.stop_reason != "tool_use":
            break

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            result = _execute_tool(user_id, tu.name, tu.input)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tu.id, "content": result}
            )
        messages.append({"role": "user", "content": tool_results})

    memory.add_message(user_id, "assistant", final_text)
    return final_text
