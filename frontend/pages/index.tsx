import Head from "next/head";
import { useState, useEffect } from "react";
import {
  Input,
  Card,
  Collapse,
  Select,
  Spin,
  message,
  Typography,
  Space,
} from "antd";
import { SearchOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";

const { Search } = Input;
const { Text } = Typography;

interface Source {
  doc_name: string;
  page: number;
  snippet: string;
  similarity: number;
}

export default function Home() {
  const [question, setQuestion] = useState("");
  const [company, setCompany] = useState<string | undefined>(undefined);
  const [year, setYear] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);

  const [companies, setCompanies] = useState<string[]>([]);
  const [years, setYears] = useState<number[]>([]);

  // 加载筛选选项
  useEffect(() => {
    fetch("/api/docs")
      .then((r) => r.json())
      .then((d) => {
        if (d.companies) setCompanies(d.companies);
        if (d.years) setYears(d.years);
      })
      .catch(() => message.error("加载筛选选项失败"));
  }, []);

  const handleSearch = async () => {
    const q = question.trim();
    if (!q) {
      message.warning("请输入问题");
      return;
    }

    setLoading(true);
    setAnswer(null);
    setSources([]);

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, company, year }),
      });
      const data = await resp.json();

      if (data.error) {
        message.error(data.error);
      } else {
        setAnswer(data.answer);
        setSources(data.sources || []);
      }
    } catch {
      message.error("请求失败，请检查后端服务是否启动");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>智能问答 - 财报智能问答系统</title>
      </Head>

      {/* 筛选栏 */}
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="选择公司（不限）"
          allowClear
          style={{ width: 160 }}
          value={company}
          onChange={(val) => setCompany(val)}
          options={[
            { label: "不限", value: undefined },
            ...companies.map((c) => ({ label: c, value: c })),
          ]}
        />
        <Select
          placeholder="选择年份（不限）"
          allowClear
          style={{ width: 140 }}
          value={year}
          onChange={(val) => setYear(val)}
          options={[
            { label: "不限", value: undefined },
            ...years.map((y) => ({ label: String(y), value: y })),
          ]}
        />
      </Space>

      {/* 提问框 */}
      <Search
        placeholder="输入问题，如：茅台 2023 毛利率是多少？"
        allowClear
        enterButton={<><SearchOutlined /> 提问</>}
        size="large"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onSearch={handleSearch}
        loading={loading}
      />

      {/* 加载态 */}
      {loading && (
        <div style={{ textAlign: "center", marginTop: 48 }}>
          <Spin size="large" tip="正在分析..." />
        </div>
      )}

      {/* 答案区 */}
      {answer !== null && !loading && (
        <Card
          title="回答"
          style={{ marginTop: 24 }}
          styles={{ body: { padding: "16px 24px" } }}
        >
          <div style={{ fontSize: 16, lineHeight: 1.8 }}>
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
        </Card>
      )}

      {/* Sources */}
      {sources.length > 0 && !loading && (
        <Collapse
          style={{ marginTop: 16 }}
          items={[
            {
              key: "sources",
              label: `参考来源（${sources.length} 条）`,
              children: sources.map((s, i) => (
                <Card
                  key={i}
                  size="small"
                  style={{ marginBottom: 8 }}
                  title={
                    <Space>
                      <Text strong>{s.doc_name}</Text>
                      <Text type="secondary">第 {s.page} 页</Text>
                      <Text type="secondary">相似度 {(s.similarity * 100).toFixed(1)}%</Text>
                    </Space>
                  }
                >
                  <Text>{s.snippet}...</Text>
                </Card>
              )),
            },
          ]}
        />
      )}
    </>
  );
}
