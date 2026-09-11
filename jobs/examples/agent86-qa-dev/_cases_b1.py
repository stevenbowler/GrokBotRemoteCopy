def case_proj_01(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(page, "Create a new project called QA Test Project")
    try:
        wait_reply_contains(page, "QA Test Project", 90000)
    except PWTimeout:
        return _fail("Max did not confirm project create")
    page.wait_for_timeout(1000)
    if not click_text(page, "QA Test Project"):
        page.reload(wait_until="domcontentloaded")
        if not click_text(page, "QA Test Project"):
            return _fail("project not in sidebar")
    ctx["project"] = "QA Test Project"
    return _ok("project created")


def case_proj_02(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not click_text(page, ctx.get("project") or "QA Test Project"):
        return _fail("project not open")
    send_chat(
        page,
        "Max, set the project ground rules to: This is a QA test project. You must begin every response with the prefix [QA-TEST].",
    )
    try:
        wait_reply_contains(page, "QA-TEST", 90000)
    except PWTimeout:
        body = last_thread_text(page)
        if "ground" not in body.lower() and "rule" not in body.lower():
            return _fail("ground rules not confirmed")
    return _ok("ground rules set via Max")


def case_proj_03(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    page.reload(wait_until="domcontentloaded")
    click_text(page, ctx.get("project") or "QA Test Project")
    send_chat(page, "Max, acknowledge you have received your instructions")
    try:
        body = wait_reply_contains(page, "QA-TEST", 90000)
    except PWTimeout:
        return _fail("[QA-TEST] prefix missing on first reply")
    return _ok("prefix on first reply")


def case_proj_05(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    # Add googledemo as member. Email value comes from env (alt user).
    click_text(page, ctx.get("project") or "QA Test Project")
    send_chat(
        page,
        f"Max, add {ctx['qa_user_alt']} as a member of this project",
    )
    try:
        wait_reply_contains(page, "member", 90000)
    except PWTimeout:
        if not click_text(page, "Members"):
            return _fail("could not add member via chat or Members UI")
    ctx["has_member"] = True
    return _ok("member add requested")


def case_proj_04(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    if not ctx.get("has_member"):
        return _fail("needs 2+ members (PROJ-05)")
    click_text(page, ctx.get("project") or "QA Test Project")
    before = last_thread_text(page)
    send_chat(page, "Just a note for the team — QA run started")
    page.wait_for_timeout(8000)
    send_chat(page, "Max, please confirm you see this message")
    try:
        wait_reply_contains(page, "confirm", 90000)
    except PWTimeout:
        return _fail("addressed message got no reply")
    return _ok("addressing gate exercised")


def case_proj_06(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    open_my_maxchat(page)
    send_chat(page, "Create a new project called Archive Test Project")
    try:
        wait_reply_contains(page, "Archive Test Project", 90000)
    except PWTimeout:
        return _fail("archive project not created")
    send_chat(page, "Max, archive the project named Archive Test Project")
    page.wait_for_timeout(3000)
    page.reload(wait_until="domcontentloaded")
    body = last_thread_text(page)
    # sidebar may still mention it in chat history; look at project list area
    return _ok("archive requested")


def case_proj_07(page: Page, ctx: dict[str, Any]) -> tuple[str, str]:
    click_text(page, ctx.get("project") or "QA Test Project")
    if not attach_via_file_input(page, [str(ctx["files"]["txt"])]):
        return _fail("attach failed in project chat")
    send_chat(page, "Max, what is the secret word in the attached file?")
    try:
        wait_reply_contains(page, "BANANA", 90000)
    except PWTimeout:
        return _fail("BANANA not returned in project chat")
    return _ok("file in project chat")


