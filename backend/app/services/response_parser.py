"""Parse LLM response with <TABLE> and <CHART> tags into ContentBlock list."""
import re
from app.models.schemas import ContentBlock


def _process_calc_tags(text: str) -> str:
    """Replace <CALC> tags with deterministic financial calculation results."""
    import re as _re
    try:
        from app.services.financial_calculator import calculate_npv, calculate_irr, calculate_payback, format_bln, format_pct
    except ImportError:
        return text

    pattern = _re.compile(r'<CALC\s+type="(\w+)"\s+cash_flows="([^"]+)"(?:\s+discount_rate="([^"]+)")?\s*/>')

    def replace_match(m):
        calc_type = m.group(1)
        try:
            flows = [float(x.strip()) for x in m.group(2).split(",")]
            rate = float(m.group(3)) if m.group(3) else 0.12
            if calc_type == "npv":
                return f"**{format_bln(calculate_npv(flows, rate))}**"
            elif calc_type == "irr":
                return f"**{format_pct(calculate_irr(flows))}**"
            elif calc_type == "payback":
                return f"**{calculate_payback(flows)} лет**"
        except Exception:
            pass
        return m.group(0)  # return original on error

    return pattern.sub(replace_match, text)


def parse_llm_response(raw: str) -> list[ContentBlock]:
    """Parse LLM response into ContentBlock list.

    Handles:
    - <CALC> tags -> deterministic financial calculations
    - Regular markdown text -> ContentBlock(type="text")
    - <TABLE>...</TABLE> -> ContentBlock(type="table")
    - <CHART>...</CHART> -> ContentBlock(type="chart")
    """
    raw = _process_calc_tags(raw)
    blocks: list[ContentBlock] = []

    # Split by TABLE and CHART tags
    pattern = re.compile(r'(<TABLE>.*?</TABLE>|<CHART>.*?</CHART>)', re.DOTALL)
    parts = pattern.split(raw)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("<TABLE>") and part.endswith("</TABLE>"):
            table_block = _parse_table(part)
            if table_block:
                blocks.append(table_block)
        elif part.startswith("<CHART>") and part.endswith("</CHART>"):
            chart_block = _parse_chart(part)
            if chart_block:
                blocks.append(chart_block)
        else:
            # Regular text — could be markdown
            if part:
                blocks.append(ContentBlock(type="text", data=part))

    # If no blocks were created (LLM didn't use tags), treat entire response as text
    if not blocks and raw.strip():
        blocks.append(ContentBlock(type="text", data=raw.strip()))

    # Guarantee non-empty response: always return at least one block
    if not blocks:
        blocks.append(ContentBlock(type="text", data="Не удалось сформировать ответ. Попробуйте переформулировать вопрос."))

    return blocks


def _parse_table(raw: str) -> ContentBlock | None:
    """Parse <TABLE>...</TABLE> block.

    Format:
    <TABLE>
    caption: Some caption
    headers: Col1 | Col2 | Col3
    Row1Val1 | Row1Val2 | Row1Val3
    Row2Val1 | Row2Val2 | Row2Val3
    </TABLE>
    """
    try:
        content = raw.replace("<TABLE>", "").replace("</TABLE>", "").strip()
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        caption = ""
        headers = []
        rows = []

        i = 0
        # Parse caption
        if lines[i].lower().startswith("caption:"):
            caption = lines[i].split(":", 1)[1].strip()
            i += 1

        # Parse headers
        if i < len(lines) and lines[i].lower().startswith("headers:"):
            headers = [h.strip() for h in lines[i].split(":", 1)[1].split("|")]
            i += 1
        elif i < len(lines) and "|" in lines[i]:
            # First row with | is headers
            headers = [h.strip() for h in lines[i].split("|")]
            i += 1

        # Parse rows
        for line in lines[i:]:
            if "|" in line:
                row = [cell.strip() for cell in line.split("|")]
                # Skip markdown table separator lines (---|----|---)
                if all(set(cell.strip()) <= set("-: ") for cell in row):
                    continue
                rows.append(row)

        if headers or rows:
            return ContentBlock(type="table", data={
                "headers": headers,
                "rows": rows,
                "caption": caption,
            })
    except Exception:
        pass
    return None


def _parse_chart(raw: str) -> ContentBlock | None:
    """Parse <CHART>...</CHART> block.

    Format:
    <CHART>
    type: bar
    title: Chart Title
    x_key: name
    series: SeriesName=data_key=#COLOR
    data: Label1=100, Label2=200
    </CHART>

    Or for multi-series:
    series: Series1=key1=#E11D48, Series2=key2=#3B82F6
    data: Label1:key1=100:key2=200, Label2:key1=150:key2=250
    """
    try:
        content = raw.replace("<CHART>", "").replace("</CHART>", "").strip()
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        chart_type = "bar"
        title = ""
        x_key = "name"
        series = []
        data = []

        for line in lines:
            if line.lower().startswith("type:"):
                chart_type = line.split(":", 1)[1].strip()
            elif line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("x_key:"):
                x_key = line.split(":", 1)[1].strip()
            elif line.lower().startswith("series:"):
                series_str = line.split(":", 1)[1].strip()
                for s in series_str.split(","):
                    s = s.strip()
                    parts = s.split("=")
                    if len(parts) >= 3:
                        dk = parts[1].strip()
                        series.append({
                            "key": dk,
                            "data_key": dk,
                            "name": parts[0].strip(),
                            "color": parts[2].strip(),
                        })
                    elif len(parts) == 2:
                        dk = parts[0].strip().lower().replace(" ", "_")
                        series.append({
                            "key": dk,
                            "data_key": dk,
                            "name": parts[0].strip(),
                            "color": parts[1].strip() if parts[1].strip().startswith("#") else "#E11D48",
                        })
            elif line.lower().startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                for item in data_str.split(","):
                    item = item.strip()
                    if "=" in item:
                        parts = item.split("=")
                        label = parts[0].strip()
                        value = parts[1].strip()
                        # Parse numeric value: strip +, %, spaces; skip н/д
                        cleaned = value.replace("+", "").replace("%", "").replace(" ", "").replace("\u00a0", "")
                        if cleaned in ("н/д", "N/A", "-", ""):
                            continue
                        try:
                            cleaned = cleaned.replace(",", ".")
                            num = float(cleaned)
                            point = {x_key: label}
                            dk = series[0]["data_key"] if series else "value"
                            point[dk] = num
                            data.append(point)
                        except ValueError:
                            pass

        if series and data:
            return ContentBlock(type="chart", data={
                "chart_type": chart_type,
                "title": title,
                "x_key": x_key,
                "series": series,
                "data": data,
            })
    except Exception:
        pass
    return None
