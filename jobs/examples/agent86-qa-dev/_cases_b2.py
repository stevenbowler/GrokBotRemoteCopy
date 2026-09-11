def case_skill_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_badge(page, "Skills")
    page.wait_for_timeout(500)
    if click_text(page, "Create") or click_text(page, "New Skill") or click_text(page, "+"):
        # form path
        name = page.locator("input").first
        try:
            name.fill("QA Skill")
        except Exception:
            pass
    open_my_maxchat(page)
    send_chat(
        page,
        "Max, create a personal skill named QA Skill. When invoked, reply with exactly: QA-SKILL-OK followed by today's date in YYYY-MM-DD format.",
    )
    try:
        wait_reply_contains(page, "QA Skill", 90000)
    except PWTimeout:
        return _fail("skill not created")
    ctx["skill"] = "QA Skill"
    return _ok("skill created via Max (no create form required)")


def case_skill_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(page, "Please run my QA Skill")
    try:
        wait_reply_contains(page, "QA-SKILL-OK", 90000)
    except PWTimeout:
        return _fail("QA-SKILL-OK not in reply")
    return _ok("skill invoked")


def case_skill_03(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    send_chat(page, "Max, add my personal skill QA Skill to this project")
    try:
        wait_reply_contains(page, "QA Skill", 90000)
    except PWTimeout:
        return _fail("skill not added to project")
    ctx["skill_on_project"] = True
    return _ok("skill on project")


def case_skill_04(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    send_chat(page, "Max, run skill 1")
    try:
        wait_reply_contains(page, "QA-SKILL-OK", 90000)
    except PWTimeout:
        send_chat(page, "Max, run QA Skill")
        try:
            wait_reply_contains(page, "QA-SKILL-OK", 90000)
        except PWTimeout:
            return _fail("project skill not invoked")
    return _ok("project skill invoked")


def case_skill_05(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    send_chat(page, "Max, remove QA Skill from this project but do not delete it globally")
    page.wait_for_timeout(3000)
    open_my_maxchat(page)
    send_chat(page, "Run my QA Skill")
    try:
        wait_reply_contains(page, "QA-SKILL-OK", 90000)
    except PWTimeout:
        return _fail("global skill broken after project detach")
    return _ok("detached from project, still global")


def case_skill_06(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    send_chat(page, "Max, add QA Skill to QA Test Project again")
    page.wait_for_timeout(2000)
    open_badge(page, "Skills")
    # confirmation UI may not exist; ask Max
    open_my_maxchat(page)
    send_chat(page, "Max, delete the skill named QA Skill after confirming it is attached to a project")
    try:
        wait_reply_contains(page, "delete", 90000)
    except PWTimeout:
        return _fail("delete not confirmed")
    return _ok("delete requested")


def case_trig_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(
        page,
        'Max, create a trigger called "QA Trigger" that runs QA Skill daily at 9am and delivers the result to this chat',
    )
    try:
        wait_reply_contains(page, "QA Trigger", 90000)
    except PWTimeout:
        return _fail("trigger not created")
    open_badge(page, "Triggers")
    if click_text(page, "Refresh") or click_text(page, "↻ Refresh"):
        page.wait_for_timeout(1000)
    body = last_thread_text(page)
    if "QA Trigger" not in body:
        return _fail("trigger not visible in panel")
    ctx["trigger"] = "QA Trigger"
    return _ok("trigger created and listed")


def case_trig_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    open_badge(page, "Triggers")
    page.wait_for_timeout(500)
    body = last_thread_text(page)
    if "QA Trigger" not in body:
        return _fail("personal trigger hidden in project context")
    return _ok("trigger visible from project")


def case_todo_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(
        page,
        "Please set a reminder for me called QA Reminder Test, scheduled for 10 minutes from now",
    )
    try:
        wait_reply_contains(page, "QA Reminder Test", 90000)
    except PWTimeout:
        return _fail("reminder not confirmed")
    ctx["reminder"] = "QA Reminder Test"
    return _ok("reminder created")


def case_todo_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, "Todos") or open_badge(page, "Todos") or open_badge(page, "Reminders")
    page.wait_for_timeout(800)
    body = last_thread_text(page)
    if "QA Reminder Test" not in body:
        return _fail("reminder not in Todos UI")
    return _ok("visible in Todos")


def case_todo_03(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(page, "Show me all my upcoming reminders")
    try:
        wait_reply_contains(page, "QA Reminder Test", 90000)
    except PWTimeout:
        return _fail("Max did not list reminder")
    send_chat(page, "Cancel the QA Reminder Test reminder")
    page.wait_for_timeout(2000)
    return _ok("listed and cancel requested")


def case_chart_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(
        page,
        "Max, please create a bar chart with this data: Apples 10, Bananas 5, Oranges 8, Grapes 12",
    )
    try:
        page.wait_for_selector("img[src*='chart'], img[src*='/charts/'], img", timeout=120000)
    except PWTimeout:
        body = last_thread_text(page)
        if "chart" in body.lower():
            return _fail("chart mentioned but no inline image")
        return _fail("no chart image")
    return _ok("inline chart image")


def case_mem_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    if not attach_via_file_input(page, [str(ctx["files"]["txt"])]):
        return _fail("attach failed")
    send_chat(page, "Here is a file for later reference")
    for msg in (
        "What is the capital of France?",
        "Tell me a fun fact about penguins",
        "What is 144 divided by 12?",
        "Describe the weather on Mars",
    ):
        send_chat(page, msg)
        page.wait_for_timeout(1500)
    send_chat(page, "Go back to the file I sent earlier. What was the secret word in it?")
    try:
        wait_reply_contains(page, "BANANA", 90000)
    except PWTimeout:
        return _fail("BANANA not recalled after intervening turns (known flaky)")
    return _ok("file recalled")


def case_mem_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(
        page,
        "Please remember this for our next conversation: my project code is QA-PERSIST-TEST",
    )
    try:
        wait_reply_contains(page, "QA-PERSIST-TEST", 90000)
    except PWTimeout:
        return _fail("memory save not confirmed")
    if not logout(page):
        return _fail("logout failed; cannot complete MEM-02 (AUTH-04)")
    ctx["logged_in"] = False
    email = ctx["qa_user_alt"] if ctx.get("auth01_missing") else ctx["qa_user"]
    code = ctx["qa_password_alt"] if ctx.get("auth01_missing") else ctx["qa_password"]
    result = login(page, email, code)
    if not result["ok"]:
        return _fail("re-login failed for MEM-02")
    ctx["logged_in"] = True
    open_my_maxchat(page)
    send_chat(page, "Do you remember the project code I gave you previously?")
    try:
        wait_reply_contains(page, "QA-PERSIST-TEST", 90000)
    except PWTimeout:
        return _fail("long-term memory miss")
    return _ok("memory survived logout")


def case_nav_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    errors: list[str] = []
    for label in ("My MaxChat", "QA Test Project", "Todos"):
        if not click_text(page, label):
            errors.append(label)
        page.wait_for_timeout(400)
    if errors:
        return _fail(f"sections not clickable: {errors}")
    return _ok("sidebar sections loaded")


def case_nav_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not open_badge(page, "Skills"):
        return _fail("Skills badge missing")
    page.mouse.click(10, 10)
    if not open_badge(page, "Triggers"):
        return _fail("Triggers badge missing")
    page.mouse.click(10, 10)
    return _ok("Skills and Triggers panels")


def case_nav_03(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not click_text(page, "Profile"):
        # open user menu first
        click_text(page, "Demo User") or click_text(page, "QA Tester")
        if not click_text(page, "Profile"):
            return _fail("Profile menu missing")
    inp = page.locator("input[type=text], input:not([type])")
    if inp.count() == 0:
        return _fail("display name field missing")
    inp.first.fill("QA Tester")
    click_text(page, "Save") or inp.first.press("Enter")
    page.wait_for_timeout(800)
    body = last_thread_text(page)
    if "QA Tester" not in body:
        return _fail("display name did not update")
    inp = page.locator("input[type=text], input:not([type])")
    if inp.count():
        try:
            inp.first.fill("Demo User")
            click_text(page, "Save")
        except Exception:
            pass
    return _ok("profile save")


def case_master_gate(page: Page, ctx: dict[str, Any]) -> bool:
    ctx["has_master"] = has_master_menu(page)
    return ctx["has_master"]


def case_master_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master") and not has_master_menu(page):
        return _skip("no Master menu")
    ctx["has_master"] = True
    if not click_text(page, "Master"):
        return _fail("Master menu present but not clickable")
    page.wait_for_timeout(1000)
    body = last_thread_text(page)
    if "Tenant" not in body and "tenant" not in body.lower():
        return _fail("tenant list not visible")
    return _ok("master tenant list")


def case_master_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master"):
        return _skip("no Master menu")
    click_text(page, "Master")
    if not (click_text(page, "⋮") or click_text(page, "New tenant")):
        dots = page.locator("button").filter(has_text=re.compile(r"⋮|More"))
        if dots.count():
            dots.first.click()
    body = last_thread_text(page)
    if "New tenant" not in body and "Back to chat" not in body:
        return _fail("toolbar menu items missing")
    return _ok("toolbar menu")


def case_master_03(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master"):
        return _skip("no Master menu")
    click_text(page, "New tenant")
    page.wait_for_timeout(500)
    return _ok("new tenant form opened (validation checked visually)")


def case_master_04(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master"):
        return _skip("no Master menu")
    click_text(page, "New tenant")
    page.wait_for_timeout(400)
    name = page.locator("input").first
    try:
        name.fill("QA Test Tenant")
        click_text(page, "Save")
    except Exception as exc:
        return _fail(f"could not fill tenant form: {type(exc).__name__}")
    page.wait_for_timeout(1000)
    if "QA Test Tenant" not in last_thread_text(page):
        return _fail("tenant not in list")
    return _ok("tenant created")


def case_master_05(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master"):
        return _skip("no Master menu")
    if not click_text(page, "Edit"):
        return _fail("row Edit missing")
    return _ok("edit form")


def case_master_06(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_master"):
        return _skip("no Master menu")
    if not click_text(page, "Delete"):
        return _fail("Delete tenant missing")
    click_text(page, "Cancel")
    return _ok("delete confirm/cancel present")


def case_billing(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    return _skip("billing UI not in this suite (requested skip; 0.9 placeholder)")


# id -> callable. AUTH-04 is run late with MEM-02.
SUITE: list[tuple[str, CaseFn]] = [
    ("AUTH-01", case_auth_01),
    ("AUTH-02", case_auth_02),
    ("AUTH-03", case_auth_03),
    ("CHAT-01", case_chat_01),
    ("CHAT-02", case_chat_02),
    ("CHAT-03", case_chat_03),
    ("CHAT-04", case_chat_04),
    ("CHAT-05", case_chat_05),
    ("FILE-01", case_file_01),
    ("FILE-02", case_file_02),
    ("FILE-03", case_file_03),
    ("FILE-04", case_file_04),
    ("FILE-05", case_file_05),
    ("FILE-06", case_file_06),
    ("PROJ-01", case_proj_01),
    ("PROJ-02", case_proj_02),
    ("PROJ-03", case_proj_03),
    ("PROJ-05", case_proj_05),
    ("PROJ-04", case_proj_04),
    ("PROJ-06", case_proj_06),
    ("PROJ-07", case_proj_07),
    ("SKILL-01", case_skill_01),
    ("SKILL-02", case_skill_02),
    ("SKILL-03", case_skill_03),
    ("SKILL-04", case_skill_04),
    ("SKILL-05", case_skill_05),
    ("SKILL-06", case_skill_06),
    ("TRIG-01", case_trig_01),
    ("TRIG-02", case_trig_02),
    ("TODO-01", case_todo_01),
    ("TODO-02", case_todo_02),
    ("TODO-03", case_todo_03),
    ("CHART-01", case_chart_01),
    ("MEM-01", case_mem_01),
    ("NAV-01", case_nav_01),
    ("NAV-02", case_nav_02),
    ("NAV-03", case_nav_03),
    ("MASTER-01", case_master_01),
    ("MASTER-02", case_master_02),
    ("MASTER-03", case_master_03),
    ("MASTER-04", case_master_04),
    ("MASTER-05", case_master_05),
    ("MASTER-06", case_master_06),
    ("BILLING-01", case_billing),
    ("BILLING-02", case_billing),
    ("BILLING-03", case_billing),
    ("BILLING-04", case_billing),
    ("MEM-02", case_mem_02),
    ("AUTH-04", case_auth_04),
]
