"""
离线灌库脚本 —— 将 PDF 年报切片、嵌入并灌入 Supabase chunks 表。

用法：
    cd backend
    python ingest.py

依赖：
    - torch (CUDA 版，利用 RTX 4060)
    - pdfplumber, sentence-transformers, langchain-text-splitters, supabase, python-dotenv
"""

import os
import re
import sys
import time

import pdfplumber
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer


def supabase_execute_with_retry(operation, max_retries=5):
    """带重试的 Supabase 操作，处理间歇性网络错误。"""
    for attempt in range(1, max_retries + 1):
        try:
            return operation.execute()
        except Exception as e:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            print(f"    网络错误（第{attempt}次重试，等待{wait}s）: {e}")
            time.sleep(wait)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# 加载环境变量 & 初始化 Supabase
# ---------------------------------------------------------------------------
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("错误：请在项目根目录 .env 中配置 SUPABASE_URL 和 SUPABASE_ANON_KEY")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')   # PDF 存放目录

# 硬编码本地模型路径（ModelScope 下载后的缓存位置）
# 如果路径不同，请修改为实际路径
MODEL_PATH = r'C:\Users\wst\.cache\modelscope\AI-ModelScope\bge-large-zh-v1.5'

# ---------------------------------------------------------------------------
# 公司名称映射：从文件名提取的公司名 → 简称
# ---------------------------------------------------------------------------
COMPANY_MAPPING = {
    "贵州茅台": "茅台",
    "宁德时代": "宁德时代",
}


def parse_metadata(filename: str):
    """
    从文件名提取公司和年份，映射为简称。

    支持的格式：
        贵州茅台2023年度报告.pdf
        贵州茅台2023年报.pdf
        宁德时代2025年度报告.pdf
    """
    base = os.path.splitext(filename)[0]  # 去 .pdf
    m = re.match(r'(.+?)(\d{4})年?度?报告', base)
    if m:
        raw_company, year = m.group(1), int(m.group(2))
        company = COMPANY_MAPPING.get(raw_company, raw_company)
        return company, year
    print(f"  警告：无法解析文件名 '{filename}'，使用文件名作为公司名")
    return base, None


def detect_company_keywords(pdf, max_pages=3):
    """
    扫描前几页，尝试从页眉中检测公司全称关键词。
    用于后续 clean_header_footer 清洗页眉。
    """
    # 预设关键词列表，覆盖两家公司的全称
    candidates = [
        "贵州茅台酒股份有限公司",
        "宁德时代新能源科技股份有限公司",
        "年度报告",
    ]
    found = set()
    for page in pdf.pages[:max_pages]:
        text = page.extract_text() or ""
        first_line = text.strip().split('\n')[0] if text.strip() else ""
        for kw in candidates:
            if kw in first_line:
                found.add(kw)
    return list(found) if found else candidates


def clean_header_footer(text: str, company_keywords: list) -> str:
    """
    去除每页的页眉和页脚：
    - 页眉：第一行包含公司名 + 年度报告
    - 页脚：最后一行是纯页码（"N/总数" 或纯数字）
    """
    if not text or not text.strip():
        return ""

    lines = text.strip().split('\n')
    if not lines:
        return ""

    # 页眉
    if lines and any(kw in lines[0] for kw in company_keywords):
        lines = lines[1:]

    # 页脚
    if lines and re.match(r'^\d+(/\d+)?$', lines[-1].strip()):
        lines = lines[:-1]

    return '\n'.join(lines)


def clean_table(table):
    """
    清洗 pdfplumber 提取的表格：
    1. 去除全 None 的列（合并单元格产生的分隔列）
    2. 合并被拆分的行（长文本跨行）
    3. 替换 None 为空字符串，清理换行符
    4. 去除全空行
    """
    if not table or len(table) < 2:
        return None

    # 1. 去除全 None 的列
    num_cols = max(len(row) for row in table)
    non_none_cols = [
        c for c in range(num_cols)
        if any(row[c] is not None for row in table if c < len(row))
    ]
    table = [
        [row[c] if c < len(row) else None for c in non_none_cols]
        for row in table
    ]

    # 2. 合并被拆分的行
    merged = [list(table[0])]
    for row in table[1:]:
        if row[0] is None and len(merged) > 0:
            prev = merged[-1]
            for i, cell in enumerate(row):
                if cell and i < len(prev):
                    prev[i] = (prev[i] or '') + cell
        else:
            merged.append(list(row))
    table = merged

    # 3. 将 None → ""，清理换行符
    table = [
        [(cell or '').replace('\n', ' ').strip() for cell in row]
        for row in table
    ]

    # 4. 去除全空行
    table = [row for row in table if any(cell for cell in row)]

    return table


def table_to_markdown(table) -> str:
    """将清洗后的表格转为 Markdown 格式。"""
    if not table or len(table) < 2:
        return ""

    max_cols = max(len(row) for row in table)
    rows_padded = [row + [''] * (max_cols - len(row)) for row in table]

    lines = []
    lines.append('| ' + ' | '.join(rows_padded[0]) + ' |')
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    for row in rows_padded[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)


