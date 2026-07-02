import Head from "next/head";
import { Card, Typography, Descriptions, Tag } from "antd";

const { Title, Paragraph } = Typography;

export default function About() {
  return (
    <>
      <Head>
        <title>关于 - 财报智能问答系统</title>
      </Head>

      <Card title="关于本项目" style={{ maxWidth: 720 }}>
        <Title level={4}>财报智能问答系统（RAG）</Title>
        <Paragraph>
          基于 RAG（检索增强生成）技术的财报智能问答系统，支持对贵州茅台和宁德时代
          2023-2025 年度报告进行自然语言问答。
        </Paragraph>

        <Paragraph>
          RAG 管线：向量检索 + 关键词补充 → 去重 → bge-reranker-v2-m3 精排 → DeepSeek 生成。
        </Paragraph>

        <Descriptions column={1} bordered size="small" style={{ marginTop: 24 }}>
          <Descriptions.Item label="前端">
            <Tag>Next.js 14</Tag>
            <Tag>Ant Design</Tag>
            <Tag>react-markdown</Tag>
            <Tag>TypeScript</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="后端">
            <Tag>Python Flask</Tag>
            <Tag>Vercel Serverless</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="数据库">
            <Tag>Supabase</Tag>
            <Tag>pgvector</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="LLM">
            <Tag>DeepSeek</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Embedding">
            <Tag>bge-large-zh-v1.5</Tag>
            <Tag>SiliconFlow</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Reranker">
            <Tag>bge-reranker-v2-m3</Tag>
            <Tag>SiliconFlow</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="PDF 解析">
            <Tag>pdfplumber</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="部署">
            <Tag>Vercel</Tag>
          </Descriptions.Item>
        </Descriptions>

        <Paragraph style={{ marginTop: 24 }} type="secondary">
          数据来源：贵州茅台 2023-2025 年度报告、宁德时代 2023-2025 年度报告
        </Paragraph>
      </Card>
    </>
  );
}