def split_large_table(md: str, max_chars: int = 1024, _depth: int = 0) -> list:
    """
    若表格 Markdown 超过 max_chars 字符，按行切半（保留表头）。
    每半部分作为一个独立 chunk。
    """
    if len(md) <= max_chars:
        return [md]

    lines = md.split('\n')
    if len(lines) <= 2:
        # 只剩表头+分隔行，无法再切，直接截断
        return [md[:max_chars]]

    if _depth > 5:
        # 防止无限递归，直接按字符截断
        return [md[:max_chars]]

    header = lines[:2]  # 表头 + 分隔行
    data_lines = lines[2:]
    mid = max(1, len(data_lines) // 2)

    first_half = header + data_lines[:mid]
    second_half = header + data_lines[mid:]

    parts = []
    for half in [first_half, second_half]:
        part_md = '\n'.join(half)
        if len(part_md) > max_chars:
            parts.extend(split_large_table(part_md, max_chars, _depth + 1))
        else:
            parts.append(part_md)
    return parts


def process_pdf(pdf_path: str) -> list:
    """
    处理单个 PDF，返回所有 chunk 的列表。
    每个 chunk 为 (content, chunk_type, page_num) 元组。
    """
    filename = os.path.basename(pdf_path)
    company, year = parse_metadata(filename)
    if year is None:
        print(f"  跳过：无法解析年份 - {filename}")
        return []

    print(f"  解析：{filename} → 公司={company}, 年份={year}")

    all_chunks = []
    pdf = pdfplumber.open(pdf_path)
    company_keywords = detect_company_keywords(pdf)

    # 初始化文本切片器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,          # 字符数
        chunk_overlap=50,        # 字符数
        separators=['\n\n', '\n', '。', '；', '，', ' ']
    )

    for page_num, page in enumerate(pdf.pages, start=1):
        # ---- 文本 ----
        raw_text = page.extract_text() or ""
        cleaned_text = clean_header_footer(raw_text, company_keywords)

        if cleaned_text.strip():
            text_chunks = text_splitter.split_text(cleaned_text)
            for tc in text_chunks:
                if tc.strip():
                    all_chunks.append((tc.strip(), 'text', page_num))

        # ---- 表格 ----
        tables = page.extract_tables() or []
        for table in tables:
            cleaned_table = clean_table(table)
            if cleaned_table is None:
                continue
            md = table_to_markdown(cleaned_table)
            if not md.strip():
                continue

            # 检查是否需要拆分
            md_parts = split_large_table(md, 1024)
            for part in md_parts:
                if part.strip():
                    all_chunks.append((part.strip(), 'table', page_num))

    pdf.close()
    return all_chunks, company, year, filename


def main():
    # ---- 加载 Embedding 模型 ----
    print(f"加载 Embedding 模型：{MODEL_PATH} ...")
    try:
        model = SentenceTransformer(MODEL_PATH)
    except Exception as e:
        print(f"错误：无法加载模型。请确认路径正确：{MODEL_PATH}")
        print(f"  错误详情：{e}")
        sys.exit(1)
    print(f"  Device: {model.device}")

    # ---- 收集所有 PDF ----
    if not os.path.isdir(PDF_DIR):
        print(f"错误：PDF 目录不存在：{PDF_DIR}")
        sys.exit(1)

    pdf_files = sorted([
        f for f in os.listdir(PDF_DIR)
        if f.lower().endswith('.pdf')
    ])
    if not pdf_files:
        print(f"错误：{PDF_DIR} 中没有 PDF 文件")
        sys.exit(1)
    print(f"找到 {len(pdf_files)} 个 PDF 文件")

    # ---- 处理每个 PDF ----
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        result = process_pdf(pdf_path)
        all_chunks, company, year, filename = result

        if not all_chunks:
            print(f"  跳过 {filename}：未提取到有效内容")
            continue

        print(f"  共 {len(all_chunks)} 个 chunk，开始生成 Embedding ...")

        # ---- Embedding ----
        texts = [c[0] for c in all_chunks]
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)

        # ---- 幂等写入 ----
        print(f"  写入 Supabase ...")
        supabase_execute_with_retry(
            supabase.table('chunks').delete().eq('doc_name', filename)
        )

        for i in range(0, len(all_chunks), 50):
            batch = [
                {
                    "doc_name": filename,
                    "company": company,
                    "year": year,
                    "page": all_chunks[j][2],
                    "chunk_type": all_chunks[j][1],
                    "content": all_chunks[j][0],
                    "embedding": embeddings[j].tolist(),
                }
                for j in range(i, min(i + 50, len(all_chunks)))
            ]
            supabase_execute_with_retry(
                supabase.table("chunks").insert(batch)
            )
            time.sleep(0.5)  # 避免触发 Supabase 限流

        print(f"  {filename} 写入完成！\n")

    print("全部 PDF 灌库完成！")


if __name__ == '__main__':
    main()
